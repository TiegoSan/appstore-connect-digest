from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import enrich_pricing_metrics
import enrich_review_metrics
import enrich_market_metrics
import enrich_store_capabilities
import daily_appstore_digest
import assemble_latest_digest
import send_latest_digest
import appstore_dashboard


class PipelineTests(unittest.TestCase):
    def test_dashboard_payload_compacts_metrics_and_builds_alerts(self) -> None:
        payload = appstore_dashboard.build_dashboard_payload(
            {
                "generated_at": "2026-06-08T10:00:00+00:00",
                "report_date": "2026-06-07",
                "metrics_scope": "report_date",
                "freshness": {"report_age_days": 1},
                "apps": [
                    {
                        "key": "coupez",
                        "name": "Coupez!",
                        "app_id": "123",
                        "bundle_id": "com.gogolabs.coupez",
                        "sku": "coupez",
                        "downloads": 0,
                        "first_time_downloads": 0,
                        "impressions": 120,
                        "product_page_views": 0,
                        "taps": 0,
                        "downloads_report_date_available": True,
                        "engagement_report_date_available": True,
                        "history": {
                            "available": True,
                            "current_7d": {"downloads": 1, "impressions": 120, "product_page_views": 0},
                            "previous_7d": {"downloads": 8},
                        },
                        "sales": {"available": True, "paid_units": 1, "refund_units": 1, "developer_proceeds": 4.2, "refund_rate": 50.0},
                        "reviews": {"available": True, "recent_low_rating_count": 0},
                        "review_pipeline": {
                            "available": True,
                            "has_pending_version": True,
                            "has_blocking_pipeline_change": True,
                            "blocking_recommendation_states": ["WAITING_FOR_REVIEW"],
                            "versions": [
                                {
                                    "id": "private-version-id",
                                    "version_string": "2.0",
                                    "app_store_state": "WAITING_FOR_REVIEW",
                                    "build": {"version": "42"},
                                    "localizations": [
                                        {
                                            "locale": "fr-FR",
                                            "description": "Description App Store complete.",
                                            "keywords": "audio,conform,aaf",
                                            "promotional_text": "Promo courte",
                                            "marketing_url": "https://gogolabs.fr",
                                            "support_url": "https://gogolabs.fr/support.html",
                                            "whats_new": "Nouveautes.",
                                        }
                                    ],
                                },
                                {
                                    "id": "live-version-id",
                                    "version_string": "1.0",
                                    "app_store_state": "READY_FOR_SALE",
                                    "build": {"version": "41"},
                                }
                            ],
                        },
                        "funnel_by_source": {"available": True, "rows": [{"name": "App Store search", "impressions": 120}]},
                        "funnel_by_territory": {"available": True, "rows": [{"name": "FR", "impressions": 20}]},
                        "pricing": {
                            "available": True,
                            "base_territory": "FRA",
                            "base_price": {"customer_price": "0.0", "currency": "EUR", "proceeds": "0.0"},
                        },
                        "metadata": {
                            "available": True,
                            "localizations": [{"locale": "fr-FR", "name": "Coupez!", "subtitle": "Conform audio"}],
                            "categories": [{"relation": "primaryCategory", "id": "MUSIC", "attributes": {"name": "Music"}}],
                        },
                        "screenshot_inventory": {
                            "available": True,
                            "localizations": [
                                {
                                    "locale": "fr-FR",
                                    "version_string": "2.0",
                                    "app_store_state": "WAITING_FOR_REVIEW",
                                    "screenshot_total": 3,
                                    "sets": [
                                        {
                                            "screenshot_display_type": "APP_IPHONE_65",
                                            "screenshot_count": 3,
                                            "screenshots": [
                                                {
                                                    "id": "shot-1",
                                                    "file_name": "01.png",
                                                    "image_asset": {
                                                        "templateUrl": "https://example.test/image/{w}x{h}bb.{f}",
                                                        "width": 2880,
                                                        "height": 1800,
                                                    },
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        },
                        "in_app_purchases": {
                            "available": True,
                            "total": 1,
                            "returned": 1,
                            "items": [{"name": "Unlimited", "product_id": "coupez.unlimited", "state": "APPROVED"}],
                        },
                        "subscriptions": {
                            "available": True,
                            "groups": {"total": 1, "items": [{"reference_name": "Pro", "subscriptions_count": 1}]},
                            "subscriptions": {
                                "items": [{"name": "Monthly", "product_id": "coupez.monthly", "state": "APPROVED"}]
                            },
                        },
                        "game_center": {"available": True, "state": "ENABLED", "leaderboards_count": 1},
                    }
                ],
            }
        )

        self.assertEqual(payload["totals"]["impressions"], 120)
        self.assertEqual(len(payload["apps"][0]["history"]["time_series"]["rows"]), 90)
        self.assertEqual(payload["apps"][0]["review_pipeline"]["versions"][0]["version_string"], "2.0")
        self.assertEqual(payload["apps"][0]["metadata"]["localizations"][0]["locale"], "fr-FR")
        self.assertEqual(payload["apps"][0]["metadata"]["localizations"][0]["description"], "Description App Store complete.")
        self.assertEqual(payload["apps"][0]["metadata"]["localizations"][0]["keywords"], "audio,conform,aaf")
        self.assertEqual(payload["apps"][0]["metadata"]["localizations"][0]["version_string"], "2.0")
        self.assertEqual(payload["apps"][0]["screenshot_inventory"]["screenshot_total"], 3)
        self.assertEqual(
            payload["apps"][0]["screenshot_inventory"]["localizations"][0]["sets"][0]["screenshots"][0]["display_url"],
            "https://example.test/image/720x450bb.png",
        )
        self.assertEqual(payload["apps"][0]["pricing"]["base_price"]["currency"], "EUR")
        self.assertEqual(payload["apps"][0]["in_app_purchases"]["items"][0]["product_id"], "coupez.unlimited")
        self.assertEqual(payload["apps"][0]["subscriptions"]["groups"][0]["reference_name"], "Pro")
        self.assertEqual(payload["apps"][0]["game_center"]["leaderboards_count"], 1)
        self.assertNotIn("private-version-id", json.dumps(payload))
        self.assertGreaterEqual(len(payload["alerts"]), 3)
        self.assertEqual(payload["alerts"][0]["level"], "critical")

    def test_alert_email_skips_info_only_alerts(self) -> None:
        payload = {
            "report_date": "2026-06-07",
            "alerts": [{"level": "info", "title": "Info", "detail": "Detail"}],
        }

        import send_appstore_alerts

        html = send_appstore_alerts.render_alert_email(
            {"report_date": payload["report_date"], "alerts": [{"level": "warning", "title": "Signal", "detail": "Détail"}]}
        )

        self.assertIn("Signal", html)
        self.assertNotIn("Info", html)

    def test_review_pipeline_compacts_pending_versions_and_redacts_review_details(self) -> None:
        class FakeClient:
            def get(self, path: str) -> dict:
                self.path = path
                return {
                    "data": [
                        {
                            "type": "appStoreVersions",
                            "id": "live-version",
                            "attributes": {
                                "platform": "MAC_OS",
                                "versionString": "1.0",
                                "appStoreState": "READY_FOR_SALE",
                                "createdDate": "2026-06-01T10:00:00Z",
                            },
                        },
                        {
                            "type": "appStoreVersions",
                            "id": "review-version",
                            "attributes": {
                                "platform": "MAC_OS",
                                "versionString": "1.1",
                                "appStoreState": "IN_REVIEW",
                                "appVersionState": "IN_REVIEW",
                                "reviewType": "APP_STORE",
                                "releaseType": "MANUAL",
                                "createdDate": "2026-06-08T10:00:00Z",
                            },
                            "relationships": {
                                "build": {"data": {"type": "builds", "id": "build-1"}},
                                "appStoreVersionLocalizations": {
                                    "data": [{"type": "appStoreVersionLocalizations", "id": "loc-1"}]
                                },
                                "appStoreReviewDetail": {
                                    "data": {"type": "appStoreReviewDetails", "id": "review-detail-1"}
                                },
                            },
                        },
                    ],
                    "included": [
                        {
                            "type": "builds",
                            "id": "build-1",
                            "attributes": {"version": "42", "uploadedDate": "2026-06-08T09:00:00Z"},
                        },
                        {
                            "type": "appStoreVersionLocalizations",
                            "id": "loc-1",
                            "attributes": {
                                "locale": "fr-FR",
                                "description": "Nouvelle description deja soumise.",
                                "promotionalText": "Promo pipeline",
                                "whatsNew": "Nouveaux screenshots et promesse clarifiee.",
                                "keywords": "audio,pro tools",
                            },
                        },
                        {
                            "type": "appStoreReviewDetails",
                            "id": "review-detail-1",
                            "attributes": {
                                "contactEmail": "private@example.com",
                                "demoAccountName": "demo-user",
                                "demoAccountPassword": "secret",
                                "notes": "private notes",
                            },
                        },
                    ],
                }

        pipeline = enrich_review_metrics.fetch_review_pipeline(FakeClient(), "123")
        rendered = json.dumps(pipeline)

        self.assertTrue(pipeline["available"])
        self.assertTrue(pipeline["has_pending_version"])
        self.assertTrue(pipeline["has_blocking_pipeline_change"])
        self.assertEqual(pipeline["versions"][0]["id"], "review-version")
        self.assertEqual(pipeline["versions"][0]["build"]["version"], "42")
        self.assertEqual(pipeline["versions"][0]["localizations"][0]["promotional_text"], "Promo pipeline")
        self.assertIn("demoAccountPassword", pipeline["versions"][0]["app_store_review_detail"]["redacted_fields"])
        self.assertNotIn("secret", rendered)
        self.assertNotIn("private@example.com", rendered)

    def test_latest_data_date_uses_latest_apple_metric_date(self) -> None:
        apps = [
            daily_appstore_digest.AppDigest(
                "one",
                "One",
                None,
                None,
                {
                    "by_date": {"2026-06-01": 1},
                    "impressions_by_date": {"2026-06-03": 10},
                },
                None,
            ),
            daily_appstore_digest.AppDigest(
                "two",
                "Two",
                None,
                None,
                {"product_page_views_by_date": {"2026-06-02": 2}},
                None,
            ),
        ]

        self.assertEqual(daily_appstore_digest.latest_data_date(apps), "2026-06-03")

    def test_send_latest_digest_subject_uses_metrics_report_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            metrics_path = Path(temp_dir) / "latest-metrics.json"
            metrics_path.write_text(json.dumps({"report_date": "2026-06-03"}), encoding="utf-8")

            report_date = send_latest_digest.report_date_for_subject(
                "<title>Gogo Labs Daily Business Digest - 2026-06-07</title>",
                metrics_path,
            )

        self.assertEqual(report_date, "2026-06-03")

    def test_assemble_injects_chatgpt_review_without_dynamic_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            strategy_dir = root / "strategy"
            strategy_dir.mkdir()
            html_path = strategy_dir / "latest-digest.html"
            html_path.write_text(
                """<!doctype html>
<html>
<head><style>
  body { color:#582B36; }
  </style></head>
<body>
  <div class="wrap">
    <h1>Compte rendu App Store Connect</h1>
    <div class="cards"></div>
    <h2>Synthese executive</h2>
    <h2>Analyse</h2>
    <p>Base analysis</p>
    <h2>Erreurs</h2>
    <p>No errors</p>
    <p class="footer">Genere depuis local. URLs signees absentes.</p>
  </div>
</body>
</html>
""",
                encoding="utf-8",
            )
            (strategy_dir / "latest-metrics.json").write_text(
                json.dumps(
                    {
                        "totals": {"impressions": 100, "product_page_views": 2},
                        "apps": [
                            {"key": "glass", "name": "Glass Master", "impressions": 100, "product_page_views": 2, "downloads": 1}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (strategy_dir / "strategic-review.md").write_text(
                "# Review\n\nIntro\n\n## Synthèse exécutive stratégique\n\nRemove me\n\n## Segment A\n\n- Action\n\n## Segment B\n\nBody",
                encoding="utf-8",
            )

            assemble_latest_digest.assemble(root)
            html = html_path.read_text(encoding="utf-8")

        self.assertIn("Gogo Labs Daily Business Digest", html)
        self.assertIn("cid:gogolabs-logo", html)
        self.assertNotIn("<h2>Synthèse exécutive</h2>", html)
        self.assertIn("Remove me", html)
        self.assertNotIn("Réflexion stratégique", html)
        self.assertIn('<div class="strategy-review" aria-label="Review">', html)
        self.assertNotIn("strategy-review-title", html)
        self.assertNotIn(">Review</h2>", html)
        self.assertNotIn('<section class="strategy-block" aria-label="Introduction">', html)
        self.assertIn('<section class="strategy-block" aria-label="Synthèse exécutive stratégique">', html)
        self.assertIn('<section class="strategy-block" aria-label="Segment A">', html)
        self.assertIn('<section class="strategy-block" aria-label="Segment B">', html)
        self.assertEqual(html.count('class="strategy-block"'), 3)
        self.assertNotIn("<h2>1. ", html)
        self.assertNotIn("<h3>2.1. ", html)
        self.assertIn("<li>Action</li>", html)
        self.assertNotIn('class="decision-panel"', html)
        self.assertNotIn("Décision du jour", html)
        self.assertGreater(html.find('class="cards"'), html.find("Gogo Labs Daily Business Digest"))
        self.assertLess(html.find('class="cards"'), html.find('class="strategy-review"'))
        self.assertNotIn('class="strategy-memory"', html)
        self.assertNotIn("Signaux par app", html)
        self.assertNotIn("Base analysis", html)

    def test_rendered_colors_follow_gogolabs_site_palette(self) -> None:
        apps = [
            daily_appstore_digest.AppDigest(
                "one",
                "Visible",
                None,
                None,
                {
                    "standard_total": 4,
                    "first_time_downloads": 2,
                    "impressions": 10,
                    "product_page_views": 1,
                    "taps": 1,
                    "page_view_rate": 10.0,
                    "tap_rate": 10.0,
                },
                None,
                None,
            )
        ]

        html = daily_appstore_digest.render_html(apps, "2026-06-06")
        colors = set(re.findall(r"#[0-9A-Fa-f]{6}", html))

        self.assertIn("#f2f1ed", colors)
        self.assertIn("#faf9f4", colors)
        self.assertIn("#161a20", colors)
        self.assertIn("#111827", colors)
        self.assertIn("#242a36", colors)
        self.assertIn("#ffffff", colors)
        self.assertIn("#6a89ff", colors)
        self.assertIn("#ece8e0", colors)

    def test_bar_rows_hides_zero_values(self) -> None:
        apps = [
            daily_appstore_digest.AppDigest("one", "Visible", None, None, {"standard_total": 4}, None, None),
            daily_appstore_digest.AppDigest("zero", "Hidden", None, None, {"standard_total": 0}, None, None),
        ]

        html = daily_appstore_digest.bar_rows(apps, "standard_total")

        self.assertIn("Visible", html)
        self.assertNotIn("Hidden", html)
        self.assertIn("background:#6a89ff", html)
        self.assertIn('class="bar-track"', html)

    def test_render_table_hides_empty_columns(self) -> None:
        apps = [
            daily_appstore_digest.AppDigest(
                "one",
                "Visible",
                None,
                None,
                {"standard_total": 4, "first_time_downloads": 0, "impressions": 0, "product_page_views": 0, "taps": 0},
                None,
                None,
            )
        ]

        header = daily_appstore_digest.render_table_header(apps)
        body = daily_appstore_digest.render_table(apps)

        self.assertIn("Downloads", header)
        self.assertNotIn("Delta", header)
        self.assertNotIn("First-time", header)
        self.assertNotIn("Impressions", header)
        self.assertIn("<td>Visible</td>", body)
        self.assertIn('<td class="num">4</td>', body)

    def test_render_html_includes_global_available_recap_and_graphs(self) -> None:
        apps = [
            daily_appstore_digest.AppDigest(
                "one",
                "Visible",
                None,
                None,
                {
                    "standard_total": 1,
                    "impressions": 2,
                    "downloads_total_available": 10,
                    "first_time_downloads_total_available": 7,
                    "impressions_total_available": 100,
                    "product_page_views_total_available": 9,
                    "taps_total_available": 3,
                },
                None,
                None,
            )
        ]

        html = daily_appstore_digest.render_html(apps, "2026-06-07")

        self.assertIn("Récap global disponible", html)
        self.assertIn("Downloads globaux", html)
        self.assertIn('<div class="value">10</div>', html)
        self.assertIn("Graphiques globaux disponibles", html)
        self.assertIn("Téléchargements globaux disponibles par app", html)
        self.assertLess(html.find('<div class="value">1</div>'), html.find("Récap global disponible"))
        self.assertLess(html.find("Récap global disponible"), html.find("Tableau principal"))

    def test_build_message_attaches_logo_inline(self) -> None:
        msg = daily_appstore_digest.build_message(
            "gautier@gogolabs.fr",
            "Test",
            '<html><body><img src="cid:gogolabs-logo"></body></html>',
        )

        rendered = msg.as_string()
        self.assertIn("Gogo Labs Daily Business Digest", rendered)
        self.assertIn("Content-ID: <gogolabs-logo>", rendered)

    def test_aggregate_sales_matches_sku_and_refunds(self) -> None:
        rows = [
            {"SKU": "APP", "Units": "2", "Developer Proceeds": "5.50", "Customer Price": "9.99", "Customer Currency": "USD"},
            {"SKU": "APP", "Units": "-1", "Developer Proceeds": "-2.00", "Customer Price": "9.99", "Customer Currency": "USD"},
            {"SKU": "OTHER", "Units": "10", "Developer Proceeds": "10.00", "Customer Currency": "EUR"},
        ]

        sales = enrich_pricing_metrics.aggregate_sales(rows, "APP")

        self.assertTrue(sales["available"])
        self.assertEqual(sales["rows"], 2)
        self.assertEqual(sales["paid_units"], 1)
        self.assertEqual(sales["refund_units"], 1)
        self.assertEqual(sales["developer_proceeds"], 3.5)
        self.assertEqual(sales["currencies"], ["USD"])

    def test_unavailable_sales_preserves_previous_available_values(self) -> None:
        previous = {"available": True, "paid_units": 2, "developer_proceeds": 0.0}
        refresh = {"available": False, "error": "APPSTORE_VENDOR_NUMBER/ASC_VENDOR_NUMBER missing"}

        sales = enrich_pricing_metrics.unavailable_sales_payload(refresh, previous)

        self.assertTrue(sales["available"])
        self.assertTrue(sales["stale"])
        self.assertEqual(sales["paid_units"], 2)
        self.assertEqual(sales["refresh_status"]["error"], "APPSTORE_VENDOR_NUMBER/ASC_VENDOR_NUMBER missing")

    def test_public_sales_status_removes_vendor_number(self) -> None:
        vendor = "12345678"
        status = enrich_pricing_metrics.public_sales_status(
            {
                "available": True,
                "vendor_number": vendor,
                "report_date": "2026-06-05",
                "rows": [{"SKU": "APP"}],
                "errors_by_date": {"2026-06-04": f"bad vendorNumber={vendor}"},
            },
            vendor,
        )

        rendered = json.dumps(status)
        self.assertNotIn("vendor_number", status)
        self.assertNotIn(vendor, rendered)
        self.assertNotIn("rows", status)
        self.assertIn("[redacted]", rendered)

    def test_fetch_pricing_adds_base_price_rows(self) -> None:
        class FakeClient:
            def get(self, path: str) -> dict:
                if path.startswith("/apps/123/appPriceSchedule"):
                    return {
                        "data": {
                            "id": "123",
                            "relationships": {
                                "baseTerritory": {"data": {"type": "territories", "id": "FRA"}},
                                "manualPrices": {"data": [{"type": "appPrices", "id": "price-1"}], "meta": {"paging": {"total": 1, "limit": 50}}},
                                "automaticPrices": {"data": [], "meta": {"paging": {"total": 0, "limit": 50}}},
                            },
                        },
                        "included": [],
                    }
                if "/appPriceSchedules/123/manualPrices" in path:
                    return {
                        "data": [
                            {
                                "type": "appPrices",
                                "id": "price-1",
                                "attributes": {"manual": True},
                                "relationships": {
                                    "appPricePoint": {"data": {"type": "appPricePoints", "id": "point-1"}},
                                    "territory": {"data": {"type": "territories", "id": "FRA"}},
                                },
                            }
                        ],
                        "included": [
                            {"type": "appPricePoints", "id": "point-1", "attributes": {"customerPrice": "4.99", "proceeds": "3.50"}},
                            {"type": "territories", "id": "FRA", "attributes": {"currency": "EUR"}},
                        ],
                        "meta": {"paging": {"total": 1}},
                    }
                if "/appPriceSchedules/123/automaticPrices" in path:
                    return {"data": [], "included": [], "meta": {"paging": {"total": 0}}}
                raise AssertionError(path)

        pricing = enrich_pricing_metrics.fetch_pricing(FakeClient(), "123")

        self.assertTrue(pricing["available"])
        self.assertEqual(pricing["base_price"]["customer_price"], "4.99")
        self.assertEqual(pricing["base_price"]["currency"], "EUR")

    def test_market_history_and_funnel_use_raw_report_rows(self) -> None:
        report = {
            "by_date": {
                "2026-06-01": 2,
                "2026-06-02": 1,
                "2026-06-07": 4,
                "2026-05-25": 9,
            },
            "impressions_by_date": {"2026-06-01": 10, "2026-06-07": 30, "2026-05-25": 5},
            "product_page_views_by_date": {"2026-06-01": 1, "2026-06-07": 6, "2026-05-25": 1},
            "raw_standard_rows": [
                {"Date": "2026-06-07", "Download Type": "First-time download", "Source Type": "App Store search", "Territory": "US", "Counts": "3"},
                {"Date": "2026-06-07", "Download Type": "Restore", "Source Type": "App Store search", "Territory": "US", "Counts": "1"},
                {"Date": "2026-05-25", "Download Type": "First-time download", "Source Type": "Browse", "Territory": "FR", "Counts": "9"},
            ],
            "raw_engagement_rows": [
                {"Event": "Impression", "Source Type": "App Store search", "Territory": "US", "Counts": "30", "Unique Counts": "20"},
                {"Event": "Page view", "Source Type": "App Store search", "Territory": "US", "Counts": "6", "Unique Counts": "5"},
                {"Event": "Tap", "Source Type": "App Store search", "Territory": "US", "Counts": "2", "Unique Counts": "2"},
            ],
        }

        history = enrich_market_metrics.build_history(report)
        funnel = enrich_market_metrics.funnel_by_dimension(report, "Source Type")

        self.assertTrue(history["available"])
        self.assertEqual(history["latest_metric_date"], "2026-06-07")
        self.assertEqual(history["current_7d"]["downloads"], 7)
        self.assertEqual(history["current_7d"]["first_time_downloads"], 3)
        self.assertEqual(history["delta_7d"]["downloads"], -2)
        self.assertTrue(funnel["available"])
        self.assertEqual(funnel["rows"][0]["name"], "App Store search")
        self.assertEqual(funnel["rows"][0]["impressions"], 30)
        self.assertEqual(funnel["rows"][0]["product_page_views"], 6)
        self.assertEqual(funnel["rows"][0]["first_time_downloads"], 3)
        self.assertEqual(funnel["rows"][0]["page_view_rate"], 30.0)

    def test_market_freshness_exposes_report_date_checks(self) -> None:
        freshness = enrich_market_metrics.build_freshness(
            {"generated_at": "2026-06-08T10:00:00+00:00", "report_date": "2026-06-07"}
        )

        self.assertTrue(freshness["has_report_date"])
        self.assertEqual(freshness["report_date"], "2026-06-07")
        self.assertIn("is_generated_recent_72h", freshness)

    def test_aggregate_sales_exposes_territory_breakdown_and_refund_rate(self) -> None:
        rows = [
            {"SKU": "APP", "Units": "3", "Developer Proceeds": "12.00", "Country Code": "US", "Customer Currency": "USD"},
            {"SKU": "APP", "Units": "-1", "Developer Proceeds": "-4.00", "Country Code": "US", "Customer Currency": "USD"},
            {"SKU": "APP", "Units": "1", "Developer Proceeds": "3.00", "Country Code": "FR", "Customer Currency": "EUR"},
        ]

        sales = enrich_pricing_metrics.aggregate_sales(rows, "APP")

        self.assertEqual(sales["paid_units"], 3)
        self.assertEqual(sales["refund_units"], 1)
        self.assertEqual(sales["refund_rate"], 25.0)
        self.assertEqual(sales["by_territory"][0]["territory"], "US")
        self.assertEqual(sales["by_territory"][0]["paid_units"], 2)
        self.assertEqual(sales["by_territory"][0]["refund_units"], 1)
        self.assertEqual(sales["by_territory"][0]["developer_proceeds"], 8.0)

    def test_screenshot_request_uses_valid_public_fields(self) -> None:
        class FakeClient:
            def get(self, path: str) -> dict:
                self.path = path
                return {"data": [], "included": []}

        client = FakeClient()
        payload = enrich_market_metrics.fetch_screenshot_sets(client, "loc-1")

        self.assertTrue(payload["available"])
        self.assertIn("fields[appScreenshots]=fileName,fileSize,assetDeliveryState,sourceFileChecksum,imageAsset", client.path)
        self.assertNotIn("uploaded", client.path)

    def test_store_capabilities_compacts_iap_subscriptions_and_game_center(self) -> None:
        class FakeClient:
            def __init__(self) -> None:
                self.paths = []

            def get(self, path: str) -> dict:
                self.paths.append(path)
                if "inAppPurchases" in path:
                    return {
                        "data": [
                            {
                                "type": "inAppPurchases",
                                "id": "iap-1",
                                "attributes": {
                                    "name": "Unlimited",
                                    "productId": "app.unlimited",
                                    "state": "APPROVED",
                                    "inAppPurchaseType": "NON_CONSUMABLE",
                                },
                            }
                        ],
                        "meta": {"paging": {"total": 1}},
                    }
                if "subscriptionGroups/group-1/subscriptions" in path:
                    return {
                        "data": [
                            {
                                "type": "subscriptions",
                                "id": "sub-1",
                                "attributes": {
                                    "name": "Monthly",
                                    "productId": "app.monthly",
                                    "state": "APPROVED",
                                    "subscriptionPeriod": "ONE_MONTH",
                                },
                            }
                        ]
                    }
                if "subscriptionGroups" in path:
                    return {
                        "data": [
                            {
                                "type": "subscriptionGroups",
                                "id": "group-1",
                                "attributes": {"referenceName": "Pro"},
                                "relationships": {"subscriptions": {"data": [{"type": "subscriptions", "id": "sub-1"}]}},
                            }
                        ],
                        "meta": {"paging": {"total": 1}},
                    }
                if "gameCenterDetail" in path:
                    return {
                        "data": {
                            "type": "gameCenterDetails",
                            "id": "gc-1",
                            "attributes": {"gameCenterState": "ENABLED"},
                            "relationships": {
                                "gameCenterLeaderboards": {"data": [{"type": "gameCenterLeaderboards", "id": "lb-1"}]},
                                "gameCenterAchievements": {"data": []},
                            },
                        }
                    }
                raise AssertionError(path)

        metrics = {"apps": [{"app_id": "123", "key": "app"}]}
        enriched = enrich_store_capabilities.enrich(metrics, FakeClient())
        app = enriched["apps"][0]

        self.assertEqual(app["in_app_purchases"]["items"][0]["product_id"], "app.unlimited")
        self.assertEqual(app["subscriptions"]["groups"]["items"][0]["reference_name"], "Pro")
        self.assertEqual(app["subscriptions"]["subscriptions"]["items"][0]["product_id"], "app.monthly")
        self.assertTrue(app["game_center"]["available"])
        self.assertEqual(app["game_center"]["leaderboards_count"], 1)


if __name__ == "__main__":
    unittest.main()
