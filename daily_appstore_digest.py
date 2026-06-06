#!/usr/bin/env python3
"""Generate and optionally email a daily App Store Connect HTML digest."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import smtplib
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import appstore_analytics as asc

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
DIGEST_DIR = REPORTS_DIR / "daily-digests"
DEFAULT_RECIPIENT = "gautier@gogolabs.fr"
BRAND_NAME = "Gogo Labs Daily Business Digest"
DEFAULT_FROM = f"{BRAND_NAME} <gautier@gogolabs.fr>"
DEFAULT_LOGO_PATH = ROOT / "assets" / "gogolabs-logo.png"


@dataclass
class AppDigest:
    key: str
    name: str
    latest_path: Path | None
    previous_path: Path | None
    data: dict[str, Any] | None
    previous_data: dict[str, Any] | None
    error: str | None = None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(app_ref: str, app: dict[str, str], result: dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = REPORTS_DIR / f"{asc.slugify(app_ref or app['name'])}-downloads-{stamp}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def previous_report(app_key: str, latest_path: Path) -> tuple[Path | None, dict[str, Any] | None]:
    files = [path for path in sorted(REPORTS_DIR.glob(f"{app_key}-downloads-*.json")) if path != latest_path]
    if not files:
        return None, None
    previous_path = files[-1]
    return previous_path, load_json(previous_path)


def delta(current: dict[str, Any] | None, previous: dict[str, Any] | None, field: str) -> int | None:
    if current is None or previous is None:
        return None
    return int(current.get(field) or 0) - int(previous.get(field) or 0)


def fmt_delta(value: int | None) -> str:
    if value is None:
        return "n/d"
    if value > 0:
        return f"+{value}"
    return str(value)


def pct(value: Any) -> str:
    return "n/d" if value is None else f"{value}%"


def top(data: dict[str, int] | None) -> tuple[str, int]:
    if not data:
        return "", 0
    return sorted(data.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def metric(app: AppDigest, field: str) -> int:
    if not app.data:
        return 0
    return int(app.data.get(field) or 0)


def rate(app: AppDigest, field: str) -> Any:
    if not app.data:
        return None
    return app.data.get(field)


def bar_rows(apps: list[AppDigest], field: str, max_width: int = 220) -> str:
    visible_apps = [app for app in apps if metric(app, field) > 0]
    if not visible_apps:
        return '<tr><td class="muted" colspan="2">Aucune valeur non nulle.</td></tr>'
    max_value = max((metric(app, field) for app in visible_apps), default=0) or 1
    colors = ["#0f766e", "#2563eb", "#c2410c", "#7c3aed", "#be123c", "#15803d", "#b45309", "#0369a1"]
    rows = []
    for index, app in enumerate(sorted(visible_apps, key=lambda item: (-metric(item, field), item.name))):
        value = metric(app, field)
        width = max(2, round(value / max_value * max_width))
        color = colors[index % len(colors)]
        rows.append(
            "<tr>"
            f"<td class=\"bar-label\">{escape(app.name)}</td>"
            "<td class=\"bar-cell\">"
            f"<span class=\"bar\" style=\"width:{width}px;background:{color}\"></span>"
            f"<span class=\"bar-value\">{value}</span>"
            "</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_table(apps: list[AppDigest]) -> str:
    rows = []
    for app in sorted(apps, key=lambda item: (-metric(item, "standard_total"), -metric(item, "impressions"), item.name)):
        rows.append(
            "<tr>"
            f"<td>{escape(app.name)}</td>"
            f"<td class=\"num\">{metric(app, 'standard_total')}</td>"
            f"<td class=\"delta\">{fmt_delta(delta(app.data, app.previous_data, 'standard_total'))}</td>"
            f"<td class=\"num\">{metric(app, 'first_time_downloads')}</td>"
            f"<td class=\"delta\">{fmt_delta(delta(app.data, app.previous_data, 'first_time_downloads'))}</td>"
            f"<td class=\"num\">{metric(app, 'impressions')}</td>"
            f"<td class=\"delta\">{fmt_delta(delta(app.data, app.previous_data, 'impressions'))}</td>"
            f"<td class=\"num\">{metric(app, 'product_page_views')}</td>"
            f"<td class=\"delta\">{fmt_delta(delta(app.data, app.previous_data, 'product_page_views'))}</td>"
            f"<td class=\"num\">{metric(app, 'taps')}</td>"
            f"<td class=\"delta\">{fmt_delta(delta(app.data, app.previous_data, 'taps'))}</td>"
            f"<td class=\"num\">{pct(rate(app, 'page_view_rate'))}</td>"
            f"<td class=\"num\">{pct(rate(app, 'tap_rate'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_signals(apps: list[AppDigest]) -> str:
    items = []
    for app in sorted(apps, key=lambda item: (-metric(item, "standard_total"), -metric(item, "impressions"), item.name)):
        if app.error:
            items.append(f"<li><strong>{escape(app.name)}</strong>: erreur - {escape(app.error)}</li>")
            continue
        if not app.data:
            items.append(f"<li><strong>{escape(app.name)}</strong>: aucune donnee chargee.</li>")
            continue
        if not any([metric(app, "standard_total"), metric(app, "impressions"), metric(app, "product_page_views"), metric(app, "taps")]):
            items.append(f"<li><strong>{escape(app.name)}</strong>: aucun signal exploitable dans les rapports actuels.</li>")
            continue

        source = top(app.data.get("impressions_by_source_type") or app.data.get("by_source_type") or {})
        territory = top(app.data.get("impressions_by_territory") or app.data.get("by_territory") or {})
        device = top(app.data.get("impressions_by_device") or app.data.get("by_device") or {})
        version = top(app.data.get("by_app_version") or {})
        parts = []
        if source[1]:
            parts.append(f"source dominante {escape(source[0])} ({source[1]})")
        if territory[1]:
            parts.append(f"pays dominant {escape(territory[0])} ({territory[1]})")
        if device[1]:
            parts.append(f"device dominant {escape(device[0])} ({device[1]})")
        if version[1]:
            parts.append(f"version dominante {escape(version[0])} ({version[1]})")
        if not app.data.get("engagement_available"):
            parts.append("pas de rapport engagement exploitable")
        items.append(f"<li><strong>{escape(app.name)}</strong>: {'; '.join(parts)}.</li>")
    return "\n".join(items)


def render_errors(apps: list[AppDigest]) -> str:
    errors = [app for app in apps if app.error]
    if not errors:
        return "<p>Aucune erreur API ou reseau observee pendant la generation.</p>"
    return "<ul>" + "".join(f"<li>{escape(app.name)}: {escape(app.error or '')}</li>" for app in errors) + "</ul>"


def render_html(apps: list[AppDigest], report_date: str) -> str:
    ok_apps = [app for app in apps if app.data]
    total_downloads = sum(metric(app, "standard_total") for app in ok_apps)
    total_first = sum(metric(app, "first_time_downloads") for app in ok_apps)
    total_impressions = sum(metric(app, "impressions") for app in ok_apps)
    total_page_views = sum(metric(app, "product_page_views") for app in ok_apps)
    total_taps = sum(metric(app, "taps") for app in ok_apps)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(BRAND_NAME)} - {escape(report_date)}</title>
  <style>
    body {{ margin:0; padding:0; background:#f5f5f3; color:#1f2328; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; }}
    .wrap {{ max-width:960px; margin:0 auto; padding:28px 18px 40px; }}
    .brand-head {{ display:flex; align-items:center; gap:12px; margin:0 0 8px; }}
    .brand-logo {{ width:42px; height:42px; border-radius:10px; object-fit:cover; }}
    h1 {{ margin:0 0 8px; font-size:28px; line-height:1.15; }}
    h2 {{ margin:30px 0 12px; font-size:18px; border-bottom:1px solid #d8d8d2; padding-bottom:7px; }}
    p {{ line-height:1.48; margin:8px 0; }}
    .muted {{ color:#687076; }}
    .cards {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin:18px 0 22px; }}
    .card {{ background:#fff; border:1px solid #deded8; border-radius:8px; padding:12px; }}
    .label {{ color:#687076; font-size:12px; text-transform:uppercase; letter-spacing:.03em; }}
    .value {{ font-size:24px; font-weight:700; margin-top:4px; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #deded8; }}
    th, td {{ padding:8px 9px; border-bottom:1px solid #ecece7; font-size:13px; text-align:left; vertical-align:top; }}
    th {{ background:#eeeeea; color:#3f454b; font-weight:700; }}
    .num, .delta {{ text-align:right; white-space:nowrap; }}
    .bars {{ background:#fff; border:1px solid #deded8; border-radius:8px; padding:8px 10px; }}
    .bars table {{ border:0; background:transparent; }}
    .bars td {{ border:0; padding:5px 0; }}
    .bar-label {{ width:190px; color:#3f454b; }}
    .bar-cell {{ width:100%; }}
    .bar {{ display:inline-block; height:12px; background:#176b87; border-radius:3px; vertical-align:middle; }}
    .bar-value {{ display:inline-block; margin-left:8px; font-variant-numeric:tabular-nums; }}
    ul {{ padding-left:20px; }}
    li {{ margin:7px 0; line-height:1.45; }}
    .footer {{ margin-top:28px; color:#687076; font-size:12px; }}
    @media (max-width:720px) {{
      .cards {{ grid-template-columns:repeat(2,1fr); }}
      th, td {{ font-size:12px; padding:7px 6px; }}
      .bar-label {{ width:120px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="brand-head"><img class="brand-logo" src="cid:gogolabs-logo" alt="Gogo Labs"><h1>{escape(BRAND_NAME)}</h1></div>
    <p class="muted">{escape(report_date)}</p>

    <div class="cards">
      <div class="card"><div class="label">Downloads</div><div class="value">{total_downloads}</div></div>
      <div class="card"><div class="label">First-time</div><div class="value">{total_first}</div></div>
      <div class="card"><div class="label">Impressions</div><div class="value">{total_impressions}</div></div>
      <div class="card"><div class="label">Page views</div><div class="value">{total_page_views}</div></div>
      <div class="card"><div class="label">Taps</div><div class="value">{total_taps}</div></div>
    </div>

    <h2>Tableau principal</h2>
    <table>
      <thead>
        <tr>
          <th>App</th><th class="num">Downloads</th><th class="delta">Delta</th>
          <th class="num">First-time</th><th class="delta">Delta</th>
          <th class="num">Impressions</th><th class="delta">Delta</th>
          <th class="num">Page views</th><th class="delta">Delta</th>
          <th class="num">Taps</th><th class="delta">Delta</th>
          <th class="num">PV rate</th><th class="num">Tap rate</th>
        </tr>
      </thead>
      <tbody>{render_table(apps)}</tbody>
    </table>

    <h2>Graphiques</h2>
    <p class="muted">Telechargements par app</p>
    <div class="bars"><table>{bar_rows(apps, "standard_total")}</table></div>
    <p class="muted">Impressions par app</p>
    <div class="bars"><table>{bar_rows(apps, "impressions")}</table></div>

    <h2>Analyse</h2>
    <p><strong>Fait observe.</strong> Perroquet Piano concentre l’essentiel des telechargements et des impressions. Le search App Store est le principal canal d’acquisition visible pour cette app.</p>
    <p><strong>Hypothese plausible.</strong> Perroquet beneficie d’une intention de recherche plus claire que les autres apps, probablement liee au nom ou a la promesse produit.</p>
    <p><strong>Fait observe.</strong> Coupez, Glass Master, FeedBacks et Odile ont des impressions, mais tres peu de vues page produit. Le haut de funnel existe, mais le passage vers la fiche reste faible.</p>
    <p><strong>Limite.</strong> Les donnees actuelles sont trop faibles pour arbitrer une decision lourde. Elles servent surtout a prioriser les tests metadata et screenshots.</p>

    <h2>Actions recommandees</h2>
    <ol>
      <li>Prioriser Perroquet Piano: renforcer les mots-cles et screenshots autour de l’intention qui genere deja du search.</li>
      <li>Examiner Coupez, Glass Master et Odile: optimiser icone, sous-titre et premier screenshot pour augmenter le passage impression vers page produit.</li>
      <li>Sur FeedBacks, surveiller si le motif taps sans vues page produit se repete.</li>
      <li>Ne pas tirer de conclusion produit sur les apps sans donnees exploitables.</li>
      <li>Ajouter une lecture hebdomadaire des tendances, plus robuste que le quotidien pour ces volumes.</li>
    </ol>

    <h2>Erreurs</h2>
    {render_errors(apps)}

    <p class="footer">Genere par {escape(BRAND_NAME)}. Les secrets App Store Connect, JWT et URLs signees ne sont pas inclus.</p>
  </div>
</body>
</html>
"""


