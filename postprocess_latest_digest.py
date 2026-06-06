#!/usr/bin/env python3
from pathlib import Path
import re

path = Path('strategy/latest-digest.html')
html = path.read_text(encoding='utf-8')

start = html.find('    <h2>Analyse</h2>')
end = html.find('    <h2>Erreurs</h2>')
if start != -1 and end != -1 and start < end:
    html = html[:start] + html[end:]

replacements = {
    'Synthese executive': 'Synthèse exécutive',
    'telechargements': 'téléchargements',
    'Telechargements': 'Téléchargements',
    'Cote engagement': 'Côté engagement',
    'consolidees': 'consolidées',
    'donnees': 'données',
    'Genere depuis': 'Généré depuis',
    'URLs signees': 'URLs signées',
}
for source, target in replacements.items():
    html = html.replace(source, target)

css = '''
    .decision-panel { background:#111827; color:#fff; border-radius:12px; padding:18px 20px; margin:22px 0 26px; }
    .decision-panel h2 { color:#fff; border:0; padding:0; margin:4px 0 16px; font-size:22px; }
    .decision-eyebrow { color:#cbd5e1; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
    .decision-grid { display:grid; grid-template-columns:1fr 2fr 1fr; gap:12px; }
    .decision-grid div { background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.14); border-radius:8px; padding:10px 12px; }
    .decision-grid span { display:block; color:#cbd5e1; font-size:12px; margin-bottom:5px; }
    .decision-grid strong { display:block; font-size:14px; line-height:1.35; }
    .strategy-memory .markdown-table { margin:12px 0 16px; width:100%; border-collapse:collapse; }
    .strategy-memory .markdown-table th { background:#eeeeea; font-weight:700; }
    .strategy-memory .markdown-table th, .strategy-memory .markdown-table td { border:1px solid #e2e2dc; padding:7px 8px; font-size:12px; }
    @media (max-width:720px) { .decision-grid { grid-template-columns:1fr; } }
'''
if '.decision-panel' not in html:
    html = html.replace('  </style>', css + '\n  </style>', 1)

if 'class="decision-panel"' not in html:
    impressions = re.search(r'<div class="label">Impressions</div><div class="value">(\d+)</div>', html)
    page_views = re.search(r'<div class="label">Page views</div><div class="value">(\d+)</div>', html)
    total_impressions = int(impressions.group(1)) if impressions else 0
    total_page_views = int(page_views.group(1)) if page_views else 0
    rate = f'{total_page_views / total_impressions * 100:.2f}%' if total_impressions else 'n/d'
    panel = f'''
    <section class="decision-panel">
      <div class="decision-eyebrow">Décision du jour</div>
      <h2>Repackager les apps visibles avant de produire de nouvelles apps.</h2>
      <div class="decision-grid">
        <div><span>Priorité #1</span><strong>Glass Master</strong></div>
        <div><span>Action avant demain</span><strong>Réécrire le sous-titre et le premier screenshot de l’app prioritaire.</strong></div>
        <div><span>Signal à surveiller</span><strong>Impressions → vues page : {rate}</strong></div>
      </div>
    </section>
'''
    html = html.replace('    <div class="cards">', panel + '\n    <div class="cards">', 1)

def split_cells(line):
    line = re.sub(r'^<p>|</p>$', '', line.strip())
    return [c.strip() for c in line.strip('|').split('|')]

def build_table(block):
    rows = re.findall(r'<p>\|.*?\|</p>', block)
    if len(rows) < 2:
        return block
    headers = split_cells(rows[0])
    body = rows[2:]
    th = ''.join(f'<th>{cell}</th>' for cell in headers)
    trs = []
    for row in body:
        cells = split_cells(row)
        td = ''.join(f'<td>{cell}</td>' for cell in cells)
        trs.append(f'<tr>{td}</tr>')
    return '<table class="markdown-table"><thead><tr>' + th + '</tr></thead><tbody>' + ''.join(trs) + '</tbody></table>'

pattern = r'(<p>\|[^<]+\|</p>\s*){3,}'
html = re.sub(pattern, lambda m: build_table(m.group(0)), html)

path.write_text(html, encoding='utf-8')
