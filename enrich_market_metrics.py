#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import appstore_analytics as asc

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
METRICS_PATH = ROOT / "strategy" / "latest-metrics.json"

EVENT_TO_FIELD = {
    "Impression": "impressions",
    "Page view": "product_page_views",
    "Tap": "taps",
}

ANALYSIS_INSTRUCTION = (
    "Produire une réflexion stratégique longue seulement si les données le justifient: utiliser les "
    "valeurs primaires filtrées sur report_date pour tout diagnostic quotidien et toute comparaison; "
    "les champs *_total_available servent uniquement à l'audit de collecte. Lire freshness/report_date, "
    "history J-7/J-30, funnel_by_source, funnel_by_territory, sales/pricing, reviews, metadata, "
    "screenshot_inventory et quality_signals. Distinguer signal réel, bruit probable, hypothèse et "
    "donnée manquante. Avant toute recommandation produit, pricing, ASO, screenshots ou metadata, "
    "vérifier app.review_pipeline: si has_blocking_pipeline_change vaut true ou si une version est "
    "READY_FOR_REVIEW, WAITING_FOR_REVIEW, IN_REVIEW, PENDING_APPLE_RELEASE, "
    "PENDING_DEVELOPER_RELEASE, PROCESSING_FOR_APP_STORE ou WAITING_FOR_EXPORT_COMPLIANCE, traiter ces "
    "changements comme déjà engagés et proposer uniquement des actions compatibles."
)


def load_metrics() -> dict[str, Any]:
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def save_metrics(payload: dict[str, Any]) -> None:
    METRICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_get(client: asc.ASCClient, path: str) -> tuple[Any | None, str | None]:
    try:
        return client.get(path), None
    except Exception as exc:
        return None, str(exc)


def parse_date(value: Any) -> datetime.date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def count_field_value(row: dict[str, str], field: str = "Counts") -> int:
    raw = str(row.get(field) or "0").replace(",", "")
    try:
        return int(float(raw))
    except ValueError:
        return 0


def safe_pct(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator) * 100, 2)


def sum_values(data: dict[str, int], start: datetime.date, end: datetime.date) -> int:
    total = 0
    for raw_date, value in data.items():
        item_date = parse_date(raw_date)
        if item_date and start <= item_date <= end:
            total += int(value or 0)
    return total


def latest_report_path(app_key: str) -> Path | None:
    files = sorted(REPORTS_DIR.glob(f"{app_key}-downloads-*.json"))
    return files[-1] if files else None


def load_latest_report(app_key: str) -> dict[str, Any] | None:
    path = latest_report_path(app_key)
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def latest_metric_date(report: dict[str, Any]) -> datetime.date | None:
    dates: set[datetime.date] = set()
    for field in ["by_date", "impressions_by_date", "product_page_views_by_date"]:
        values = report.get(field)
        if isinstance(values, dict):
            for raw_date in values:
                parsed = parse_date(raw_date)
                if parsed:
                    dates.add(parsed)
    return max(dates) if dates else None


def window_metrics(report: dict[str, Any], days: int, end_date: datetime.date) -> dict[str, Any]:
    start_date = end_date - timedelta(days=days - 1)
    downloads = sum_values(report.get("by_date") or {}, start_date, end_date)
    impressions = sum_values(report.get("impressions_by_date") or {}, start_date, end_date)
    page_views = sum_values(report.get("product_page_views_by_date") or {}, start_date, end_date)
    return {
        "days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "downloads": downloads,
        "first_time_downloads": downloads_by_type(report, "First-time download", start_date, end_date),
        "impressions": impressions,
        "product_page_views": page_views,
        "page_view_rate": safe_pct(page_views, impressions),
        "avg_daily_downloads": round(downloads / days, 2),
        "avg_daily_impressions": round(impressions / days, 2),
        "avg_daily_product_page_views": round(page_views / days, 2),
    }


def downloads_by_type(report: dict[str, Any], download_type: str, start: datetime.date, end: datetime.date) -> int:
    total = 0
    for row in report.get("raw_standard_rows") or []:
        if row.get("Download Type") != download_type:
            continue
        row_date = parse_date(row.get("Date"))
        if row_date and start <= row_date <= end:
            total += count_field_value(row)
    return total