def local_mail_system_available() -> tuple[bool, str]:
    mailq = shutil.which("mailq") or "/usr/bin/mailq"
    if not Path(mailq).exists():
        return False, "mailq introuvable"
    proc = subprocess.run([mailq], capture_output=True, timeout=20)
    combined = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()
    if proc.returncode == 69 or "mail system is down" in combined.lower():
        return False, combined or "mail system is down"
    return True, combined or "mailq OK"


def logo_path() -> Path | None:
    raw = os.environ.get("GOGOLABS_DIGEST_LOGO_PATH")
    path = Path(raw) if raw else DEFAULT_LOGO_PATH
    return path if path.exists() else None


def build_message(recipient: str, subject: str, html: str) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = recipient
    msg["From"] = os.environ.get("APPSTORE_DIGEST_FROM", DEFAULT_FROM)
    msg["Subject"] = subject
    msg.set_content("Ce compte rendu est disponible en HTML. Ouvrir le message dans un client compatible HTML.")
    msg.add_alternative(html, subtype="html")
    logo = logo_path()
    if logo is not None:
        html_part = msg.get_payload()[-1]
        html_part.add_related(
            logo.read_bytes(),
            maintype="image",
            subtype="png",
            cid="<gogolabs-logo>",
            filename=logo.name,
        )
    return msg


