from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import enrich_pricing_metrics
import enrich_review_metrics
import daily_appstore_digest
import assemble_latest_digest
import send_latest_digest


class PipelineTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
