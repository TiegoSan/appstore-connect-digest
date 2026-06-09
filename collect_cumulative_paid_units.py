#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import io
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import appstore_analytics as asc

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "appstore_config.json"
STRATEGY_DIR = ROOT / "strategy"
LATEST_METRICS_PATH = STRATEGY_DIR / "latest-metrics.json"
OUTPUT_PATH = STRATEGY_DIR / "cumulative-paid-units.json"

DEFAULT_START_DATE = "2026-01-01"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def decode_sales_report(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    data = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
    try:
        text = gzip.decompress(data).decode("utf-8-sig")
    except Exception:
        text = data.decode("utf-8-sig", errors="replace")
    if not text.strip():
        return []
    delimiter = "\t" if "\t" in text.splitlines()[0] else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def number(row: dict[str, str], *names: str) -> float:
    for name in names:
        raw = row.get(name)
        if raw not in (None, ""):
            try:
                return float(str(raw).replace(",", ""))
            except ValueError:
                return 0.0
    return 0.0


def row_sku(row: dict[str, str]) -> str:
    return row.get("SKU") or row.get("Vendor Identifier") or ""


def row_title(row: dict[str, str]) -> str:
    return row.get("Title") or row.get("Apple Identifier") or row_sku(row) or "(unknown)"


def row_country(row: dict[str, str]) -> str:
    return row.get("Country Code") or row.get("Country") or row.get("Territory") or "(unknown)"


def row_currency(row: dict[str, str]) -> str:
    return row.get("Customer Currency") or row.get("Currency of Proceeds") or ""


def report_date_from_row(row: dict[str, str], fallback: str) -> str:
    return row.get("Begin Date") or row.get("End Date") or row.get("Date") or fallback


def fetch_daily_sales(client: asc.ASCClient, vendor: str, day: date) -> tuple[list[dict[str, str]], str | None]:
    report_date = day.isoformat()
    path = (
        "/salesReports?filter[frequency]=DAILY"
        f"&filter[reportDate]={report_date}"
        "&filter[reportSubType]=SUMMARY"
        "&filter[reportType]=SALES"
        f"&filter[vendorNumber]={vendor}"
    )
    try:
        raw = client.get(path)
        return decode_sales_report(raw), None
    except Exception as exc:
        return [], str(exc)


def fetch_all_daily_sales(client: asc.ASCClient, vendor: str, start: date, end: date) -> tuple[list[dict[str, str]], dict[str, str]]:
    rows: list[dict[str, str]] = []
    errors: dict[str, str] = {}
    for day in date_range(start, end):
        day_rows, error = fetch_daily_sales(client, vendor, day)
        if day_rows:
            for row in day_rows:
                row["_report_date"] = day.isoformat()
            rows.extend(day_rows)
        elif error:
            # Apple often returns no downloadable report for dates without sales or not yet processed.
            errors[day.isoformat()] = error
    return rows, errors


def app_lookup(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for key, app in (config.get("apps") or {}).items():
        item = {
            "key": key,
            "name": app.get("name") or key,
            "app_id": app.get("app_id"),
            "bundle_id": app.get("bundle_id"),
            "sku": app.get("sku") or "",
        }
        sku = item["sku"]
        if sku:
            lookup[sku] = item
    return lookup


def empty_app_sales(app: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": app.get("key"),
        "name": app.get("name"),
        "app_id": app.get("app_id"),
        "bundle_id": app.get("bundle_id"),
        "sku": app.get("sku"),
        "paid_units_gross": 0,
        "refund_units": 0,
        "paid_units_net": 0,
        "developer_proceeds": 0.0,
        "customer_price_min": None,
        "customer_price_max": None,
        "currencies": [],
        "territories": {},
        "first_sale_date": None,
        "last_sale_date": None,
        "rows": 0,
    }


def aggregate(rows: list[dict[str, str]], config: dict[str, Any], period_start: date, period_end: date) -> dict[str, Any]:
    known = app_lookup(config)
    apps_by_sku: dict[str, dict[str, Any]] = {sku: empty_app_sales(app) for sku, app in known.items()}
    unknown_apps: dict[str, dict[str, Any]] = {}

    def bucket_for(sku: str, row: dict[str, str]) -> dict[str, Any]:
        if sku in apps_by_sku:
            return apps_by_sku[sku]
        bucket = unknown_apps.get(sku)
        if not bucket:
            bucket = empty_app_sales({"key": None, "name": row_title(row), "sku": sku})
            unknown_apps[sku] = bucket
        return bucket

    total_gross = 0
    total_refunds = 0
    total_net = 0
    total_proceeds = 0.0
    all_currencies: set[str] = set()
    all_territories: defaultdict[str, int] = defaultdict(int)
    price_values: list[float] = []
    sale_dates: list[str] = []

    for row in rows:
        sku = row_sku(row)
        units = int(number(row, "Units"))
        if not sku or units == 0:
            continue
        proceeds = number(row, "Developer Proceeds", "Proceeds")
        customer_price = number(row, "Customer Price")
        currency = row_currency(row)
        territory = row_country(row)
        sale_date = report_date_from_row(row, row.get("_report_date") or "")

        bucket = bucket_for(sku, row)
        bucket["rows"] += 1
        bucket["paid_units_net"] += units
        if units > 0:
            bucket["paid_units_gross"] += units
            total_gross += units
        elif units < 0:
            bucket["refund_units"] += abs(units)
            total_refunds += abs(units)
        bucket["developer_proceeds"] = round(float(bucket["developer_proceeds"] or 0.0) + proceeds, 2)
        bucket["territories"][territory] = int(bucket["territories"].get(territory, 0)) + units
        if currency:
            currencies = set(bucket.get("currencies") or [])
            currencies.add(currency)
            bucket["currencies"] = sorted(currencies)
            all_currencies.add(currency)
        if customer_price:
            prices = [v for v in [bucket.get("customer_price_min"), bucket.get("customer_price_max")] if isinstance(v, (int, float))]
            prices.append(customer_price)
            bucket["customer_price_min"] = min(prices)
            bucket["customer_price_max"] = max(prices)
            price_values.append(customer_price)
        if sale_date:
            dates = [d for d in [bucket.get("first_sale_date"), bucket.get("last_sale_date"), sale_date] if d]
            bucket["first_sale_date"] = min(dates)
            bucket["last_sale_date"] = max(dates)
            sale_dates.append(sale_date)
        total_net += units
        total_proceeds += proceeds
        all_territories[territory] += units

    apps = list(apps_by_sku.values()) + list(unknown_apps.values())
    apps = sorted(apps, key=lambda item: (-int(item.get("paid_units_net") or 0), str(item.get("name") or "")))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "App Store Connect salesReports DAILY SALES SUMMARY",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "totals": {
            "paid_units_gross": int(total_gross),
            "refund_units": int(total_refunds),
            "paid_units_net": int(total_net),
            "developer_proceeds": round(total_proceeds, 2),
            "customer_price_min": min(price_values) if price_values else None,
            "customer_price_max": max(price_values) if price_values else None,
            "currencies": sorted(all_currencies),
            "territories": dict(sorted(all_territories.items(), key=lambda kv: (-kv[1], kv[0]))),
            "first_sale_date": min(sale_dates) if sale_dates else None,
            "last_sale_date": max(sale_dates) if sale_dates else None,
            "rows": len(rows),
        },
        "apps": apps,
    }


def inject_into_latest_metrics(cumulative: dict[str, Any]) -> None:
    metrics = load_json(LATEST_METRICS_PATH)
    if not metrics:
        return
    metrics["cumulative_sales"] = {
        "source": cumulative.get("source"),
        "generated_at": cumulative.get("generated_at"),
        "period_start": cumulative.get("period_start"),
        "period_end": cumulative.get("period_end"),
        **(cumulative.get("totals") or {}),
        "by_app": cumulative.get("apps") or [],
    }
    save_json(LATEST_METRICS_PATH, metrics)


def main() -> None:
    config = asc.load_config()
    vendor = os.environ.get("APPSTORE_VENDOR_NUMBER") or os.environ.get("ASC_VENDOR_NUMBER")
    if not vendor:
        raise SystemExit("APPSTORE_VENDOR_NUMBER/ASC_VENDOR_NUMBER missing")

    raw_start = os.environ.get("ASC_CUMULATIVE_START_DATE") or os.environ.get("APPSTORE_CUMULATIVE_START_DATE") or DEFAULT_START_DATE
    start = parse_date(raw_start) or parse_date(DEFAULT_START_DATE)
    end = date.today() - timedelta(days=1)
    if not start or start > end:
        raise SystemExit("Invalid cumulative sales date range")

    client = asc.ASCClient(config)
    rows, errors = fetch_all_daily_sales(client, vendor, start, end)
    cumulative = aggregate(rows, config, start, end)
    cumulative["collection_status"] = {
        "requested_days": len(date_range(start, end)),
        "days_with_rows": len({row.get("_report_date") for row in rows if row.get("_report_date")}),
        "days_without_rows_or_unavailable": len(errors),
        "errors_sample": dict(list(errors.items())[:10]),
    }
    save_json(OUTPUT_PATH, cumulative)
    inject_into_latest_metrics(cumulative)
    print(f"CUMULATIVE_PAID_UNITS {OUTPUT_PATH}")
    print(json.dumps(cumulative.get("totals") or {}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