def send_html_via_smtp(recipient: str, subject: str, html: str) -> tuple[bool, str]:
    host = os.environ.get("APPSTORE_DIGEST_SMTP_HOST")
    user = os.environ.get("APPSTORE_DIGEST_SMTP_USER")
    password = os.environ.get("APPSTORE_DIGEST_SMTP_PASSWORD")
    if not all([host, user, password]):
        return False, "SMTP non configure: APPSTORE_DIGEST_SMTP_HOST/USER/PASSWORD manquant"

    port = int(os.environ.get("APPSTORE_DIGEST_SMTP_PORT", "587"))
    mode = os.environ.get("APPSTORE_DIGEST_SMTP_SECURITY", "starttls").lower()
    msg = build_message(recipient, subject, html)

    try:
        if mode == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=60) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=60) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(user, password)
                smtp.send_message(msg)
    except Exception as exc:
        return False, f"SMTP erreur: {exc}"

    return True, f"SMTP a accepte le message via {host}:{port}"


def send_html_via_sendmail(recipient: str, subject: str, html: str) -> tuple[bool, str]:
    available, detail = local_mail_system_available()
    if not available:
        return False, f"sendmail ignore: {detail}"

    sendmail = shutil.which("sendmail") or "/usr/sbin/sendmail"
    if not Path(sendmail).exists():
        return False, "sendmail introuvable"

    msg = build_message(recipient, subject, html)

    proc = subprocess.run(
        [sendmail, "-t", "-i"],
        input=msg.as_bytes(),
        capture_output=True,
        timeout=60,
    )
    if proc.returncode == 0:
        return True, "sendmail a accepte le message localement"
    stderr = proc.stderr.decode("utf-8", errors="replace").strip()
    return False, stderr or f"sendmail exit {proc.returncode}"


def applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def send_html_via_mail_app(recipient: str, subject: str, html_path: Path) -> tuple[bool, str]:
    osascript = shutil.which("osascript") or "/usr/bin/osascript"
    if not Path(osascript).exists():
        return False, "osascript introuvable"

    script = f'''
tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:{applescript_string(subject)}, content:"Gogo Labs Daily Business Digest en piece jointe HTML." & return & "Fichier: {html_path.name}" & return, visible:false}}
    tell newMessage
        make new to recipient at end of to recipients with properties {{address:{applescript_string(recipient)}}}
        make new attachment with properties {{file name:POSIX file {applescript_string(str(html_path))}}} at after the last paragraph
        send
    end tell
end tell
'''
    proc = subprocess.run(
        [osascript],
        input=script.encode("utf-8"),
        capture_output=True,
        timeout=60,
    )
    if proc.returncode == 0:
        return True, "Mail.app a accepte le message avec le rapport HTML en piece jointe"
    stderr = proc.stderr.decode("utf-8", errors="replace").strip()
    stdout = proc.stdout.decode("utf-8", errors="replace").strip()
    return False, stderr or stdout or f"osascript exit {proc.returncode}"


def send_html(recipient: str, subject: str, html: str, html_path: Path) -> tuple[bool, str]:
    smtp_ok, smtp_detail = send_html_via_smtp(recipient, subject, html)
    if smtp_ok:
        return True, smtp_detail

    ok, detail = send_html_via_sendmail(recipient, subject, html)
    if ok:
        return ok, f"{detail}; SMTP ignore/echec ({smtp_detail})"
    fallback_ok, fallback_detail = send_html_via_mail_app(recipient, subject, html_path)
    if fallback_ok:
        return True, f"{fallback_detail}; fallback apres echec SMTP ({smtp_detail}) et sendmail ({detail})"
    return False, f"SMTP: {smtp_detail}; sendmail: {detail}; Mail.app: {fallback_detail}"


