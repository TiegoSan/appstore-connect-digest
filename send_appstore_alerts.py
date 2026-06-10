#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path

import appstore_dashboard
import daily_appstore_digest as digest

ALERT_LEVELS_TO_SEND = {"critical", "warning"}
DASHBOARD_URL = "https://analytics.gogolabs.fr/"


def alert_subject(report_date: str | None, alerts: list[dict]) -> str:
    has_critical = any(alert.get("level") == "critical" for alert in alerts)
    level = "critique" if has_critical else "alerte"
    return f"Gogo Labs App Store - {level} - {report_date or 'latest'}"


def render_alert_email(payload: dict, dashboard_url: str = DASHBOARD_URL) -> str:
    alerts = [alert for alert in payload.get("alerts", []) if alert.get("level") in ALERT_LEVELS_TO_SEND]
    rows = "\n".join(
        f"""
        <tr>
          <td>{html.escape(str(alert.get("level", "")))}</td>
          <td>{html.escape(str(alert.get("title", "")))}</td>
          <td>{html.escape(str(alert.get("detail", "")))}</td>
        </tr>
        """
        for alert in alerts[:8]
    )
    return f"""<!doctype html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #161a20; background: #f2f1ed; padding: 24px;">
  <div style="max-width: 760px; margin: 0 auto; background: #ffffff; border: 1px solid rgba(22,26,32,.14); border-radius: 8px; padding: 24px;">
    <h1 style="font-size: 22px; margin: 0 0 8px;">App Store Connect - alertes</h1>
    <p style="margin: 0 0 18px; color: #5a646b;">Report date: {html.escape(str(payload.get("report_date") or "latest"))}</p>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <thead>
        <tr>
          <th align="left" style="border-bottom: 1px solid rgba(22,26,32,.14); padding: 8px;">Niveau</th>
          <th align="left" style="border-bottom: 1px solid rgba(22,26,32,.14); padding: 8px;">Signal</th>
          <th align="left" style="border-bottom: 1px solid rgba(22,26,32,.14); padding: 8px;">Détail</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="margin: 20px 0 0;"><a href="{html.escape(dashboard_url)}">Ouvrir le dashboard privé</a></p>
  </div>
</body>
</html>
"""


def main() -> None:
    payload_path = appstore_dashboard.DASHBOARD_PAYLOAD_PATH
    if not payload_path.exists():
        payload = appstore_dashboard.write_dashboard()
    else:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))

    alerts = [alert for alert in payload.get("alerts", []) if alert.get("level") in ALERT_LEVELS_TO_SEND]
    if not alerts:
        print("ALERT_MAIL skipped: no warning or critical alert")
        return

    subject = alert_subject(payload.get("report_date"), alerts)
    html_body = render_alert_email(payload)
    html_path = appstore_dashboard.DASHBOARD_DIR / "latest-appstore-alerts.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html_body, encoding="utf-8")
    ok, detail = digest.send_html("gautier@gogolabs.fr", subject, html_body, html_path)
    print(f"ALERT_MAIL {'OK' if ok else 'ERREUR'}: {detail}")
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
