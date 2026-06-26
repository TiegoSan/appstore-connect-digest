#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import appstore_analytics as asc
import daily_appstore_digest as digest

ROOT = Path(__file__).resolve().parent
STRATEGY_DIR = ROOT / "strategy"
LATEST_METRICS_PATH = STRATEGY_DIR / "latest-metrics.json"


ENGAGEMENT_TOTAL_FIELDS = {
    "impressions": "impressions_total_available",
    "unique_impressions": "unique_impressions_total_available",
    "product_page_views": "product_page_views_total_available",
    "unique_product_page_views": "unique_product_page_views_total_available",
    "taps": "taps_total_available",
    "unique_taps": "unique_taps_total_available",
}


def count_field_value(row: dict[str, str], field: str) -> int:
    raw = (row.get(field) or "0").replace(",", "")
    return int(raw) if raw.isdigit() else 0


def count_value(row: dict[str, str]) -> int:
    return count_field_value(row, "Counts")


def pct(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator * 100, 2)


def top(data: dict[str, int] | None) -> tuple[str, int]:
    if not data:
        return "", 0
    return sorted(data.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def rows_for_date(rows: list[dict[str, str]], report_date: str) -> list[dict[str, str]]:
    return [row for row in rows if row.get("Date") == report_date]


def rows_for_event(rows: list[dict[str, str]], event: str) -> list[dict[str, str]]:
    return [row for row in rows if row.get("Event") == event]


def aggregate(rows: list[dict[str, str]], dim: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if dim in row:
            counter[row.get(dim) or ""] += count_value(row)
    return dict(counter)


def aggregate_field(rows: list[dict[str, str]], dim: str, field: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if dim in row:
            counter[row.get(dim) or ""] += count_field_value(row, field)
    return dict(counter)


def first_time_downloads_by_date(rows: list[dict[str, str]]) -> dict[str, int]:
    return aggregate([row for row in rows if row.get("Download Type") == "First-time download"], "Date")


def latest_row_date(apps: list[digest.AppDigest]) -> str | None:
    dates: set[str] = set()
    for app in apps:
        data = app.data or {}
        for row in data.get("raw_standard_rows") or []:
            if row.get("Date"):
                dates.add(str(row["Date"]))
        for row in data.get("raw_engagement_rows") or []:
            if row.get("Date"):
                dates.add(str(row["Date"]))
    return max(dates) if dates else None


def metric(app: digest.AppDigest, field: str) -> int:
    return digest.metric(app, field)


def filtered_summary_data(data: dict[str, Any], report_date: str) -> dict[str, Any]:
    standard_rows = rows_for_date(data.get("raw_standard_rows") or [], report_date)
    engagement_rows = rows_for_date(data.get("raw_engagement_rows") or [], report_date)

    impression_rows = rows_for_event(engagement_rows, "Impression")
    product_page_view_rows = rows_for_event(engagement_rows, "Page view")
    tap_rows = rows_for_event(engagement_rows, "Tap")
    first_time_rows = [row for row in standard_rows if row.get("Download Type") == "First-time download"]

    downloads = sum(count_value(row) for row in standard_rows)
    first_time_downloads = sum(count_value(row) for row in first_time_rows)
    impressions = sum(count_value(row) for row in impression_rows)
    unique_impressions = sum(count_field_value(row, "Unique Counts") for row in impression_rows)
    product_page_views = sum(count_value(row) for row in product_page_view_rows)
    unique_product_page_views = sum(count_field_value(row, "Unique Counts") for row in product_page_view_rows)
    taps = sum(count_value(row) for row in tap_rows)
    unique_taps = sum(count_field_value(row, "Unique Counts") for row in tap_rows)

    return {
        "downloads": downloads,
        "first_time_downloads": first_time_downloads,
        "impressions": impressions,
        "unique_impressions": unique_impressions,
        "product_page_views": product_page_views,
        "unique_product_page_views": unique_product_page_views,
        "taps": taps,
        "unique_taps": unique_taps,
        "conversion_rate": pct(first_time_downloads, unique_impressions),
        "page_view_rate": pct(product_page_views, unique_impressions),
        "tap_rate": pct(taps, unique_impressions),
        "dominant_source": top(aggregate(impression_rows, "Source Type")),
        "dominant_territory": top(aggregate(impression_rows, "Territory")),
        "dominant_device": top(aggregate(impression_rows, "Device")),
        "engagement_report_date_available": bool(engagement_rows),
        "downloads_report_date_available": bool(standard_rows),
        "impressions_by_date": aggregate(impression_rows, "Date"),
        "product_page_views_by_date": aggregate(product_page_view_rows, "Date"),
        "taps_by_date": aggregate(tap_rows, "Date"),
        "impressions_by_source_type_report_date": aggregate(impression_rows, "Source Type"),
        "impressions_by_territory_report_date": aggregate(impression_rows, "Territory"),
        "impressions_by_device_report_date": aggregate(impression_rows, "Device"),
        "engagement_by_event_report_date": aggregate(engagement_rows, "Event"),
        "engagement_unique_by_event_report_date": aggregate_field(engagement_rows, "Event", "Unique Counts"),
    }


def previous_filtered_value(previous_data: dict[str, Any] | None, field: str) -> int | None:
    if not previous_data:
        return None
    previous_date = latest_row_date([digest.AppDigest("previous", "previous", None, None, previous_data, None)])
    if not previous_date:
        return None
    return int(filtered_summary_data(previous_data, previous_date).get(field) or 0)


def delta_filtered(current_value: int, previous_data: dict[str, Any] | None, field: str) -> int | None:
    previous_value = previous_filtered_value(previous_data, field)
    if previous_value is None:
        return None
    return current_value - previous_value


def app_summary(app: digest.AppDigest, report_date: str) -> dict[str, Any]:
    data = app.data or {}
    profile = data.get("app", {})
    filtered = filtered_summary_data(data, report_date)
    source = filtered["dominant_source"]
    territory = filtered["dominant_territory"]
    device = filtered["dominant_device"]

    summary = {
        "key": app.key,
        "name": app.name,
        "app_id": profile.get("app_id"),
        "bundle_id": profile.get("bundle_id"),
        "sku": profile.get("sku"),
        "error": app.error,
        "analytics_segment_errors": data.get("segment_errors") or [],
        "metrics_scope": "report_date",
        "metrics_report_date": report_date,
        "downloads": filtered["downloads"],
        "first_time_downloads": filtered["first_time_downloads"],
        "impressions": filtered["impressions"],
        "unique_impressions": filtered["unique_impressions"],
        "product_page_views": filtered["product_page_views"],
        "unique_product_page_views": filtered["unique_product_page_views"],
        "taps": filtered["taps"],
        "unique_taps": filtered["unique_taps"],
        "conversion_rate": filtered["conversion_rate"],
        "page_view_rate": filtered["page_view_rate"],
        "tap_rate": filtered["tap_rate"],
        "dominant_source": {"name": source[0], "count": source[1]},
        "dominant_territory": {"name": territory[0], "count": territory[1]},
        "dominant_device": {"name": device[0], "count": device[1]},
        "delta_downloads": delta_filtered(filtered["downloads"], app.previous_data, "downloads"),
        "delta_first_time_downloads": delta_filtered(filtered["first_time_downloads"], app.previous_data, "first_time_downloads"),
        "delta_impressions": delta_filtered(filtered["impressions"], app.previous_data, "impressions"),
        "delta_product_page_views": delta_filtered(filtered["product_page_views"], app.previous_data, "product_page_views"),
        "delta_taps": delta_filtered(filtered["taps"], app.previous_data, "taps"),
        "engagement_report_date_available": filtered["engagement_report_date_available"],
        "downloads_report_date_available": filtered["downloads_report_date_available"],
        "impressions_by_date": filtered["impressions_by_date"],
        "product_page_views_by_date": filtered["product_page_views_by_date"],
        "taps_by_date": filtered["taps_by_date"],
        "first_time_downloads_by_date": first_time_downloads_by_date(data.get("raw_standard_rows") or []),
        "impressions_by_source_type_report_date": filtered["impressions_by_source_type_report_date"],
        "impressions_by_territory_report_date": filtered["impressions_by_territory_report_date"],
        "impressions_by_device_report_date": filtered["impressions_by_device_report_date"],
        "engagement_by_event_report_date": filtered["engagement_by_event_report_date"],
        "engagement_unique_by_event_report_date": filtered["engagement_unique_by_event_report_date"],
    }

    for source_field, target_field in ENGAGEMENT_TOTAL_FIELDS.items():
        summary[target_field] = metric(app, source_field)
    summary["downloads_total_available"] = metric(app, "standard_total")
    summary["first_time_downloads_total_available"] = metric(app, "first_time_downloads")
    summary["conversion_rate_total_available"] = data.get("conversion_rate")
    summary["page_view_rate_total_available"] = data.get("page_view_rate")
    summary["tap_rate_total_available"] = data.get("tap_rate")

    return summary


def failed_collection_payload(app: dict[str, Any], error: Exception) -> dict[str, Any]:
    return {
        "app": app,
        "standard_total": 0,
        "first_time_downloads": 0,
        "raw_standard_rows": [],
        "raw_engagement_rows": [],
        "segment_errors": [],
        "collection_error": str(error),
    }


def write_latest_metrics(apps: list[digest.AppDigest], report_date: str) -> None:
    STRATEGY_DIR.mkdir(exist_ok=True)
    summaries = [app_summary(app, report_date) for app in apps]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_date": report_date,
        "metrics_scope": "report_date",
        "metrics_semantics": {
            "primary_values": "downloads, first_time_downloads, impressions, product_page_views and taps are filtered to rows where Date == report_date.",
            "total_available_values": "*_total_available fields preserve the previous unfiltered aggregate across all rows returned by Apple Analytics.",
        },
        "positioning": {
            "brand": "GogoLabs",
            "goal": "Vendre les apps et construire un revenu logiciel indépendant.",
            "doctrine": "Transformer l'expertise de production en apps macOS premium qui économisent du temps, réduisent les erreurs et rendent les workflows créatifs plus contrôlables.",
        },
        "totals": {
            "downloads": sum(item["downloads"] for item in summaries),
            "first_time_downloads": sum(item["first_time_downloads"] for item in summaries),
            "impressions": sum(item["impressions"] for item in summaries),
            "product_page_views": sum(item["product_page_views"] for item in summaries),
            "taps": sum(item["taps"] for item in summaries),
            "downloads_total_available": sum(item["downloads_total_available"] for item in summaries),
            "first_time_downloads_total_available": sum(item["first_time_downloads_total_available"] for item in summaries),
            "impressions_total_available": sum(item["impressions_total_available"] for item in summaries),
            "product_page_views_total_available": sum(item["product_page_views_total_available"] for item in summaries),
            "taps_total_available": sum(item["taps_total_available"] for item in summaries),
        },
        "apps": summaries,
        "analysis_instruction": "Produire une réflexion stratégique longue seulement si les données le justifient: utiliser les valeurs primaires filtrées sur report_date pour tout diagnostic quotidien et toute comparaison; les champs *_total_available servent uniquement à l'audit de collecte. Lire freshness/report_date, history J-7/J-30, funnel_by_source, funnel_by_territory, sales/pricing, reviews, metadata, screenshot_inventory et quality_signals. Distinguer signal réel, bruit probable, hypothèse et donnée manquante. Avant toute recommandation produit, pricing, ASO, screenshots ou metadata, vérifier app.review_pipeline: si has_blocking_pipeline_change vaut true ou si une version est READY_FOR_REVIEW, WAITING_FOR_REVIEW, IN_REVIEW, PENDING_APPLE_RELEASE, PENDING_DEVELOPER_RELEASE, PROCESSING_FOR_APP_STORE ou WAITING_FOR_EXPORT_COMPLIANCE, traiter ces changements comme déjà engagés et proposer uniquement des actions compatibles.",
    }
    LATEST_METRICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"METRICS {LATEST_METRICS_PATH}")


def collect() -> None:
    config = asc.load_config()
    apps: list[digest.AppDigest] = []
    for key, app in config.get("apps", {}).items():
        try:
            result = asc.collect_downloads(config, app, create_snapshot=True)
            latest_path = digest.save_json(key, app, result)
            previous_path, previous_data = digest.previous_report(key, latest_path)
            apps.append(digest.AppDigest(key, app["name"], latest_path, previous_path, result, previous_data))
            print(f"{key}: JSON {latest_path}")
        except Exception as exc:
            result = failed_collection_payload(app, exc)
            apps.append(digest.AppDigest(key, app.get("name", key), None, None, result, None, str(exc)))
            print(f"{key}: ERROR {exc}")
    report_date = latest_row_date(apps) or datetime.now().strftime("%Y-%m-%d")
    write_latest_metrics(apps, report_date)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect latest App Store metrics without rendering or sending email")
    parser.parse_args()
    collect()


if __name__ == "__main__":
    main()
