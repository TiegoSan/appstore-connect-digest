#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path

import daily_appstore_digest as digest

html_path = Path('strategy/latest-digest.html')
html = html_path.read_text(encoding='utf-8')
report_date = datetime.now().strftime('%Y-%m-%d')
subject = f'Compte rendu App Store Connect - {report_date}'
ok, detail = digest.send_html('gautier@gogolabs.fr', subject, html, html_path)
print(f"MAIL {'OK' if ok else 'ERREUR'}: {detail}")
raise SystemExit(0 if ok else 2)
