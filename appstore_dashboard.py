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
            return report
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


def merged_metric(reports: list[dict[str, Any]], field: str, app: dict[str, Any]) -> dict[str, int]:
    sources = [report.get(field) for report in reports]
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


def build_time_series(app: dict[str, Any], reports: list[dict[str, Any]], days: int = 30) -> dict[str, Any]:
    downloads = merged_metric(reports, "by_date", app)
    impressions = merged_metric(reports, "impressions_by_date", app)
    page_views = merged_metric(reports, "product_page_views_by_date", app)
    taps = merged_metric(reports, "taps_by_date", app)

    explicit_end = parse_date(app.get("metrics_report_date")) or parse_date(app.get("report_date"))
    dates = [parse_date(key) for series in [downloads, impressions, page_views, taps] for key in series]
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
                },
            }
        )
    return compacted


def compact_app(app: dict[str, Any], reports: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    history = app.get("history") if isinstance(app.get("history"), dict) else {}
    sales = app.get("sales") if isinstance(app.get("sales"), dict) else {}
    reviews = app.get("reviews") if isinstance(app.get("reviews"), dict) else {}
    review_pipeline = app.get("review_pipeline") if isinstance(app.get("review_pipeline"), dict) else {}
    quality = app.get("quality_signals") if isinstance(app.get("quality_signals"), dict) else {}
    pricing = app.get("pricing") if isinstance(app.get("pricing"), dict) else {}
    source_funnel = app.get("funnel_by_source") if isinstance(app.get("funnel_by_source"), dict) else {}
    territory_funnel = app.get("funnel_by_territory") if isinstance(app.get("funnel_by_territory"), dict) else {}
    screenshots = app.get("screenshot_inventory") if isinstance(app.get("screenshot_inventory"), dict) else {}
    reports = reports or []

    return {
        "key": app.get("key"),
        "name": app.get("name"),
        "app_id": app.get("app_id"),
        "bundle_id": app.get("bundle_id"),
        "sku": app.get("sku"),
        "metrics_report_date": app.get("metrics_report_date"),
        "availability": {
            "downloads_report_date": bool(app.get("downloads_report_date_available")),
            "engagement_report_date": bool(app.get("engagement_report_date_available")),
            "history": bool(history.get("available")),
            "sales": bool(sales.get("available")),
            "reviews": bool(reviews.get("available")),
            "review_pipeline": bool(review_pipeline.get("available")),
            "screenshots": bool(screenshots.get("available")),
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
            "time_series": build_time_series(app, reports),
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
            "manual_prices": pricing.get("manual_prices") or {},
            "automatic_prices": pricing.get("automatic_prices") or {},
        },
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
        current_downloads = as_int(current_7d.get("downloads"))
        previous_downloads = as_int(previous_7d.get("downloads"))
        if previous_downloads >= 5 and current_downloads <= previous_downloads * 0.5:
            alerts.append(
                {
                    "level": "warning",
                    "scope": app.get("key"),
                    "title": f"{name}: baisse forte des téléchargements J-7",
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

        if today.get("impressions", 0) > 0 and today.get("product_page_views", 0) == 0 and today.get("downloads", 0) == 0:
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


def build_dashboard_payload(metrics: dict[str, Any]) -> dict[str, Any]:
    apps = [
        compact_app(app, load_reports(app.get("key") or ""))
        for app in metrics.get("apps", [])
        if isinstance(app, dict)
    ]
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
        },
        "apps": apps,
        "totals": totals_from_apps(apps),
    }
    payload["alerts"] = build_alerts(payload)
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_dashboard(metrics_path: Path = METRICS_PATH, output_path: Path = DASHBOARD_PAYLOAD_PATH) -> dict[str, Any]:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload = build_dashboard_payload(metrics)
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
    parser.add_argument("--copy-to-site", type=Path, help="Optional target directory, usually Gogolabs.fr/private/appstore.")
    args = parser.parse_args()

    payload = write_dashboard(args.metrics, args.output)
    print(f"DASHBOARD {args.output}")
    print(f"ALERTS {ALERTS_PATH}")
    print(f"ALERT_COUNT {len(payload['alerts'])}")
    if args.copy_to_site:
        copied = copy_payload_to_site(args.output, args.copy_to_site)
        print(f"SITE_PAYLOAD {copied}")


if __name__ == "__main__":
    main()
