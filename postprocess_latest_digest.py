#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def app_has_store_signal(app: dict[str, Any] | None) -> bool:
    return any(int_value((app or {}).get(field)) for field in ["downloads", "first_time_downloads", "impressions", "product_page_views", "taps"])


def app_map(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not payload:
        return {}
    return {app.get("key") or app.get("name"): app for app in payload.get("apps", [])}


def choose_focus_app(metrics: dict[str, Any] | None) -> dict[str, Any] | None:
    apps = (metrics or {}).get("apps", [])
    candidates = [app for app in apps if int_value(app.get("impressions")) > 0]
    if not candidates:
        return None

    def score(app: dict[str, Any]) -> tuple[float, int, int, str]:
        impressions = int_value(app.get("impressions"))
        views = int_value(app.get("product_page_views"))
        taps = int_value(app.get("taps"))
        view_rate = views / impressions if impressions else 0.0
        opportunity = impressions * (1 - min(view_rate, 1))
        return (opportunity, taps, impressions, app.get("name") or "")

    return max(candidates, key=score)


def decision_panel(metrics: dict[str, Any] | None) -> str:
    totals = (metrics or {}).get("totals", {})
    impressions = int_value(totals.get("impressions"))
    page_views = int_value(totals.get("product_page_views"))
    rate = f"{page_views / impressions * 100:.2f}%" if impressions else "n/d"
    focus = choose_focus_app(metrics)
    focus_name = focus.get("name") if focus else "App prioritaire"
    action = "Réécrire le sous-titre et le premier screenshot de l'app prioritaire."
    if focus:
        action = f"Réécrire le sous-titre et le premier screenshot de {focus_name}."

    return f"""
      <section class="decision-panel">
      <div class="decision-eyebrow">Décision du jour</div>
      <h2>Repackager les apps visibles avant de produire de nouvelles apps.</h2>
      <div class="decision-grid">
        <div><span>Priorité #1</span><strong>{escape(str(focus_name))}</strong></div>
        <div><span>Action avant demain</span><strong>{escape(action)}</strong></div>
        <div><span>Signal à surveiller</span><strong>Impressions -> vues page : {escape(rate)}</strong></div>
      </div>
    </section>
"""


def delta_line(label: str, current: int, previous: int) -> str:
    diff = current - previous
    sign = "+" if diff > 0 else ""
    return f"<li><strong>{escape(label)}</strong> : {current} ({sign}{diff} vs hier)</li>"


def yesterday_section(metrics: dict[str, Any] | None, previous_metrics: dict[str, Any] | None) -> str:
    if not metrics or not previous_metrics:
        return (
            '<section class="yesterday"><h2>Que s\'est-il passé depuis hier</h2>'
            "<p>Pas encore de point de comparaison fiable. Cette section sera exploitable après deux runs consécutifs avec métriques persistées.</p></section>"
        )

    current_totals = metrics.get("totals", {})
    previous_totals = previous_metrics.get("totals", {})
    current_apps = app_map(metrics)
    previous_apps = app_map(previous_metrics)
    rows: list[tuple[int, str, int, int, int]] = []
    for key, app in current_apps.items():
        previous = previous_apps.get(key, {})
        if not (app_has_store_signal(app) or app_has_store_signal(previous)):
            continue
        downloads_delta = int_value(app.get("downloads")) - int_value(previous.get("downloads"))
        impressions_delta = int_value(app.get("impressions")) - int_value(previous.get("impressions"))
        views_delta = int_value(app.get("product_page_views")) - int_value(previous.get("product_page_views"))
        if downloads_delta or impressions_delta or views_delta:
            movement = abs(downloads_delta) + abs(impressions_delta) + abs(views_delta)
            rows.append((movement, app.get("name") or key, downloads_delta, impressions_delta, views_delta))
    rows.sort(reverse=True)
    app_lines = "".join(
        f"<li><strong>{escape(name)}</strong> : downloads {downloads:+d}, impressions {impressions:+d}, vues page {views:+d}</li>"
        for _, name, downloads, impressions, views in rows[:6]
    )
    if not app_lines:
        app_lines = "<li>Aucun mouvement significatif sur les apps présentes dans l'App Store.</li>"

    return f"""<section class="yesterday">
<h2>Que s'est-il passé depuis hier</h2>
<ul>
{delta_line("Downloads", int_value(current_totals.get("downloads")), int_value(previous_totals.get("downloads")))}
{delta_line("First-time downloads", int_value(current_totals.get("first_time_downloads")), int_value(previous_totals.get("first_time_downloads")))}
{delta_line("Impressions", int_value(current_totals.get("impressions")), int_value(previous_totals.get("impressions")))}
{delta_line("Page views", int_value(current_totals.get("product_page_views")), int_value(previous_totals.get("product_page_views")))}
{delta_line("Taps", int_value(current_totals.get("taps")), int_value(previous_totals.get("taps")))}
</ul>
<h3>Apps qui ont bougé</h3>
<ul>{app_lines}</ul>
<p class="muted">Apps exclues : apps sans signal App Store dans les métriques actuelles et précédentes.</p>
</section>"""


def markdown_inline(text: str) -> str:
    rendered = escape(text.strip())
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"_(.+?)_", r"<em>\1</em>", rendered)
    return rendered


