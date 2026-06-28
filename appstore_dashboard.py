#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "strategy" / "latest-metrics.json"
DASHBOARD_DIR = ROOT / "dashboard"
DASHBOARD_PAYLOAD_PATH = DASHBOARD_DIR / "latest-appstore-dashboard.json"
ALERTS_PATH = DASHBOARD_DIR / "latest-appstore-alerts.json"
REPORTS_DIR = ROOT / "reports"

BLOCKING_STATES = {
    "READY_FOR_REVIEW",
    "WAITING_FOR_REVIEW",
    "IN_REVIEW",
    "PENDING_APPLE_RELEASE",
    "PENDING_DEVELOPER_RELEASE",
    "PROCESSING_FOR_APP_STORE",
    "WAITING_FOR_EXPORT_COMPLIANCE",
}

LIVE_STATES = {"READY_FOR_SALE"}


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def report_paths(app_key: str, reports_dir: Path = REPORTS_DIR) -> list[Path]:
    return sorted(reports_dir.glob(f"{app_key}-downloads-*.json"))


def latest_report_path(app_key: str, reports_dir: Path = REPORTS_DIR) -> Path | None:
    paths = report_paths(app_key, reports_dir)
    return paths[-1] if paths else None


def load_report(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(report, dict):
            report["_source_report_name"] = path.name
            return normalize_report_download_series(report)
        return {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_reports(app_key: str, reports_dir: Path = REPORTS_DIR) -> list[dict[str, Any]]:
    return [report for path in report_paths(app_key, reports_dir) if (report := load_report(path))]


def int_by_date(*sources: Any) -> dict[str, int]:
    values: dict[str, int] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if parse_date(key):
                values[key] = as_int(value)
    return values


ROW_VALUE_FIELDS = {"Counts", "Unique Counts"}


def raw_row_identity(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, str(value or "")) for key, value in row.items() if key not in ROW_VALUE_FIELDS))


