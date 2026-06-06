#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import io
import json
import os
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


def compact_price_schedule(resp: Any) -> dict[str, Any]:
    if not isinstance(resp, dict):
        return {"available": False, "raw_type": type(resp).__name__}
    data = resp.get("data") or {}
    attrs = data.get("attributes") or {}
    rel = data.get("relationships") or {}
    included = resp.get("included") or []
    return {
        "available": True,
        "attributes": attrs,
        "relationships": rel,
        "included_count": len(included),
        "included_sample": included[:5],
    }


def fetch_pricing(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    path = (
        f"/apps/{app_id}/appPriceSchedule"
        "?include=baseTerritory,manualPrices,automaticPrices"
        "&limit[manualPrices]=200&limit[automaticPrices]=200"
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


def fetch_sales(client: asc.ASCClient, report_date: str) -> dict[str, Any]:
    vendor = os.environ.get("APPSTORE_VENDOR_NUMBER") or os.environ.get("ASC_VENDOR_NUMBER")
    if not vendor:
        return {"available": False, "error": "APPSTORE_VENDOR_NUMBER/ASC_VENDOR_NUMBER missing"}
    path = (
        "/salesReports?filter[frequency]=DAILY"
        f"&filter[reportDate]={report_date}"
        "&filter[reportSubType]=SUMMARY"
        "&filter[reportType]=SALES"
        f"&filter[vendorNumber]={vendor}"
    )
    raw, error = safe_get(client, path)
    if error:
        return {"available": False, "error": error}
    rows = decode_sales(raw)
    return {"available": True, "vendor_number": vendor, "report_date": report_date, "rows": rows}


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
    metrics["pricing_sales_source"] = {
        "pricing": "App Store Connect appPriceSchedule endpoint, best effort",
        "sales": "App Store Connect salesReports DAILY SALES SUMMARY, best effort",
        "sales_status": {k: v for k, v in sales.items() if k != "rows"},
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
        app_sales = aggregate_sales(sales_rows, sku) if sales.get("available") else {"available": False, "error": sales.get("error")}
        app["sales"] = app_sales
        total_paid += int(app_sales.get("paid_units") or 0)
        total_proceeds += float(app_sales.get("developer_proceeds") or 0)

    totals["paid_units"] = total_paid
    totals["developer_proceeds"] = round(total_proceeds, 2)
    save_metrics(metrics)


if __name__ == "__main__":
    main()
