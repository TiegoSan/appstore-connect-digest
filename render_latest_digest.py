#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import daily_appstore_digest as digest

ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "strategy" / "latest-metrics.json"
DIGEST_DIR = ROOT / "reports" / "daily-digests"
LATEST_DIGEST_HTML_PATH = ROOT / "strategy" / "latest-digest.html"


def app_digest_from_summary(item: dict[str, Any]) -> digest.AppDigest:
    data = {
        "standard_total": item.get("downloads") or 0,
        "first_time_downloads": item.get("first_time_downloads") or 0,
        "impressions": item.get("impressions") or 0,
        "unique_impressions": item.get("unique_impressions") or 0,
        "product_page_views": item.get("product_page_views") or 0,
        "unique_product_page_views": item.get("unique_product_page_views") or 0,
        "taps": item.get("taps") or 0,
        "unique_taps": item.get("unique_taps") or 0,
        "conversion_rate": item.get("conversion_rate"),
        "page_view_rate": item.get("page_view_rate"),
        "tap_rate": item.get("tap_rate"),
        "engagement_available": bool(item.get("impressions") or item.get("product_page_views") or item.get("taps")),
        "by_app_version": {},
        "impressions_by_source_type": {},
        "impressions_by_territory": {},
        "impressions_by_device": {},
    }
    source = item.get("dominant_source") or {}
    territory = item.get("dominant_territory") or {}
    device = item.get("dominant_device") or {}
    if source.get("name"):
        data["impressions_by_source_type"] = {source.get("name"): source.get("count") or 0}
    if territory.get("name"):
        data["impressions_by_territory"] = {territory.get("name"): territory.get("count") or 0}
    if device.get("name"):
        data["impressions_by_device"] = {device.get("name"): device.get("count") or 0}
    previous = None
    return digest.AppDigest(
        key=item.get("key") or item.get("name") or "app",
        name=item.get("name") or item.get("key") or "App",
        latest_path=None,
        previous_path=None,
        data=data,
        previous_data=previous,
        error=item.get("error"),
    )


def main() -> None:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    report_date = metrics.get("report_date") or "latest"
    apps = [app_digest_from_summary(item) for item in metrics.get("apps", [])]
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    html = digest.render_html(apps, report_date)
    html_path = DIGEST_DIR / f"appstore-digest-{report_date.replace('-', '')}.html"
    html_path.write_text(html, encoding="utf-8")
    LATEST_DIGEST_HTML_PATH.write_text(html, encoding="utf-8")
    print(f"HTML {html_path}")
    print(f"LATEST {LATEST_DIGEST_HTML_PATH}")


if __name__ == "__main__":
    main()
