#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import appstore_analytics as asc

ROOT = Path(__file__).resolve().parent
DEFAULT_METADATA_PATH = ROOT / "coupez_v2_compare_metadata.json"


def load_metadata(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for field in ("app_key", "version", "localizations"):
        if field not in payload:
            raise SystemExit(f"Champ manquant dans {path.name}: {field}")
    return payload


def find_version(client: asc.ASCClient, app_id: str, version_string: str) -> dict[str, Any]:
    resp = client.get(
        f"/apps/{app_id}/appStoreVersions"
        "?limit=200"
        "&fields[appStoreVersions]=versionString,appStoreState,appVersionState,platform"
    )
    for item in resp.get("data") or []:
        attrs = item.get("attributes") or {}
        if attrs.get("versionString") == version_string and attrs.get("platform") == "MAC_OS":
            return item
    raise SystemExit(f"Version macOS {version_string} introuvable pour app_id={app_id}.")


def localizations_for_version(client: asc.ASCClient, version_id: str) -> dict[str, dict[str, Any]]:
    resp = client.get(
        f"/appStoreVersions/{version_id}/appStoreVersionLocalizations"
        "?limit=200"
        "&fields[appStoreVersionLocalizations]=locale,promotionalText,description,keywords,whatsNew"
    )
    result: dict[str, dict[str, Any]] = {}
    for item in resp.get("data") or []:
        locale = (item.get("attributes") or {}).get("locale")
        if locale:
            result[locale] = item
    return result


def validate_metadata(payload: dict[str, Any]) -> None:
    for locale, attrs in (payload.get("localizations") or {}).items():
        promo = attrs.get("promotionalText") or ""
        keywords = attrs.get("keywords") or ""
        description = attrs.get("description") or ""
        whats_new = attrs.get("whatsNew") or ""
        if len(promo) > 170:
            raise SystemExit(f"{locale}: promotionalText trop long ({len(promo)} > 170).")
        if len(keywords.encode("utf-8")) > 100:
            raise SystemExit(f"{locale}: keywords trop longs ({len(keywords.encode('utf-8'))} bytes > 100).")
        if len(description) > 4000:
            raise SystemExit(f"{locale}: description trop longue ({len(description)} > 4000).")
        if len(whats_new) > 4000:
            raise SystemExit(f"{locale}: whatsNew trop long ({len(whats_new)} > 4000).")


def patch_localization(client: asc.ASCClient, localization_id: str, attrs: dict[str, Any]) -> dict[str, Any]:
    body = {
        "data": {
            "type": "appStoreVersionLocalizations",
            "id": localization_id,
            "attributes": attrs,
        }
    }
    return client.request("PATCH", f"/appStoreVersionLocalizations/{localization_id}", body=body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Coupez 2.0 compare-focused App Store metadata.")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Print intended updates without writing to App Store Connect.")
    args = parser.parse_args()

    payload = load_metadata(args.metadata)
    validate_metadata(payload)

    config = asc.load_config()
    app = asc.resolve_app(config, payload["app_key"])
    client = asc.ASCClient(config)

    version = find_version(client, app["app_id"], payload["version"])
    version_id = version["id"]
    version_attrs = version.get("attributes") or {}
    print(
        f"Coupez! {payload['version']} macOS: "
        f"{version_attrs.get('appStoreState')} / {version_attrs.get('appVersionState')} ({version_id})"
    )

    existing = localizations_for_version(client, version_id)
    for locale, attrs in payload["localizations"].items():
        loc = existing.get(locale)
        if not loc:
            print(f"{locale}: localization absente, ignorée.")
            continue
        localization_id = loc["id"]
        print(f"{locale}: PATCH appStoreVersionLocalizations/{localization_id}")
        if args.dry_run:
            print(json.dumps(attrs, ensure_ascii=False, indent=2))
            continue
        patch_localization(client, localization_id, attrs)
        print(f"{locale}: ok")


if __name__ == "__main__":
    main()
