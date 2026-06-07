#!/usr/bin/env python3
import json
import re
from datetime import datetime
from pathlib import Path

import daily_appstore_digest as digest


def report_date_for_subject(html: str, metrics_path: Path) -> str:
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding='utf-8'))
        report_date = metrics.get('report_date')
        if report_date:
            return report_date
    title_match = re.search(r'<title>[^<]+ - ([0-9]{4}-[0-9]{2}-[0-9]{2})</title>', html)
    if title_match:
        return title_match.group(1)
    return datetime.now().strftime('%Y-%m-%d')


def main() -> None:
    html_path = Path('strategy/latest-digest.html')
    metrics_path = Path('strategy/latest-metrics.json')
    html = html_path.read_text(encoding='utf-8')
    report_date = report_date_for_subject(html, metrics_path)
    subject = f'{digest.BRAND_NAME} - {report_date}'
    ok, detail = digest.send_html('gautier@gogolabs.fr', subject, html, html_path)
    print(f"MAIL {'OK' if ok else 'ERREUR'}: {detail}")
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
