from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import enrich_pricing_metrics
import daily_appstore_digest
import postprocess_latest_digest


class PipelineTests(unittest.TestCase):
    def test_choose_focus_app_prefers_visible_low_conversion_app(self) -> None:
        metrics = {
            "apps": [
                {"name": "High Volume", "impressions": 100, "product_page_views": 60, "taps": 0},
                {"name": "Visible Opportunity", "impressions": 90, "product_page_views": 1, "taps": 2},
                {"name": "Invisible", "impressions": 0, "product_page_views": 0, "taps": 0},
            ]
        }

        focus = postprocess_latest_digest.choose_focus_app(metrics)

        self.assertIsNotNone(focus)
        self.assertEqual(focus["name"], "Visible Opportunity")

    def test_postprocess_injects_dynamic_decision_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            strategy_dir = root / "strategy"
            strategy_dir.mkdir()
            html_path = strategy_dir / "latest-digest.html"
            html_path.write_text(
                """<!doctype html>
<html>
<head><style>
  body { color:#111; }
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

            postprocess_latest_digest.postprocess(root)
            html = html_path.read_text(encoding="utf-8")

        self.assertIn("Glass Master", html)
        self.assertIn("Gogo Labs Daily Business Digest", html)
        self.assertIn("cid:gogolabs-logo", html)
        self.assertNotIn("<h2>Synthèse exécutive</h2>", html)
        self.assertIn("Remove me", html)
        self.assertNotIn("Réflexion stratégique", html)
        self.assertIn('<div class="strategy-review" aria-label="Review">', html)
        self.assertIn('<h2 class="strategy-review-title">Review</h2>', html)
        self.assertNotIn('<section class="strategy-block" aria-label="Introduction">', html)
        self.assertIn('<section class="strategy-block" aria-label="Synthèse exécutive stratégique">', html)
        self.assertIn('<section class="strategy-block" aria-label="Segment A">', html)
        self.assertIn('<section class="strategy-block" aria-label="Segment B">', html)
        self.assertEqual(html.count('class="strategy-block"'), 3)
        self.assertNotIn("<h2>1. ", html)
        self.assertNotIn("<h3>2.1. ", html)
        self.assertIn("<li>Action</li>", html)
        self.assertNotIn('class="strategy-memory"', html)
        self.assertNotIn("Signaux par app", html)
        self.assertNotIn("Base analysis", html)

    def test_bar_rows_hides_zero_values(self) -> None:
        apps = [
            daily_appstore_digest.AppDigest("one", "Visible", None, None, {"standard_total": 4}, None, None),
            daily_appstore_digest.AppDigest("zero", "Hidden", None, None, {"standard_total": 0}, None, None),
        ]

        html = daily_appstore_digest.bar_rows(apps, "standard_total")

        self.assertIn("Visible", html)
        self.assertNotIn("Hidden", html)
        self.assertIn("background:#", html)

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