def build_history(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {"available": False, "error": "missing local report JSON"}
    end_date = latest_metric_date(report)
    if not end_date:
        return {"available": False, "error": "missing dated metrics in local report JSON"}
    current_7d = window_metrics(report, 7, end_date)
    previous_7d_end = end_date - timedelta(days=7)
    previous_7d = window_metrics(report, 7, previous_7d_end)
    current_30d = window_metrics(report, 30, end_date)
    return {
        "available": True,
        "source": "local reports raw App Store Analytics rows",
        "latest_metric_date": end_date.isoformat(),
        "current_7d": current_7d,
        "previous_7d": previous_7d,
        "current_30d": current_30d,
        "delta_7d": {
            "downloads": current_7d["downloads"] - previous_7d["downloads"],
            "first_time_downloads": current_7d["first_time_downloads"] - previous_7d["first_time_downloads"],
            "impressions": current_7d["impressions"] - previous_7d["impressions"],
            "product_page_views": current_7d["product_page_views"] - previous_7d["product_page_views"],
            "page_view_rate": rate_delta(current_7d.get("page_view_rate"), previous_7d.get("page_view_rate")),
        },
    }


def build_freshness(metrics: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    generated_at = metrics.get("generated_at")
    report_date = metrics.get("report_date")
    generated_age_hours = None
    if isinstance(generated_at, str) and generated_at:
        try:
            generated_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            generated_age_hours = round((now - generated_dt).total_seconds() / 3600, 2)
        except ValueError:
            generated_age_hours = None
    report_age_days = None
    parsed_report_date = parse_date(report_date)
    if parsed_report_date:
        report_age_days = (now.date() - parsed_report_date).days
    return {
        "checked_at": now.isoformat(),
        "generated_at": generated_at,
        "report_date": report_date,
        "generated_age_hours": generated_age_hours,
        "report_age_days": report_age_days,
        "is_generated_recent_72h": generated_age_hours is not None and generated_age_hours <= 72,
        "has_report_date": bool(parsed_report_date),
    }


def rate_delta(current: Any, previous: Any) -> float | None:
    if current is None or previous is None:
        return None
    return round(float(current) - float(previous), 2)


def new_funnel_bucket() -> dict[str, int]:
    return {
        "impressions": 0,
        "unique_impressions": 0,
        "product_page_views": 0,
        "unique_product_page_views": 0,
        "taps": 0,
        "unique_taps": 0,
        "first_time_downloads": 0,
        "downloads": 0,
    }


def add_rates(bucket: dict[str, Any]) -> dict[str, Any]:
    bucket["page_view_rate"] = safe_pct(bucket["product_page_views"], bucket["unique_impressions"] or bucket["impressions"])
    bucket["tap_rate"] = safe_pct(bucket["taps"], bucket["unique_impressions"] or bucket["impressions"])
    bucket["download_rate"] = safe_pct(bucket["first_time_downloads"], bucket["unique_impressions"] or bucket["impressions"])
    return bucket


def funnel_by_dimension(report: dict[str, Any] | None, dimension: str, limit: int = 10) -> dict[str, Any]:
    if not report:
        return {"available": False, "error": "missing local report JSON"}
    buckets: dict[str, dict[str, int]] = defaultdict(new_funnel_bucket)
    for row in report.get("raw_engagement_rows") or []:
        key = row.get(dimension) or "(empty)"
        event_field = EVENT_TO_FIELD.get(row.get("Event") or "")
        if not event_field:
            continue
        buckets[key][event_field] += count_field_value(row)
        if event_field == "impressions":
            buckets[key]["unique_impressions"] += count_field_value(row, "Unique Counts")
        elif event_field == "product_page_views":
            buckets[key]["unique_product_page_views"] += count_field_value(row, "Unique Counts")
        elif event_field == "taps":
            buckets[key]["unique_taps"] += count_field_value(row, "Unique Counts")
    for row in report.get("raw_standard_rows") or []:
        key = row.get(dimension) or "(empty)"
        buckets[key]["downloads"] += count_field_value(row)
        if row.get("Download Type") == "First-time download":
            buckets[key]["first_time_downloads"] += count_field_value(row)
    rows = [add_rates({"name": key, **value}) for key, value in buckets.items()]
    rows = sorted(
        rows,
        key=lambda item: (
            -int(item.get("impressions") or 0),
            -int(item.get("product_page_views") or 0),
            -int(item.get("first_time_downloads") or 0),
            str(item.get("name") or ""),
        ),
    )
    return {
        "available": bool(rows),
        "dimension": dimension,
        "limit": limit,
        "rows": rows[:limit],
        "omitted_count": max(len(rows) - limit, 0),
    }


def compact_review(item: dict[str, Any]) -> dict[str, Any]:
    attrs = item.get("attributes") or {}
    return {
        "id": item.get("id"),
        "rating": attrs.get("rating"),
        "title": attrs.get("title"),
        "body": attrs.get("body"),
        "reviewer_nickname": attrs.get("reviewerNickname"),
        "territory": attrs.get("territory"),
        "created_date": attrs.get("createdDate"),
    }


def fetch_reviews(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    path = f"/apps/{app_id}/customerReviews?limit=50&sort=-createdDate"
    resp, error = safe_get(client, path)
    if error:
        return {"available": False, "source": "App Store Connect customerReviews", "error": error}
    reviews = [compact_review(item) for item in (resp or {}).get("data") or []]
    low = [item for item in reviews if int(item.get("rating") or 0) <= 2]
    high = [item for item in reviews if int(item.get("rating") or 0) >= 4]
    ratings = [int(item["rating"]) for item in reviews if item.get("rating") is not None]
    return {
        "available": True,
        "source": "App Store Connect customerReviews",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "recent_count": len(reviews),
        "recent_average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "recent_low_rating_count": len(low),
        "recent_high_rating_count": len(high),
        "recent_low_rating_reviews": low[:5],
        "recent_high_rating_reviews": high[:5],
        "recent_reviews": reviews[:10],
    }


def included_by_type_and_id(resp: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(item.get("type") or ""), str(item.get("id") or "")): item
        for item in resp.get("included") or []
        if item.get("type") and item.get("id")
    }


def relationship_items(resource: dict[str, Any], name: str) -> list[dict[str, str]]:
    data = ((resource.get("relationships") or {}).get(name) or {}).get("data")
    if not data:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def fetch_live_metadata(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    path = (
        f"/apps/{app_id}/appInfos"
        "?include=appInfoLocalizations,primaryCategory,secondaryCategory"
        "&fields[appInfos]=appInfoLocalizations,primaryCategory,secondaryCategory"
        "&fields[appInfoLocalizations]=locale,name,subtitle,privacyPolicyUrl,privacyPolicyText"
        "&limit=50"
    )
    resp, error = safe_get(client, path)
    if error:
        return {"available": False, "source": "App Store Connect appInfos", "error": error}
    included = included_by_type_and_id(resp or {})
    localizations = []
    categories = []
    for info in (resp or {}).get("data") or []:
        for relation in ["primaryCategory", "secondaryCategory"]:
            for ref in relationship_items(info, relation):
                item = included.get((str(ref.get("type") or ""), str(ref.get("id") or "")))
                if item:
                    categories.append({"relation": relation, "id": item.get("id"), "attributes": item.get("attributes") or {}})
        for ref in relationship_items(info, "appInfoLocalizations"):
            item = included.get((str(ref.get("type") or ""), str(ref.get("id") or "")))
            if not item:
                continue
            attrs = item.get("attributes") or {}
            localizations.append({
                "id": item.get("id"),
                "locale": attrs.get("locale"),
                "name": attrs.get("name"),
                "subtitle": attrs.get("subtitle"),
                "privacy_policy_url": attrs.get("privacyPolicyUrl"),
                "has_privacy_policy_text": bool(attrs.get("privacyPolicyText")),
            })
    return {
        "available": True,
        "source": "App Store Connect appInfos",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "localizations": localizations,
        "categories": categories,
    }


def localization_ids_from_review_pipeline(app: dict[str, Any]) -> list[dict[str, str]]:
    ids = []
    for version in ((app.get("review_pipeline") or {}).get("versions") or []):
        for loc in version.get("localizations") or []:
            loc_id = loc.get("id")
            if loc_id:
                ids.append({
                    "localization_id": loc_id,
                    "locale": loc.get("locale") or "",
                    "version_string": version.get("version_string") or "",
                    "app_store_state": version.get("app_store_state") or "",
                })
    return ids


def fetch_screenshot_sets(client: asc.ASCClient, localization_id: str) -> dict[str, Any]:
    path = (
        f"/appStoreVersionLocalizations/{localization_id}/appScreenshotSets"
        "?include=appScreenshots"
        "&fields[appScreenshotSets]=screenshotDisplayType,appScreenshots"
        "&fields[appScreenshots]=fileName,fileSize,assetDeliveryState,sourceFileChecksum,imageAsset"
        "&limit=50&limit[appScreenshots]=50"
    )
    resp, error = safe_get(client, path)
    if error:
        return {"available": False, "error": error}
    included = included_by_type_and_id(resp or {})
    sets = []
    for screenshot_set in (resp or {}).get("data") or []:
        attrs = screenshot_set.get("attributes") or {}
        screenshots = []
        for ref in relationship_items(screenshot_set, "appScreenshots"):
            item = included.get((str(ref.get("type") or ""), str(ref.get("id") or "")))
            if not item:
                continue
            shot_attrs = item.get("attributes") or {}
            image_asset = shot_attrs.get("imageAsset") if isinstance(shot_attrs.get("imageAsset"), dict) else {}
            screenshots.append({
                "id": item.get("id"),
                "file_name": shot_attrs.get("fileName"),
                "file_size": shot_attrs.get("fileSize"),
                "asset_delivery_state": shot_attrs.get("assetDeliveryState"),
                "source_file_checksum": shot_attrs.get("sourceFileChecksum"),
                "image_asset": image_asset,
            })
        sets.append({
            "id": screenshot_set.get("id"),
            "screenshot_display_type": attrs.get("screenshotDisplayType"),
            "screenshot_count": len(screenshots),
            "screenshots": screenshots,
        })
    return {"available": True, "sets": sets}


def fetch_screenshot_inventory(client: asc.ASCClient, app: dict[str, Any]) -> dict[str, Any]:
    localization_refs = localization_ids_from_review_pipeline(app)
    if not localization_refs:
        return {
            "available": False,
            "source": "App Store Connect appScreenshotSets",
            "error": "missing appStoreVersionLocalization ids from review_pipeline",
        }
    localizations = []
    errors = []
    for ref in localization_refs:
        payload = fetch_screenshot_sets(client, ref["localization_id"])
        if not payload.get("available"):
            errors.append({**ref, "error": payload.get("error")})
            continue
        total = sum(item.get("screenshot_count") or 0 for item in payload.get("sets") or [])
        localizations.append({**ref, "screenshot_total": total, "sets": payload.get("sets") or []})
    return {
        "available": bool(localizations),
        "source": "App Store Connect appScreenshotSets via review_pipeline localization ids",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "localizations": localizations,
        "errors": errors,
    }


def quality_signals(app: dict[str, Any]) -> dict[str, Any]:
    sales = app.get("sales") or {}
    paid_units = int(sales.get("paid_units") or 0)
    refunds = int(sales.get("refund_units") or 0)
    return {
        "refund_rate": safe_pct(refunds, paid_units + refunds),
        "has_paid_signal": bool(paid_units or sales.get("developer_proceeds")),
        "has_review_signal": bool((app.get("reviews") or {}).get("recent_count")),
        "has_source_funnel": bool((app.get("funnel_by_source") or {}).get("available")),
        "has_territory_funnel": bool((app.get("funnel_by_territory") or {}).get("available")),
    }


def unavailable_api_payload(source: str, error: str) -> dict[str, Any]:
    return {"available": False, "source": source, "error": error}


def enrich(metrics: dict[str, Any], client: asc.ASCClient | None = None, api_error: str | None = None) -> dict[str, Any]:
    metrics["analysis_instruction"] = ANALYSIS_INSTRUCTION
    metrics["freshness"] = build_freshness(metrics)
    metrics["market_intelligence_source"] = {
        "history": "local reports/*.json raw App Store Analytics rows",
        "source_and_territory_funnels": "local raw engagement/download rows grouped by Source Type and Territory",
        "reviews": "App Store Connect customerReviews endpoint, best effort",
        "metadata": "App Store Connect appInfos endpoint plus review_pipeline version localizations, best effort",
        "screenshots": "App Store Connect appScreenshotSets endpoint via appStoreVersionLocalization ids, best effort",
        "limitations": [
            "Sales source is not attributable to App Store discovery source.",
            "Screenshot inventory stores counts and file metadata, not OCR or visual quality.",
            "Customer review availability can vary by platform, territory, account permissions and review volume.",
        ],
    }
    if api_error:
        metrics["market_intelligence_source"]["api_status"] = {"available": False, "error": api_error}
    for app in metrics.get("apps", []):
        report = load_latest_report(app.get("key") or "")
        app["history"] = build_history(report)
        app["funnel_by_source"] = funnel_by_dimension(report, "Source Type")
        app["funnel_by_territory"] = funnel_by_dimension(report, "Territory")
        app_id = app.get("app_id") or ""
        if app_id and client:
            app["reviews"] = fetch_reviews(client, app_id)
            app["metadata"] = fetch_live_metadata(client, app_id)
            app["screenshot_inventory"] = fetch_screenshot_inventory(client, app)
        elif app_id and api_error:
            app["reviews"] = unavailable_api_payload("App Store Connect customerReviews", api_error)
            app["metadata"] = unavailable_api_payload("App Store Connect appInfos", api_error)
            app["screenshot_inventory"] = unavailable_api_payload("App Store Connect appScreenshotSets", api_error)
        else:
            missing = {"available": False, "error": "missing app_id"}
            app["reviews"] = dict(missing)
            app["metadata"] = dict(missing)
            app["screenshot_inventory"] = dict(missing)
        app["quality_signals"] = quality_signals(app)
    return metrics


def main() -> None:
    metrics = load_metrics()
    try:
        config = asc.load_config()
        client = asc.ASCClient(config)
        save_metrics(enrich(metrics, client))
    except Exception as exc:
        save_metrics(enrich(metrics, None, str(exc)))


if __name__ == "__main__":
    main()
