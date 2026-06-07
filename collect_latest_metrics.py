#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import appstore_analytics as asc
import daily_appstore_digest as digest

ROOT = Path(__file__).resolve().parent
STRATEGY_DIR = ROOT / "strategy"
LATEST_METRICS_PATH = STRATEGY_DIR / "latest-metrics.json"


def metric(app: digest.AppDigest, field: str) -> int:
    return digest.metric(app, field)


def app_summary(app: digest.AppDigest) -> dict[str, Any]:
    data = app.data or {}
    profile = data.get("app", {})
    source = digest.top(data.get("impressions_by_source_type") or data.get("by_source_type") or {})
    territory = digest.top(data.get("impressions_by_territory") or data.get("by_territory") or {})
    device = digest.top(data.get("impressions_by_device") or data.get("by_device") or {})
    return {
        "key": app.key,
        "name": app.name,
        "app_id": profile.get("app_id"),
        "bundle_id": profile.get("bundle_id"),
        "sku": profile.get("sku"),
        "error": app.error,
        "downloads": metric(app, "standard_total"),
        "first_time_downloads": metric(app, "first_time_downloads"),
        "impressions": metric(app, "impressions"),
        "unique_impressions": metric(app, "unique_impressions"),
        "product_page_views": metric(app, "product_page_views"),
        "unique_product_page_views": metric(app, "unique_product_page_views"),
        "taps": metric(app, "taps"),
        "unique_taps": metric(app, "unique_taps"),
        "conversion_rate": data.get("conversion_rate"),
        "page_view_rate": data.get("page_view_rate"),
        "tap_rate": data.get("tap_rate"),
        "dominant_source": {"name": source[0], "count": source[1]},
        "dominant_territory": {"name": territory[0], "count": territory[1]},
        "dominant_device": {"name": device[0], "count": device[1]},
        "delta_downloads": digest.delta(app.data, app.previous_data, "standard_total"),
        "delta_first_time_downloads": digest.delta(app.data, app.previous_data, "first_time_downloads"),
        "delta_impressions": digest.delta(app.data, app.previous_data, "impressions"),
        "delta_product_page_views": digest.delta(app.data, app.previous_data, "product_page_views"),
        "delta_taps": digest.delta(app.data, app.previous_data, "taps"),
    }


def write_latest_metrics(apps: list[digest.AppDigest], report_date: str) -> None:
    STRATEGY_DIR.mkdir(exist_ok=True)
    summaries = [app_summary(app) for app in apps]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_date": report_date,
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
        },
        "apps": summaries,
        "analysis_instruction": "Produire une réflexion stratégique longue mais structurée: diagnostic funnel, priorités ventes, pricing, ASO, screenshots, promesse par app, focus pro vs consumer, actions concrètes.",
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
            apps.append(digest.AppDigest(key, app.get("name", key), None, None, None, None, str(exc)))
            print(f"{key}: ERROR {exc}")
    report_date = digest.latest_data_date(apps) or datetime.now().strftime("%Y-%m-%d")
    write_latest_metrics(apps, report_date)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect latest App Store metrics without rendering or sending email")
    parser.parse_args()
    collect()


if __name__ == "__main__":
    main()