def clean_heading_number(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.\s*", "", title.strip())


def split_table_cells(line: str) -> list[str]:
    line = re.sub(r"^<p>|</p>$", "", line.strip())
    return [cell.strip() for cell in line.strip("|").split("|")]


def build_table(block: str) -> str:
    rows = re.findall(r"<p>\|.*?\|</p>", block)
    if len(rows) < 2:
        return block
    headers = split_table_cells(rows[0])
    body = rows[2:]
    th = "".join(f"<th>{cell}</th>" for cell in headers)
    trs = []
    for row in body:
        cells = split_table_cells(row)
        td = "".join(f"<td>{cell}</td>" for cell in cells)
        trs.append(f"<tr>{td}</tr>")
    return '<table class="markdown-table"><thead><tr>' + th + "</tr></thead><tbody>" + "".join(trs) + "</tbody></table>"


def markdown_to_html(markdown: str) -> str:
    out: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            close_lists()
            continue
        if line.startswith("### "):
            close_lists()
            out.append(f"<h3>{markdown_inline(clean_heading_number(line[4:]))}</h3>")
        elif line.startswith("## "):
            close_lists()
            out.append(f"<h2>{markdown_inline(clean_heading_number(line[3:]))}</h2>")
        elif line.startswith("# "):
            close_lists()
            out.append(f"<h2>{markdown_inline(clean_heading_number(line[2:]))}</h2>")
        elif line.startswith("- "):
            if not in_ul:
                close_lists()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{markdown_inline(line[2:])}</li>")
        elif re.match(r"^\d+\.\s+", line):
            if not in_ol:
                close_lists()
                out.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s+", "", line)
            out.append(f"<li>{markdown_inline(item)}</li>")
        else:
            close_lists()
            out.append(f"<p>{markdown_inline(line)}</p>")
    close_lists()
    rendered = "\n".join(out)
    return re.sub(r"(<p>\|[^<]+\|</p>\s*){3,}", lambda match: build_table(match.group(0)), rendered)


def strategic_review_blocks(markdown: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []
    in_section = False

    for raw in markdown.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            if in_section and current_lines:
                blocks.append((current_title, current_lines))
            current_title = clean_heading_number(line[3:])
            current_lines = [raw]
            in_section = True
            continue
        if not in_section:
            continue
        current_lines.append(raw)

    if in_section and current_lines:
        blocks.append((current_title, current_lines))

    return [(title, "\n".join(lines).strip()) for title, lines in blocks if "\n".join(lines).strip()]


def strategic_review_section(review_path: Path, decision_html: str = "") -> str:
    if not review_path.exists():
        return ""
    markdown = review_path.read_text(encoding="utf-8").strip()
    if not markdown:
        return ""

    title = "Revue stratégique"
    body_lines = []
    for raw in markdown.splitlines():
        if raw.strip().startswith("# "):
            title = raw.strip()[2:].strip() or title
            continue
        body_lines.append(raw)

    blocks = strategic_review_blocks("\n".join(body_lines).strip())
    rendered_blocks = "\n".join(
        f'      <section class="strategy-block" aria-label="{escape(block_title)}">{markdown_to_html(block_markdown)}</section>'
        for block_title, block_markdown in blocks
    )
    return f"""
    <div class="strategy-review" aria-label="{escape(title)}">
{decision_html.rstrip()}
{rendered_blocks}
    </div>
"""


def inject_css(html: str) -> str:
    html = re.sub(r"\n\s*\.strategy-memory[^{]*\{[^}]*\}", "", html)
    css_chunks: list[str] = []
    if ".brand-head {" not in html:
        css_chunks.append("""
    .brand-head { display:flex; align-items:center; gap:12px; margin:0 0 8px; }
    .brand-logo { width:42px; height:42px; border-radius:10px; object-fit:cover; }
""")
    if ".decision-panel {" not in html:
        css_chunks.append("""
    .decision-panel { background:#111827; color:#ffffff; border:0; border-radius:14px; padding:18px 20px; margin:0 0 18px; }
    .decision-panel h2 { color:#ffffff; border:0; padding:0; margin:4px 0 16px; font-size:22px; }
    .decision-eyebrow { color:#cbd5e1; font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }
    .decision-grid { display:grid; grid-template-columns:1fr 2fr 1fr; gap:12px; }
    .decision-grid div { background:#242a36; border:1px solid rgba(255,255,255,.16); border-radius:8px; padding:10px 12px; }
    .decision-grid span { display:block; color:#cbd5e1; font-size:12px; margin-bottom:5px; }
    .decision-grid strong { color:#ffffff; }
    .decision-grid strong { display:block; font-size:14px; line-height:1.35; }
    @media (max-width:720px) { .decision-grid { grid-template-columns:1fr; } }
""")
    if ".yesterday {" not in html:
        css_chunks.append("""
    .yesterday { background:#faf9f4; border:1px solid rgba(22,26,32,.12); border-radius:10px; padding:14px 16px; margin:18px 0 24px; }
    .yesterday ul { margin:8px 0 0; }
    .yesterday p, .yesterday li { font-size:15px; line-height:1.55; }
""")
    if ".strategy-block {" not in html:
        css_chunks.append("""
    .strategy-review { margin:24px 0; }
    .strategy-block { background:#faf9f4; border:1px solid rgba(22,26,32,.12); border-radius:10px; padding:14px 16px; margin:0 0 18px; overflow-x:auto; }
    .strategy-block h3 { margin:16px 0 8px; font-size:15px; }
    .strategy-block p { margin:8px 0; font-size:15px; line-height:1.55; }
    .strategy-block ul, .strategy-block ol { margin:8px 0 14px; }
    .strategy-block li { font-size:15px; line-height:1.55; }
    .strategy-block code { background:#ece8e0; border-radius:4px; padding:1px 4px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }
    .strategy-block .markdown-table { margin:12px 0 16px; width:100%; border-collapse:collapse; }
    .strategy-block .markdown-table th { background:#ece8e0; font-weight:700; }
    .strategy-block .markdown-table th, .strategy-block .markdown-table td { border:1px solid rgba(22,26,32,.12); padding:7px 8px; font-size:12px; }
""")
    if not css_chunks:
        return html
    if "  </style>" not in html:
        raise RuntimeError("Balise </style> introuvable dans le digest HTML.")
    return html.replace("  </style>", "".join(css_chunks) + "\n  </style>", 1)


def apply_branding(html: str) -> str:
    html = html.replace("<title>Compte rendu App Store Connect -", "<title>Gogo Labs Daily Business Digest -")
    html = html.replace(
        "    <h1>Compte rendu App Store Connect</h1>",
        '    <div class="brand-head"><img class="brand-logo" src="cid:gogolabs-logo" alt="Gogo Labs"><h1>Gogo Labs Daily Business Digest</h1></div>',
        1,
    )
    return html


def apply_text_replacements(html: str) -> str:
    replacements = {
        "Synthese executive": "Synthèse exécutive",
        "telechargements": "téléchargements",
        "Telechargements": "Téléchargements",
        "Cote engagement": "Côté engagement",
        "consolidees": "consolidées",
        "donnees": "données",
        "Genere depuis": "Généré depuis",
        "Genere par": "Généré par",
        "URLs signees": "URLs signées",
        "reseau observee pendant la generation": "réseau observée pendant la génération",
    }
    for source, target in replacements.items():
        html = html.replace(source, target)
    return html


def remove_base_analysis(html: str) -> str:
    start = html.find("    <h2>Analyse</h2>")
    end = html.find("    <h2>Erreurs</h2>")
    if start != -1 and end != -1 and start < end:
        return html[:start] + html[end:]
    return html


def remove_named_section(html: str, title: str) -> str:
    pattern = rf"\s*<h2>{re.escape(title)}</h2>.*?(?=\s*<h2>|\s*<div class=\"strategy-review\"|\s*<p class=\"footer\">)"
    return re.sub(pattern, "\n", html, count=1, flags=re.DOTALL)


def replace_strategy_section(html: str, section: str) -> str:
    html = re.sub(r"\s*<div class=\"strategy-review\".*?</div>\s*", "\n", html, flags=re.DOTALL)
    html = re.sub(r"\s*<h2>Reflexion strategique</h2>\s*<div class=\"strategy-memory\">.*?</div>\s*", "\n", html, flags=re.DOTALL)
    html = re.sub(r"\s*<h2>Réflexion stratégique</h2>\s*<div class=\"strategy-memory\">.*?</div>\s*", "\n", html, flags=re.DOTALL)
    html = re.sub(r"\s*<div class=\"strategy-memory\">.*?</div>\s*", "\n", html, flags=re.DOTALL)
    errors_start = html.find("    <h2>Erreurs</h2>")
    footer_match = re.search(r"\s*<p class=\"footer\">", html)
    footer_start = footer_match.start() if footer_match else -1
    footer_tail = "    " + html[footer_start:].lstrip() if footer_match else ""
    if errors_start != -1 and footer_start != -1 and errors_start < footer_start:
        return html[:errors_start] + section + "\n" + footer_tail
    if footer_start != -1:
        return html[:footer_start] + section + "\n" + footer_tail
    raise RuntimeError("Emplacement d'insertion de la réflexion stratégique introuvable.")


def postprocess(root: Path = ROOT) -> Path:
    html_path = root / "strategy" / "latest-digest.html"
    metrics_path = root / "strategy" / "latest-metrics.json"
    previous_metrics_path = Path("/tmp/previous-metrics.json")
    review_path = root / "strategy" / "strategic-review.md"
    if not html_path.exists():
        raise FileNotFoundError(html_path)

    html = html_path.read_text(encoding="utf-8")
    metrics = load_json(metrics_path)
    previous_metrics = load_json(previous_metrics_path)
    html = remove_base_analysis(html)
    html = apply_branding(html)
    html = apply_text_replacements(html)
    html = remove_named_section(html, "Synthèse exécutive")
    html = remove_named_section(html, "Signaux par app")
    html = inject_css(html)
    if "Que s'est-il passé depuis hier" not in html and "Que s’est-il passé depuis hier" not in html:
        html = html.replace("    <h2>Tableau principal</h2>", yesterday_section(metrics, previous_metrics) + "\n\n    <h2>Tableau principal</h2>", 1)
    html = replace_strategy_section(html, strategic_review_section(review_path, decision_panel(metrics)))
    html = re.sub(r"(<p>\|[^<]+\|</p>\s*){3,}", lambda match: build_table(match.group(0)), html)
    html_path.write_text(html, encoding="utf-8")
    return html_path


def main() -> None:
    path = postprocess()
    print(f"POSTPROCESS {path}")


if __name__ == "__main__":
    main()
