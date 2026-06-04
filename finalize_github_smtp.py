#!/usr/bin/env python3
"""Prompt for an iCloud app-specific password, set GitHub secrets, and test the workflow."""

from __future__ import annotations

import smtplib
import subprocess
import sys

REPO = "TiegoSan/appstore-connect-digest"
SMTP_HOST = "smtp.mail.me.com"
SMTP_PORT = 587
SMTP_USER_CANDIDATES = [
    "gautier@me.com",
    "monkeystudio@me.com",
    "ag.defaultrier@icloud.com",
    "goachats@me.com",
    "gautier",
    "monkeystudio",
    "ag.defaultrier",
    "goachats",
    "gautier@gogolabs.fr",
]


def prompt_password() -> str:
    script = '''
display dialog "Colle le mot de passe spécifique à l’app iCloud. Le script testera le login SMTP et l’enverra directement dans GitHub Secrets, sans l’afficher." default answer "" with hidden answer buttons {"Annuler", "Tester"} default button "Tester" with title "Secret SMTP iCloud"
text returned of result
'''
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("Annule.")
    password = proc.stdout.rstrip("\n")
    if not password:
        raise SystemExit("Mot de passe vide.")
    return password


def test_smtp(password: str) -> str:
    errors: list[str] = []
    for username in SMTP_USER_CANDIDATES:
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(username, password)
            return username
        except Exception as exc:
            errors.append(f"{username}: {exc}")
    print("Aucun username teste ne fonctionne avec ce mot de passe.", file=sys.stderr)
    for line in errors:
        print(f"- {line}", file=sys.stderr)
    raise SystemExit(2)


def set_secret(name: str, value: str) -> None:
    proc = subprocess.run(
        ["gh", "secret", "set", name, "--repo", REPO],
        input=value.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"Erreur gh secret set {name}: {stderr}")


def main() -> None:
    password = prompt_password()
    username = test_smtp(password)
    set_secret("APPSTORE_DIGEST_SMTP_USER", username)
    set_secret("APPSTORE_DIGEST_SMTP_PASSWORD", password)
    print(f"SMTP OK avec {username}. Secrets GitHub mis a jour.")

    proc = subprocess.run(
        ["gh", "workflow", "run", "appstore-digest.yml", "--repo", REPO],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise SystemExit(f"Workflow non lance: {proc.stderr.strip()}")
    print("Workflow GitHub lance.")


if __name__ == "__main__":
    main()
