#!/usr/bin/env python3
"""Digest runner that stores latest metrics in the repo and injects strategic-review.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

import daily_appstore_digest as base

ROOT = Path(__file__).resolve().parent
STRATEGY_DIR = ROOT / "strategy"
LATEST_METRICS_PATH = STRATEGY_DIR / "latest-metrics.json"
STRATEGIC_REVIEW_PATH = STRATEGY_DIR / "strategic-review.md"
LATEST_DIGEST_HTML_PATH = STRATEGY_DIR / "latest-digest.html"
_ORIGINAL_RENDER_HTML = base.render_html


def metric(app: base.AppDigest, field: str) -> int:
    return base.metric(app, field)


def app_summary(app: base.AppDigest) -> dict[str, Any]:
    data = app.data or {}
    profile = data.get("app", {})
    source = base.top(data.get("impressions_by_source_type") or data.get("by_source_type") or {})
    territory = base.top(data.get("impressions_by_territory") or data.get("by_territory") or {})
    device = base.top(data.get("impressions_by_device") or data.get("by_device") or {})
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
        "delta_downloads": base.delta(app.data, app.previous_data, "standard_total"),
        "delta_first_time_downloads": base.delta(app.data, app.previous_data, "first_time_downloads"),
        "delta_impressions": base.delta(app.data, app.previous_data, "impressions"),
        "delta_product_page_views": base.delta(app.data, app.previous_data, "product_page_views"),
        "delta_taps": base.delta(app.data, app.previous_data, "taps"),
    }


def write_latest_metrics(apps: list[base.AppDigest], report_date: str) -> None:
    STRATEGY_DIR.mkdir(exist_ok=True)
    summaries = [app_summary(app) for app in apps]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_date": report_date,
        "positioning": {
            "brand": "GogoLabs",
            "goal": "Vendre les apps et construire un revenu logiciel independant.",
            "doctrine": "Transformer l'expertise de production en apps macOS premium qui economisent du temps, reduisent les erreurs et rendent les workflows creatifs plus controlables.",
        },
        "totals": {
            "downloads": sum(item["downloads"] for item in summaries),
            "first_time_downloads": sum(item["first_time_downloads"] for item in summaries),
            "impressions": sum(item["impressions"] for item in summaries),
            "product_page_views": sum(item["product_page_views"] for item in summaries),
            "taps": sum(item["taps"] for item in summaries),
        },
        "apps": summaries,
        "analysis_instruction": "Produire une reflexion strategique longue mais structuree: diagnostic funnel, priorites ventes, pricing, ASO, screenshots, promesse par app, focus pro vs consumer, actions concretes.",
    }
    LATEST_METRICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def markdown_to_html(markdown: str) -> str:
    html_lines = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("## ") or line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            title = line[3:] if line.startswith("## ") else line[2:]
            html_lines.append(f"<h2>{escape(title)}</h2>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{escape(line[2:])}</li>")
        else:
            html_lines.append(f"<p>{escape(line)}</p>")
    if in_list:
        html_lines.append("</ul>")
    html = "\n".join(html_lines)
    return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)


def strategic_review_html() -> str:
    if not STRATEGIC_REVIEW_PATH.exists():
        return """
        <div class="strategy-memory">
          <p>Aucune analyse strategique n'est encore disponible.</p>
          <p>L'analyse planifiee doit lire strategy/latest-metrics.json puis remplacer strategy/strategic-review.md.</p>
        </div>
        """
    markdown = STRATEGIC_REVIEW_PATH.read_text(encoding="utf-8").strip()
    return f"""
    <div class="strategy-memory">{markdown_to_html(markdown)}</div>
    """


def write_latest_digest_html(html: str) -> None:
    STRATEGY_DIR.mkdir(exist_ok=True)
    LATEST_DIGEST_HTML_PATH.write_text(html, encoding="utf-8")


def render_html(apps: list[base.AppDigest], report_date: str) -> str:
    write_latest_metrics(apps, report_date)
    html = _ORIGINAL_RENDER_HTML(apps, report_date)
    css = """
    .strategy-memory { background:#fff; border:1px solid #deded8; border-left:5px solid #4d5bd1; border-radius:8px; padding:14px 16px; }
    .strategy-memory h2 { border:0; margin:18px 0 8px; padding:0; }
    .strategy-memory h3 { margin:16px 0 8px; font-size:15px; }
    """
    html = html.replace("  </style>", f"{css}\n  </style>")
    html = html.replace("    <h2>Erreurs</h2>", f"{strategic_review_html()}\n\n    <h2>Erreurs</h2>")
    write_latest_digest_html(html)
    return html


def commit_strategy_outputs() -> None:
    paths = [path for path in (LATEST_METRICS_PATH, LATEST_DIGEST_HTML_PATH) if path.exists()]
    if not paths:
        return
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    commands = [
        ["git", "config", "user.name", "github-actions[bot]"],
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        ["git", "add", *[str(path.relative_to(ROOT)) for path in paths]],
        ["git", "commit", "-m", "Update latest App Store strategy outputs"],
        ["git", "push"],
    ]
    for command in commands:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            print(f"strategy outputs commit skipped: {' '.join(command)} -> {detail}")
            break


def main() -> None:
    base.render_html = render_html
    parser = argparse.ArgumentParser(description="Generate and email the App Store Connect digest with repo memory")
    parser.add_argument("--recipient", default=base.DEFAULT_RECIPIENT)
    parser.add_argument("--no-send", action="store_true", help="genere le HTML sans envoyer de mail")
    parser.add_argument("--only-paris-hour", type=int, help="ne lance le digest que si l'heure Europe/Paris correspond")
    parser.add_argument("--schedule-cron", help="cron GitHub Actions declencheur; evite les doublons ete/hiver meme si GitHub retarde le run")
    args = parser.parse_args()
    exit_code = base.generate_digest(
        args.recipient,
        should_send=not args.no_send,
        only_paris_hour=args.only_paris_hour,
        schedule_cron=args.schedule_cron,
    )
    commit_strategy_outputs()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