def raw_downloads_by_date(report: dict[str, Any], download_type: str | None = None) -> dict[str, int]:
    values: dict[str, int] = {}
    rows = report.get("raw_standard_rows") if isinstance(report.get("raw_standard_rows"), list) else []
    deduped_rows: dict[tuple[tuple[str, str], ...], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        deduped_rows[raw_row_identity(row)] = row
    for row in deduped_rows.values():
        key = row.get("Date")
        if not parse_date(key):
            continue
        if download_type and row.get("Download Type") != download_type:
            continue
        values[str(key)] = values.get(str(key), 0) + as_int(row.get("Counts"))
    return values


def normalize_report_download_series(report: dict[str, Any]) -> dict[str, Any]:
    if "first_time_downloads_by_date" not in report:
        report["first_time_downloads_by_date"] = raw_downloads_by_date(report, "First-time download")
    if "total_downloads_by_date" not in report:
        report["total_downloads_by_date"] = report.get("by_date") or raw_downloads_by_date(report)
    return report


def previous_metric(previous_time_series: dict[str, Any] | None, field: str) -> dict[str, int]:
    if not isinstance(previous_time_series, dict):
        return {}
    values: dict[str, int] = {}
    for row in previous_time_series.get("rows") or []:
        if not isinstance(row, dict):
            continue
        key = row.get("date")
        if parse_date(key) and row.get(field) is not None:
            values[str(key)] = as_int(row.get(field))
    return values


def merged_metric(
    reports: list[dict[str, Any]],
    field: str,
    app: dict[str, Any],
    previous_time_series: dict[str, Any] | None = None,
) -> dict[str, int]:
    previous_field = {
        "by_date": "downloads",
        "first_time_downloads_by_date": "first_time_downloads",
        "total_downloads_by_date": "downloads",
        "impressions_by_date": "impressions",
        "product_page_views_by_date": "product_page_views",
        "taps_by_date": "taps",
    }.get(field, field)
    sources = [previous_metric(previous_time_series, previous_field)]
    sources.extend(report.get(field) for report in reports)
    sources.append(app.get(field))
    return int_by_date(*sources)


def metric_freshness(series: dict[str, int], end: date) -> dict[str, Any]:
    dates = sorted(parse_date(key) for key in series if parse_date(key))
    dates = [item for item in dates if item]
    latest = dates[-1] if dates else None
    return {
        "available": bool(latest),
        "latest_date": latest.isoformat() if latest else None,
        "age_days": (end - latest).days if latest else None,
        "is_current": bool(latest and latest == end),
        "measured_days": len(dates),
    }


def build_time_series(
    app: dict[str, Any],
    reports: list[dict[str, Any]],
    previous_time_series: dict[str, Any] | None = None,
    days: int = 90,
) -> dict[str, Any]:
    downloads = merged_metric(reports, "by_date", app, previous_time_series)
    first_time_downloads = merged_metric(reports, "first_time_downloads_by_date", app, previous_time_series)
    impressions = merged_metric(reports, "impressions_by_date", app, previous_time_series)
    page_views = merged_metric(reports, "product_page_views_by_date", app, previous_time_series)
    taps = merged_metric(reports, "taps_by_date", app, previous_time_series)

    explicit_end = parse_date(app.get("metrics_report_date")) or parse_date(app.get("report_date"))
    dates = [parse_date(key) for series in [downloads, first_time_downloads, impressions, page_views, taps] for key in series]
    dates = [item for item in dates if item]
    end = explicit_end or max(dates, default=datetime.now(timezone.utc).date())
    start = end - timedelta(days=days - 1)

    rows = []
    current = start
    while current <= end:
        key = current.isoformat()
        rows.append(
            {
                "date": key,
                "downloads": downloads.get(key),
                "first_time_downloads": first_time_downloads.get(key),
                "impressions": impressions.get(key),
                "product_page_views": page_views.get(key),
                "taps": taps.get(key),
            }
        )
        current += timedelta(days=1)

    return {
        "days": days,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "rows": rows,
        "source_reports": [report.get("_source_report_name") for report in reports if report.get("_source_report_name")],
        "freshness_by_metric": {
            "downloads": metric_freshness(downloads, end),
            "first_time_downloads": metric_freshness(first_time_downloads, end),
            "impressions": metric_freshness(impressions, end),
            "product_page_views": metric_freshness(page_views, end),
            "taps": metric_freshness(taps, end),
        },
    }


def compact_rows(rows: Any, limit: int = 8) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    allowed = {
        "name",
        "impressions",
        "unique_impressions",
        "product_page_views",
        "unique_product_page_views",
        "taps",
        "unique_taps",
        "first_time_downloads",
        "downloads",
        "page_view_rate",
        "tap_rate",
        "download_rate",
        "paid_units",
        "refund_units",
        "developer_proceeds",
        "currencies",
        "territory",
    }
    compacted = []
    for row in rows[:limit]:
        if isinstance(row, dict):
            compacted.append({key: row.get(key) for key in allowed if key in row})
    return compacted


def compact_versions(versions: Any, limit: int = 4) -> list[dict[str, Any]]:
    if not isinstance(versions, list):
        return []
    compacted = []
    for version in versions[:limit]:
        if not isinstance(version, dict):
            continue
        build = version.get("build") if isinstance(version.get("build"), dict) else {}
        compacted.append(
            {
                "platform": version.get("platform"),
                "version_string": version.get("version_string"),
                "app_store_state": version.get("app_store_state"),
                "app_version_state": version.get("app_version_state"),
                "created_date": version.get("created_date"),
                "build": {
                    "version": build.get("version"),
                    "uploaded_date": build.get("uploaded_date"),
                    "processing_state": build.get("processing_state"),
                    "expired": build.get("expired"),
                    "min_os_version": build.get("min_os_version"),
                    "computed_min_macos_version": build.get("computed_min_macos_version"),
                },
            }
        )
    return compacted


def version_metadata_localizations(review_pipeline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_locale: dict[str, dict[str, Any]] = {}
    for version in review_pipeline.get("versions") or []:
        if not isinstance(version, dict):
            continue
        version_string = version.get("version_string")
        app_store_state = version.get("app_store_state")
        for item in version.get("localizations") or []:
            if not isinstance(item, dict):
                continue
            locale = item.get("locale")
            if not locale or locale in by_locale:
                continue
            by_locale[locale] = {
                "version_string": version_string,
                "app_store_state": app_store_state,
                "promotional_text": item.get("promotional_text"),
                "description": item.get("description"),
                "keywords": item.get("keywords"),
                "marketing_url": item.get("marketing_url"),
                "support_url": item.get("support_url"),
                "whats_new": item.get("whats_new"),
            }
    return by_locale


def compact_metadata(metadata: dict[str, Any], review_pipeline: dict[str, Any] | None = None) -> dict[str, Any]:
    localizations = metadata.get("localizations") if isinstance(metadata.get("localizations"), list) else []
    categories = metadata.get("categories") if isinstance(metadata.get("categories"), list) else []
    version_metadata = version_metadata_localizations(review_pipeline or {})
    return {
        "available": bool(metadata.get("available")),
        "localization_count": len(localizations),
        "localizations": [
            {
                "locale": item.get("locale"),
                "name": item.get("name"),
                "subtitle": item.get("subtitle"),
                "privacy_policy_url": item.get("privacy_policy_url"),
                "has_privacy_policy_text": bool(item.get("has_privacy_policy_text")),
                **version_metadata.get(item.get("locale"), {}),
            }
            for item in localizations[:8]
            if isinstance(item, dict)
        ],
        "categories": [
            {
                "relation": item.get("relation"),
                "id": item.get("id"),
                "name": ((item.get("attributes") or {}).get("name") if isinstance(item.get("attributes"), dict) else None),
            }
            for item in categories[:4]
            if isinstance(item, dict)
        ],
        "error": metadata.get("error"),
    }


def compact_screenshots(screenshots: dict[str, Any]) -> dict[str, Any]:
    localizations = screenshots.get("localizations") if isinstance(screenshots.get("localizations"), list) else []
    errors = screenshots.get("errors") if isinstance(screenshots.get("errors"), list) else []
    rows = []
    total = 0
    for loc in localizations[:8]:
        if not isinstance(loc, dict):
            continue
        count = as_int(loc.get("screenshot_total"))
        total += count
        rows.append(
            {
                "locale": loc.get("locale"),
                "version_string": loc.get("version_string"),
                "app_store_state": loc.get("app_store_state"),
                "screenshot_total": count,
                "sets": [
                    {
                        "screenshot_display_type": item.get("screenshot_display_type"),
                        "screenshot_count": as_int(item.get("screenshot_count")),
                        "screenshots": [
                            compact_screenshot_item(shot, item.get("screenshot_display_type"))
                            for shot in (item.get("screenshots") or [])[:12]
                            if isinstance(shot, dict)
                        ],
                    }
                    for item in (loc.get("sets") or [])[:8]
                    if isinstance(item, dict)
                ],
            }
        )
    return {
        "available": bool(screenshots.get("available")),
        "localization_count": len(localizations),
        "screenshot_total": total,
        "localizations": rows,
        "error_count": len(errors),
        "errors": [
            {"locale": item.get("locale"), "version_string": item.get("version_string"), "error": item.get("error")}
            for item in errors[:3]
            if isinstance(item, dict)
        ],
        "error": screenshots.get("error"),
    }


def screenshot_display_url(image_asset: dict[str, Any], target_width: int = 720) -> str | None:
    template_url = image_asset.get("template_url") or image_asset.get("templateUrl")
    if not isinstance(template_url, str) or not template_url:
        return None
    width = as_int(image_asset.get("width"))
    height = as_int(image_asset.get("height"))
    target_height = round(target_width * height / width) if width and height else target_width
    return (
        template_url
        .replace("{w}", str(target_width))
        .replace("{h}", str(target_height))
        .replace("{f}", "png")
    )


def compact_screenshot_item(item: dict[str, Any], display_type: Any) -> dict[str, Any]:
    image_asset = item.get("image_asset") if isinstance(item.get("image_asset"), dict) else {}
    return {
        "id": item.get("id"),
        "file_name": item.get("file_name"),
        "display_type": display_type,
        "asset_delivery_state": item.get("asset_delivery_state"),
        "width": as_int(image_asset.get("width")),
        "height": as_int(image_asset.get("height")),
        "display_url": screenshot_display_url(image_asset),
    }


def compact_iap(iap: dict[str, Any]) -> dict[str, Any]:
    items = iap.get("items") if isinstance(iap.get("items"), list) else []
    return {
        "available": bool(iap.get("available")),
        "total": as_int(iap.get("total")),
        "returned": as_int(iap.get("returned")),
        "items": [
            {
                "name": item.get("name"),
                "product_id": item.get("product_id"),
                "in_app_purchase_type": item.get("in_app_purchase_type"),
                "state": item.get("state"),
                "family_sharable": item.get("family_sharable"),
            }
            for item in items[:8]
            if isinstance(item, dict)
        ],
        "error": iap.get("error"),
        "errors": iap.get("errors") if isinstance(iap.get("errors"), list) else None,
    }


def compact_subscriptions(subscriptions: dict[str, Any]) -> dict[str, Any]:
    groups = ((subscriptions.get("groups") or {}).get("items") if isinstance(subscriptions.get("groups"), dict) else []) or []
    subs = (
        ((subscriptions.get("subscriptions") or {}).get("items") if isinstance(subscriptions.get("subscriptions"), dict) else [])
        or []
    )
    return {
        "available": bool(subscriptions.get("available")),
        "group_count": as_int((subscriptions.get("groups") or {}).get("total")) if isinstance(subscriptions.get("groups"), dict) else 0,
        "subscription_count": len(subs),
        "groups": [
            {
                "reference_name": item.get("reference_name"),
                "subscriptions_count": item.get("subscriptions_count"),
            }
            for item in groups[:8]
            if isinstance(item, dict)
        ],
        "subscriptions": [
            {
                "name": item.get("name"),
                "product_id": item.get("product_id"),
                "state": item.get("state"),
                "subscription_period": item.get("subscription_period"),
                "family_sharable": item.get("family_sharable"),
            }
            for item in subs[:8]
            if isinstance(item, dict)
        ],
        "error": subscriptions.get("error"),
    }


def compact_game_center(game_center: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": bool(game_center.get("available")),
        "state": game_center.get("state"),
        "achievements_count": game_center.get("achievements_count"),
        "leaderboards_count": game_center.get("leaderboards_count"),
        "challenges_count": game_center.get("challenges_count"),
        "activities_count": game_center.get("activities_count"),
        "app_versions_count": game_center.get("app_versions_count"),
        "error": game_center.get("error"),
    }


def review_states(review_pipeline: dict[str, Any]) -> set[str]:
    states = set(review_pipeline.get("pipeline_states") or [])
    states.update(review_pipeline.get("blocking_recommendation_states") or [])
    for version in review_pipeline.get("versions") or []:
        if isinstance(version, dict) and version.get("app_store_state"):
            states.add(str(version["app_store_state"]))
    return states


def analytics_scope(review_pipeline: dict[str, Any]) -> dict[str, Any]:
    states = review_states(review_pipeline)
    is_live = bool(states.intersection(LIVE_STATES))
    return {
        "is_live": is_live,
        "included_in_portfolio_metrics": is_live,
        "reason": "ready_for_sale_version" if is_live else "no_ready_for_sale_version",
        "states": sorted(states),
    }


def compact_app(
    app: dict[str, Any],
    reports: list[dict[str, Any]] | None = None,
    previous_app: dict[str, Any] | None = None,
) -> dict[str, Any]:
    history = app.get("history") if isinstance(app.get("history"), dict) else {}
    sales = app.get("sales") if isinstance(app.get("sales"), dict) else {}
    reviews = app.get("reviews") if isinstance(app.get("reviews"), dict) else {}
    review_pipeline = app.get("review_pipeline") if isinstance(app.get("review_pipeline"), dict) else {}
    quality = app.get("quality_signals") if isinstance(app.get("quality_signals"), dict) else {}
    pricing = app.get("pricing") if isinstance(app.get("pricing"), dict) else {}
    source_funnel = app.get("funnel_by_source") if isinstance(app.get("funnel_by_source"), dict) else {}
    territory_funnel = app.get("funnel_by_territory") if isinstance(app.get("funnel_by_territory"), dict) else {}
    screenshots = app.get("screenshot_inventory") if isinstance(app.get("screenshot_inventory"), dict) else {}
    metadata = app.get("metadata") if isinstance(app.get("metadata"), dict) else {}
    iap = app.get("in_app_purchases") if isinstance(app.get("in_app_purchases"), dict) else {}
    subscriptions = app.get("subscriptions") if isinstance(app.get("subscriptions"), dict) else {}
    game_center = app.get("game_center") if isinstance(app.get("game_center"), dict) else {}
    reports = reports or []
    previous_history = previous_app.get("history") if isinstance(previous_app, dict) and isinstance(previous_app.get("history"), dict) else {}
    previous_time_series = previous_history.get("time_series") if isinstance(previous_history.get("time_series"), dict) else None
    scope = analytics_scope(review_pipeline)

    return {
        "key": app.get("key"),
        "name": app.get("name"),
        "app_id": app.get("app_id"),
        "bundle_id": app.get("bundle_id"),
        "sku": app.get("sku"),
        "metrics_report_date": app.get("metrics_report_date"),
        "analytics_scope": scope,
        "availability": {
            "downloads_report_date": bool(app.get("downloads_report_date_available")),
            "engagement_report_date": bool(app.get("engagement_report_date_available")),
            "history": bool(history.get("available")),
            "sales": bool(sales.get("available")),
            "reviews": bool(reviews.get("available")),
            "review_pipeline": bool(review_pipeline.get("available")),
            "metadata": bool(metadata.get("available")),
            "screenshots": bool(screenshots.get("available")),
            "in_app_purchases": bool(iap.get("available")),
            "subscriptions": bool(subscriptions.get("available")),
            "game_center": bool(game_center.get("available")),
        },
        "today": {
            "downloads": as_int(app.get("downloads")),
            "first_time_downloads": as_int(app.get("first_time_downloads")),
            "impressions": as_int(app.get("impressions")),
            "product_page_views": as_int(app.get("product_page_views")),
            "taps": as_int(app.get("taps")),
            "conversion_rate": as_float(app.get("conversion_rate")),
            "page_view_rate": as_float(app.get("page_view_rate")),
            "tap_rate": as_float(app.get("tap_rate")),
            "delta_downloads": as_int(app.get("delta_downloads")),
            "delta_first_time_downloads": as_int(app.get("delta_first_time_downloads")),
            "delta_impressions": as_int(app.get("delta_impressions")),
            "delta_product_page_views": as_int(app.get("delta_product_page_views")),
            "delta_taps": as_int(app.get("delta_taps")),
        },
        "history": {
            "latest_metric_date": history.get("latest_metric_date"),
            "current_7d": history.get("current_7d") or {},
            "previous_7d": history.get("previous_7d") or {},
            "current_30d": history.get("current_30d") or {},
            "delta_7d": history.get("delta_7d") or {},
            "time_series": build_time_series(app, reports, previous_time_series),
        },
        "sales": {
            "available": bool(sales.get("available")),
            "stale": bool(sales.get("stale")),
            "paid_units": as_int(sales.get("paid_units")),
            "refund_units": as_int(sales.get("refund_units")),
            "developer_proceeds": as_float(sales.get("developer_proceeds")) or 0,
            "refund_rate": as_float(sales.get("refund_rate")),
            "currencies": sales.get("currencies") or [],
            "by_territory": compact_rows(sales.get("by_territory"), 8),
        },
        "reviews": {
            "available": bool(reviews.get("available")),
            "recent_count": as_int(reviews.get("recent_count")),
            "recent_average_rating": as_float(reviews.get("recent_average_rating")),
            "recent_low_rating_count": as_int(reviews.get("recent_low_rating_count")),
            "recent_high_rating_count": as_int(reviews.get("recent_high_rating_count")),
        },
        "review_pipeline": {
            "available": bool(review_pipeline.get("available")),
            "has_pending_version": bool(review_pipeline.get("has_pending_version")),
            "has_blocking_pipeline_change": bool(review_pipeline.get("has_blocking_pipeline_change")),
            "pipeline_states": review_pipeline.get("pipeline_states") or [],
            "blocking_recommendation_states": review_pipeline.get("blocking_recommendation_states") or [],
            "pipeline_version_count": as_int(review_pipeline.get("pipeline_version_count")),
            "versions": compact_versions(review_pipeline.get("versions")),
        },
        "funnels": {
            "source": {
                "available": bool(source_funnel.get("available")),
                "rows": compact_rows(source_funnel.get("rows")),
            },
            "territory": {
                "available": bool(territory_funnel.get("available")),
                "rows": compact_rows(territory_funnel.get("rows")),
            },
        },
        "quality": {
            "refund_rate": as_float(quality.get("refund_rate")),
            "has_paid_signal": bool(quality.get("has_paid_signal")),
            "has_review_signal": bool(quality.get("has_review_signal")),
            "has_source_funnel": bool(quality.get("has_source_funnel")),
            "has_territory_funnel": bool(quality.get("has_territory_funnel")),
            "screenshot_inventory_available": bool(screenshots.get("available")),
        },
        "pricing": {
            "available": bool(pricing.get("available")),
            "base_territory": pricing.get("base_territory"),
            "base_price": pricing.get("base_price") or {},
            "manual_prices": pricing.get("manual_prices") or {},
            "automatic_prices": pricing.get("automatic_prices") or {},
        },
        "metadata": compact_metadata(metadata, review_pipeline),
        "screenshot_inventory": compact_screenshots(screenshots),
        "in_app_purchases": compact_iap(iap),
        "subscriptions": compact_subscriptions(subscriptions),
        "game_center": compact_game_center(game_center),
        "dominants": {
            "source": app.get("dominant_source") or {},
            "territory": app.get("dominant_territory") or {},
            "device": app.get("dominant_device") or {},
        },
        "error": app.get("error"),
    }


def totals_from_apps(apps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "downloads": sum(app["today"]["downloads"] for app in apps),
        "first_time_downloads": sum(app["today"]["first_time_downloads"] for app in apps),
        "impressions": sum(app["today"]["impressions"] for app in apps),
        "product_page_views": sum(app["today"]["product_page_views"] for app in apps),
        "taps": sum(app["today"]["taps"] for app in apps),
        "paid_units": sum(app["sales"]["paid_units"] for app in apps),
        "refund_units": sum(app["sales"]["refund_units"] for app in apps),
        "developer_proceeds": round(sum(app["sales"]["developer_proceeds"] for app in apps), 2),
    }


def totals_from_time_series(apps: list[dict[str, Any]], days: int = 7) -> dict[str, Any]:
    totals = {
        "downloads": 0,
        "first_time_downloads": 0,
        "impressions": 0,
        "product_page_views": 0,
        "taps": 0,
        "measured_points": 0,
        "possible_points": 0,
        "days": days,
    }
    for app in apps:
        rows = (((app.get("history") or {}).get("time_series") or {}).get("rows") or [])[-days:]
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in ["downloads", "first_time_downloads", "impressions", "product_page_views", "taps"]:
                totals["possible_points"] += 1
                if row.get(key) is not None:
                    totals[key] += as_int(row.get(key))
                    totals["measured_points"] += 1
    totals["coverage_rate"] = round((totals["measured_points"] / totals["possible_points"]) * 100, 1) if totals["possible_points"] else 0
    return totals


def apps_in_portfolio_metrics(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        app
        for app in apps
        if ((app.get("analytics_scope") or {}).get("included_in_portfolio_metrics"))
    ]


def load_previous_dashboard(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_alerts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    freshness = payload.get("freshness") if isinstance(payload.get("freshness"), dict) else {}

    report_age_days = freshness.get("report_age_days")
    if isinstance(report_age_days, int) and report_age_days > 2:
        alerts.append(
            {
                "level": "critical",
                "scope": "portfolio",
                "title": "Données App Store en retard",
                "detail": f"Le report_date a {report_age_days} jours.",
            }
        )

    for app in payload.get("apps", []):
        name = app.get("name") or app.get("key") or "App"
        today = app.get("today") or {}
        history = app.get("history") or {}
        sales = app.get("sales") or {}
        reviews = app.get("reviews") or {}
        pipeline = app.get("review_pipeline") or {}
        availability = app.get("availability") or {}
        scope = app.get("analytics_scope") or {}

        states = set(pipeline.get("blocking_recommendation_states") or pipeline.get("pipeline_states") or [])
        if pipeline.get("has_blocking_pipeline_change") or states.intersection(BLOCKING_STATES):
            alerts.append(
                {
                    "level": "critical",
                    "scope": app.get("key"),
                    "title": f"{name}: version App Store en état bloquant",
                    "detail": ", ".join(sorted(states)) or "Pipeline App Store actif.",
                }
            )

        if not scope.get("included_in_portfolio_metrics"):
            continue

        if not availability.get("downloads_report_date") and not availability.get("engagement_report_date"):
            alerts.append(
                {
                    "level": "warning",
                    "scope": app.get("key"),
                    "title": f"{name}: métriques du jour absentes",
                    "detail": "Ni downloads ni engagement ne sont disponibles pour le report_date.",
                }
            )

        current_7d = history.get("current_7d") or {}
        previous_7d = history.get("previous_7d") or {}
        current_downloads = as_int(current_7d.get("first_time_downloads") if current_7d.get("first_time_downloads") is not None else current_7d.get("downloads"))
        previous_downloads = as_int(previous_7d.get("first_time_downloads") if previous_7d.get("first_time_downloads") is not None else previous_7d.get("downloads"))
        if previous_downloads >= 5 and current_downloads <= previous_downloads * 0.5:
            alerts.append(
                {
                    "level": "warning",
                    "scope": app.get("key"),
                    "title": f"{name}: baisse forte des premiers téléchargements J-7",
                    "detail": f"{current_downloads} vs {previous_downloads} sur la fenêtre précédente.",
                }
            )

        impressions = as_int(current_7d.get("impressions"))
        page_views = as_int(current_7d.get("product_page_views"))
        if impressions >= 100 and page_views == 0:
            alerts.append(
                {
                    "level": "warning",
                    "scope": app.get("key"),
                    "title": f"{name}: impressions sans pages vues",
                    "detail": f"{impressions} impressions sur 7 jours, 0 page view.",
                }
            )

        if as_int(sales.get("refund_units")) > 0:
            alerts.append(
                {
                    "level": "warning",
                    "scope": app.get("key"),
                    "title": f"{name}: remboursement détecté",
                    "detail": f"{sales.get('refund_units')} remboursement(s), taux {sales.get('refund_rate')}.",
                }
            )

        if as_int(reviews.get("recent_low_rating_count")) > 0:
            alerts.append(
                {
                    "level": "warning",
                    "scope": app.get("key"),
                    "title": f"{name}: avis faible récent",
                    "detail": f"{reviews.get('recent_low_rating_count')} avis faible(s) récent(s).",
                }
            )

        today_downloads = today.get("first_time_downloads") if today.get("first_time_downloads") is not None else today.get("downloads")
        if today.get("impressions", 0) > 0 and today.get("product_page_views", 0) == 0 and as_int(today_downloads) == 0:
            alerts.append(
                {
                    "level": "info",
                    "scope": app.get("key"),
                    "title": f"{name}: visibilité sans conversion aujourd'hui",
                    "detail": f"{today.get('impressions')} impressions, 0 page view, 0 download.",
                }
            )

    level_rank = {"critical": 0, "warning": 1, "info": 2}
    return sorted(alerts, key=lambda item: (level_rank.get(item["level"], 9), item.get("title") or ""))


def build_dashboard_payload(metrics: dict[str, Any], previous_dashboard: dict[str, Any] | None = None) -> dict[str, Any]:
    previous_apps = {
        app.get("key"): app
        for app in (previous_dashboard or {}).get("apps", [])
        if isinstance(app, dict) and app.get("key")
    }
    apps = [
        compact_app(app, load_reports(app.get("key") or ""), previous_apps.get(app.get("key")))
        for app in metrics.get("apps", [])
        if isinstance(app, dict)
    ]
    portfolio_apps = apps_in_portfolio_metrics(apps)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_generated_at": metrics.get("generated_at"),
        "report_date": metrics.get("report_date"),
        "metrics_scope": metrics.get("metrics_scope"),
        "freshness": metrics.get("freshness") or {},
        "sources": {
            "market_intelligence": metrics.get("market_intelligence_source"),
            "pricing_sales": metrics.get("pricing_sales_source"),
            "review_pipeline": metrics.get("review_pipeline_source"),
            "store_capabilities": metrics.get("store_capabilities_source"),
        },
        "apps": apps,
        "analytics_scope": {
            "mode": "live_apps_only",
            "total_app_count": len(apps),
            "live_app_count": len(portfolio_apps),
            "excluded_app_count": len(apps) - len(portfolio_apps),
        },
        "totals": totals_from_apps(portfolio_apps),
        "totals_7d": totals_from_time_series(portfolio_apps, 7),
    }
    payload["alerts"] = build_alerts(payload)
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_dashboard(
    metrics_path: Path = METRICS_PATH,
    output_path: Path = DASHBOARD_PAYLOAD_PATH,
    previous_dashboard_path: Path | None = None,
) -> dict[str, Any]:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload = build_dashboard_payload(metrics, load_previous_dashboard(previous_dashboard_path))
    write_json(output_path, payload)
    write_json(ALERTS_PATH, {"report_date": payload.get("report_date"), "alerts": payload["alerts"]})
    return payload


def copy_payload_to_site(payload_path: Path, site_dir: Path) -> Path:
    site_dir.mkdir(parents=True, exist_ok=True)
    target = site_dir / "latest-appstore-dashboard.json"
    shutil.copy2(payload_path, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the private static App Store dashboard payload.")
    parser.add_argument("--metrics", type=Path, default=METRICS_PATH)
    parser.add_argument("--output", type=Path, default=DASHBOARD_PAYLOAD_PATH)
    parser.add_argument("--previous-dashboard", type=Path, help="Optional previous dashboard payload used to preserve time series.")
    parser.add_argument("--copy-to-site", type=Path, help="Optional target directory, usually Gogolabs.fr/private/appstore.")
    args = parser.parse_args()

    payload = write_dashboard(args.metrics, args.output, args.previous_dashboard)
    print(f"DASHBOARD {args.output}")
    print(f"ALERTS {ALERTS_PATH}")
    print(f"ALERT_COUNT {len(payload['alerts'])}")
    if args.copy_to_site:
        copied = copy_payload_to_site(args.output, args.copy_to_site)
        print(f"SITE_PAYLOAD {copied}")


if __name__ == "__main__":
    main()