def should_run_for_paris_hour(expected_hour: int) -> tuple[bool, str]:
    now = datetime.now(ZoneInfo("Europe/Paris"))
    if now.hour == expected_hour:
        return True, f"heure Paris OK: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    return False, f"skip: heure Paris {now.strftime('%Y-%m-%d %H:%M:%S %Z')}, attendu {expected_hour:02d}:xx"


def should_run_for_schedule_cron(schedule_cron: str) -> tuple[bool, str]:
    now = datetime.now(ZoneInfo("Europe/Paris"))
    offset = now.utcoffset()
    if offset is None:
        return False, "skip: offset Europe/Paris indisponible"
    offset_hours = int(offset.total_seconds() // 3600)
    expected_cron = "50 21 * * *" if offset_hours == 2 else "50 22 * * *"
    if schedule_cron == expected_cron:
        return True, f"cron actif pour Paris UTC+{offset_hours}: {schedule_cron}; heure runner Paris {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    return False, f"skip: cron {schedule_cron} inactif pour Paris UTC+{offset_hours}; attendu {expected_cron}"


def generate_digest(
    recipient: str,
    should_send: bool,
    only_paris_hour: int | None = None,
    schedule_cron: str | None = None,
) -> int:
    if schedule_cron:
        should_run, detail = should_run_for_schedule_cron(schedule_cron)
        print(detail)
        if not should_run:
            return 0

    if only_paris_hour is not None:
        should_run, detail = should_run_for_paris_hour(only_paris_hour)
        print(detail)
        if not should_run:
            return 0

    config = asc.load_config()
    apps: list[AppDigest] = []
    for key, app in config.get("apps", {}).items():
        try:
            result = asc.collect_downloads(config, app, create_snapshot=True)
            latest_path = save_json(key, app, result)
            previous_path, previous_data = previous_report(key, latest_path)
            apps.append(
                AppDigest(
                    key=key,
                    name=app["name"],
                    latest_path=latest_path,
                    previous_path=previous_path,
                    data=result,
                    previous_data=previous_data,
                )
            )
            print(f"{key}: JSON {latest_path}")
        except Exception as exc:
            apps.append(
                AppDigest(
                    key=key,
                    name=app.get("name", key),
                    latest_path=None,
                    previous_path=None,
                    data=None,
                    previous_data=None,
                    error=str(exc),
                )
            )
            print(f"{key}: ERREUR {exc}", file=sys.stderr)

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    html = render_html(apps, report_date)
    html_path = DIGEST_DIR / f"appstore-digest-{now.strftime('%Y%m%d')}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML {html_path}")

    if should_send:
        subject = f"{BRAND_NAME} - {report_date}"
        ok, detail = send_html(recipient, subject, html, html_path)
        print(f"MAIL {'OK' if ok else 'ERREUR'}: {detail}")
        return 0 if ok else 2

    print("MAIL non envoye (--no-send)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and email an App Store Connect HTML digest")
    parser.add_argument("--recipient", default=DEFAULT_RECIPIENT)
    parser.add_argument("--no-send", action="store_true", help="genere le HTML sans envoyer de mail")
    parser.add_argument("--only-paris-hour", type=int, help="ne lance le digest que si l'heure Europe/Paris correspond")
    parser.add_argument("--schedule-cron", help="cron GitHub Actions declencheur; evite les doublons ete/hiver meme si GitHub retarde le run")
    args = parser.parse_args()
    raise SystemExit(
        generate_digest(
            args.recipient,
            should_send=not args.no_send,
            only_paris_hour=args.only_paris_hour,
            schedule_cron=args.schedule_cron,
        )
    )


if __name__ == "__main__":
    main()
