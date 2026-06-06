#!/usr/bin/env python3
from pathlib import Path

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

path.write_text(html, encoding='utf-8')
