#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import io
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import appstore_analytics as asc

ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "strategy" / "latest-metrics.json"


def load_metrics() -> dict[str, Any]:
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def save_metrics(payload: dict[str, Any]) -> None:
    METRICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_get(client: asc.ASCClient, path: str) -> tuple[Any | None, str | None]:
    try:
        return client.get(path), None
    except Exception as exc:
        return None, str(exc)


def redact_value(value: Any, secret: str | None) -> Any:
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, "[redacted]")
    if isinstance(value, dict):
        return {key: redact_value(item, secret) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item, secret) for item in value]
    return value


def public_sales_status(sales: dict[str, Any], vendor: str | None = None) -> dict[str, Any]:
    return {
        key: redact_value(value, vendor)
        for key, value in sales.items()
        if key not in {"rows", "vendor_number"}
    }


def compact_price_schedule(resp: Any) -> dict[str, Any]:
    if not isinstance(resp, dict):
        return {"available": False, "raw_type": type(resp).__name__}
    data = resp.get("data") or {}
    attrs = data.get("attributes") or {}
    rel = data.get("relationships") or {}
    included = resp.get("included") or []
    base_territory = ((rel.get("baseTerritory") or {}).get("data") or {}).get("id")
    manual_prices = rel.get("manualPrices") or {}
    automatic_prices = rel.get("automaticPrices") or {}
    return {
        "available": True,
        "schedule_id": data.get("id"),
        "attributes": attrs,
        "base_territory": base_territory,
        "manual_prices": {
            "total": (((manual_prices.get("meta") or {}).get("paging") or {}).get("total")),
            "returned": len(manual_prices.get("data") or []),
            "limit": (((manual_prices.get("meta") or {}).get("paging") or {}).get("limit")),
        },
        "automatic_prices": {
            "total": (((automatic_prices.get("meta") or {}).get("paging") or {}).get("total")),
            "returned": len(automatic_prices.get("data") or []),
            "limit": (((automatic_prices.get("meta") or {}).get("paging") or {}).get("limit")),
        },
        "included_count": len(included),
        "included_sample": included[:5],
    }


def fetch_pricing(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    path = (
        f"/apps/{app_id}/appPriceSchedule"
        "?include=baseTerritory,manualPrices,automaticPrices"
        "&limit[manualPrices]=50&limit[automaticPrices]=50"
    )
    schedule, error = safe_get(client, path)
    if error:
        return {"available": False, "error": error}
    return compact_price_schedule(schedule)


def decode_sales(raw: Any) -> list[dict[str, str]]:
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


def candidate_sales_dates(report_date: str) -> list[str]:
    try:
        current = datetime.strptime(report_date, "%Y-%m-%d").date()
    except ValueError:
        current = date.today()
    return [(current - timedelta(days=offset)).isoformat() for offset in range(1, 5)]


def fetch_sales_for_date(client: asc.ASCClient, vendor: str, report_date: str) -> tuple[dict[str, Any] | None, str | None]:
    path = (
        "/salesReports?filter[frequency]=DAILY"
        f"&filter[reportDate]={report_date}"
        "&filter[reportSubType]=SUMMARY"
        "&filter[reportType]=SALES"
        f"&filter[vendorNumber]={vendor}"
    )
    raw, error = safe_get(client, path)
    if error:
        return None, error
    rows = decode_sales(raw)
    return {"available": True, "vendor_number": vendor, "report_date": report_date, "rows": rows}, None


def fetch_sales(client: asc.ASCClient, metrics_report_date: str) -> dict[str, Any]:
    vendor = os.environ.get("APPSTORE_VENDOR_NUMBER") or os.environ.get("ASC_VENDOR_NUMBER")
    if not vendor:
        return {"available": False, "error": "APPSTORE_VENDOR_NUMBER/ASC_VENDOR_NUMBER missing"}
    errors: dict[str, str] = {}
    for candidate in candidate_sales_dates(metrics_report_date):
        sales, error = fetch_sales_for_date(client, vendor, candidate)
        if sales is not None:
            sales["requested_metrics_report_date"] = metrics_report_date
            sales["fallback_dates_tried"] = list(errors.keys())
            return sales
        errors[candidate] = error or "unknown error"
    return {"available": False, "vendor_number": vendor, "requested_metrics_report_date": metrics_report_date, "errors_by_date": errors}


def aggregate_sales(rows: list[dict[str, str]], sku: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("SKU") == sku or row.get("Vendor Identifier") == sku]
    units = sum(number(row, "Units") for row in matches)
    proceeds = sum(number(row, "Developer Proceeds", "Proceeds") for row in matches)
    customer_price_values = [number(row, "Customer Price") for row in matches if number(row, "Customer Price")]
    currencies = sorted({row.get("Customer Currency") or row.get("Currency of Proceeds") or "" for row in matches if row})
    refunds = sum(abs(number(row, "Units")) for row in matches if number(row, "Units") < 0)
    return {
        "available": bool(matches),
        "rows": len(matches),
        "paid_units": int(units),
        "refund_units": int(refunds),
        "developer_proceeds": round(proceeds, 2),
        "customer_price_min": min(customer_price_values) if customer_price_values else None,
        "customer_price_max": max(customer_price_values) if customer_price_values else None,
        "currencies": [c for c in currencies if c],
    }


def unavailable_sales_payload(sales: dict[str, Any], previous_sales: Any = None) -> dict[str, Any]:
    refresh_status = {
        "available": False,
        "error": sales.get("error"),
        "errors_by_date": sales.get("errors_by_date"),
    }
    if isinstance(previous_sales, dict) and previous_sales.get("available"):
        preserved = dict(previous_sales)
        preserved["stale"] = True
        preserved["refresh_status"] = {k: v for k, v in refresh_status.items() if v}
        return preserved
    return refresh_status


def main() -> None:
    metrics = load_metrics()
    config = asc.load_config()
    client = asc.ASCClient(config)
    report_date = metrics.get("report_date") or ""
    sales = fetch_sales(client, report_date) if report_date else {"available": False, "error": "missing report_date"}
    sales_rows = sales.get("rows") or []

    totals = metrics.setdefault("totals", {})
    totals.setdefault("paid_units", 0)
    totals.setdefault("developer_proceeds", 0.0)
    sales_available = bool(sales.get("available"))
    metrics["pricing_sales_source"] = {
        "pricing": "App Store Connect appPriceSchedule endpoint, best effort",
        "sales": "App Store Connect salesReports DAILY SALES SUMMARY, best effort, preserving previous values when refresh is unavailable",
        "sales_status": public_sales_status(sales, os.environ.get("APPSTORE_VENDOR_NUMBER") or os.environ.get("ASC_VENDOR_NUMBER")),
    }

    total_paid = 0
    total_proceeds = 0.0
    for app in metrics.get("apps", []):
        app_id = ((app.get("app") or {}).get("app_id") or app.get("app_id") or "")
        sku = app.get("sku") or ((app.get("app") or {}).get("sku")) or ""
        if app_id:
            app["pricing"] = fetch_pricing(client, app_id)
        else:
            app["pricing"] = {"available": False, "error": "missing app_id"}
        app_sales = aggregate_sales(sales_rows, sku) if sales_available else unavailable_sales_payload(sales, app.get("sales"))
        app["sales"] = app_sales
        if sales_available:
            total_paid += int(app_sales.get("paid_units") or 0)
            total_proceeds += float(app_sales.get("developer_proceeds") or 0)

    if sales_available:
        totals["paid_units"] = total_paid
        totals["developer_proceeds"] = round(total_proceeds, 2)
    save_metrics(metrics)


if __name__ == "__main__":
    main()
