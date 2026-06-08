#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import appstore_analytics as asc

ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "strategy" / "latest-metrics.json"

PIPELINE_STATES = {
    "PREPARE_FOR_SUBMISSION",
    "READY_FOR_REVIEW",
    "WAITING_FOR_REVIEW",
    "IN_REVIEW",
    "PENDING_APPLE_RELEASE",
    "PENDING_DEVELOPER_RELEASE",
    "PROCESSING_FOR_APP_STORE",
    "WAITING_FOR_EXPORT_COMPLIANCE",
    "METADATA_REJECTED",
    "REJECTED",
    "INVALID_BINARY",
}

BLOCKING_RECOMMENDATION_STATES = {
    "READY_FOR_REVIEW",
    "WAITING_FOR_REVIEW",
    "IN_REVIEW",
    "PENDING_APPLE_RELEASE",
    "PENDING_DEVELOPER_RELEASE",
    "PROCESSING_FOR_APP_STORE",
    "WAITING_FOR_EXPORT_COMPLIANCE",
}

LIVE_STATES = {"READY_FOR_SALE"}

ANALYSIS_INSTRUCTION = (
    "Produire une réflexion stratégique longue seulement si les données le justifient: utiliser les "
    "valeurs primaires filtrées sur report_date pour tout diagnostic quotidien et toute comparaison; "
    "les champs *_total_available servent uniquement à l'audit de collecte. Lire freshness/report_date, "
    "history J-7/J-30, funnel_by_source, funnel_by_territory, sales/pricing, reviews, metadata, "
    "screenshot_inventory et quality_signals. Distinguer signal réel, bruit probable, hypothèse et "
    "donnée manquante. Avant toute recommandation produit, pricing, ASO, screenshots ou metadata, "
    "vérifier app.review_pipeline: si has_blocking_pipeline_change vaut true ou si une version est "
    "READY_FOR_REVIEW, WAITING_FOR_REVIEW, IN_REVIEW, PENDING_APPLE_RELEASE, "
    "PENDING_DEVELOPER_RELEASE, PROCESSING_FOR_APP_STORE ou WAITING_FOR_EXPORT_COMPLIANCE, traiter ces "
    "changements comme déjà engagés et proposer uniquement des actions compatibles."
)

REDACTED_REVIEW_DETAIL_FIELDS = {
    "contactEmail",
    "contactFirstName",
    "contactLastName",
    "contactPhone",
    "demoAccountName",
    "demoAccountPassword",
    "notes",
}


def load_metrics() -> dict[str, Any]:
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def save_metrics(payload: dict[str, Any]) -> None:
    METRICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_get(client: asc.ASCClient, path: str) -> tuple[Any | None, str | None]:
    try:
        return client.get(path), None
    except Exception as exc:
        return None, str(exc)


def included_by_type_and_id(resp: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(item.get("type") or ""), str(item.get("id") or "")): item
        for item in resp.get("included") or []
        if item.get("type") and item.get("id")
    }


def relationship_items(resource: dict[str, Any], name: str) -> list[dict[str, str]]:
    data = ((resource.get("relationships") or {}).get(name) or {}).get("data")
    if not data:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def included_resources(
    resource: dict[str, Any],
    name: str,
    included: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    resources = []
    for item in relationship_items(resource, name):
        found = included.get((str(item.get("type") or ""), str(item.get("id") or "")))
        if found:
            resources.append(found)
    return resources


def public_review_detail(review_detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if not review_detail:
        return None
    attrs = review_detail.get("attributes") or {}
    public_attrs = {
        key: value
        for key, value in attrs.items()
        if key not in REDACTED_REVIEW_DETAIL_FIELDS
    }
    return {
        "id": review_detail.get("id"),
        "attributes": public_attrs,
        "redacted_fields": sorted(key for key in REDACTED_REVIEW_DETAIL_FIELDS if attrs.get(key)),
        "has_contact_email": bool(attrs.get("contactEmail")),
        "has_contact_phone": bool(attrs.get("contactPhone")),
        "has_demo_account": bool(attrs.get("demoAccountName") or attrs.get("demoAccountPassword")),
        "has_notes": bool(attrs.get("notes")),
    }


def compact_build(build: dict[str, Any] | None) -> dict[str, Any] | None:
    if not build:
        return None
    attrs = build.get("attributes") or {}
    return {
        "id": build.get("id"),
        "version": attrs.get("version"),
        "uploaded_date": attrs.get("uploadedDate"),
        "processing_state": attrs.get("processingState"),
        "min_os_version": attrs.get("minOsVersion"),
        "ls_minimum_system_version": attrs.get("lsMinimumSystemVersion"),
        "computed_min_macos_version": attrs.get("computedMinMacOsVersion"),
        "expired": attrs.get("expired"),
        "uses_non_exempt_encryption": attrs.get("usesNonExemptEncryption"),
    }


def compact_localization(localization: dict[str, Any]) -> dict[str, Any]:
    attrs = localization.get("attributes") or {}
    return {
        "id": localization.get("id"),
        "locale": attrs.get("locale"),
        "name": attrs.get("name"),
        "subtitle": attrs.get("subtitle"),
        "privacy_policy_url": attrs.get("privacyPolicyUrl"),
        "privacy_policy_text": attrs.get("privacyPolicyText"),
        "promotional_text": attrs.get("promotionalText"),
        "description": attrs.get("description"),
        "keywords": attrs.get("keywords"),
        "marketing_url": attrs.get("marketingUrl"),
        "support_url": attrs.get("supportUrl"),
        "whats_new": attrs.get("whatsNew"),
    }


def compact_phased_release(phased_release: dict[str, Any] | None) -> dict[str, Any] | None:
    if not phased_release:
        return None
    attrs = phased_release.get("attributes") or {}
    return {
        "id": phased_release.get("id"),
        "phased_release_state": attrs.get("phasedReleaseState"),
        "start_date": attrs.get("startDate"),
        "total_pause_duration": attrs.get("totalPauseDuration"),
        "current_day_number": attrs.get("currentDayNumber"),
    }


def compact_submission(submission: dict[str, Any] | None) -> dict[str, Any] | None:
    if not submission:
        return None
    return {
        "id": submission.get("id"),
        "attributes": submission.get("attributes") or {},
    }


def compact_version(
    version: dict[str, Any],
    included: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    attrs = version.get("attributes") or {}
    state = attrs.get("appStoreState")
    localizations = included_resources(version, "appStoreVersionLocalizations", included)
    builds = included_resources(version, "build", included)
    review_details = included_resources(version, "appStoreReviewDetail", included)
    submissions = included_resources(version, "appStoreVersionSubmission", included)
    phased_releases = included_resources(version, "appStoreVersionPhasedRelease", included)
    return {
        "id": version.get("id"),
        "platform": attrs.get("platform"),
        "version_string": attrs.get("versionString"),
        "app_store_state": state,
        "app_version_state": attrs.get("appVersionState"),
        "review_type": attrs.get("reviewType"),
        "release_type": attrs.get("releaseType"),
        "earliest_release_date": attrs.get("earliestReleaseDate"),
        "created_date": attrs.get("createdDate"),
        "downloadable": attrs.get("downloadable"),
        "uses_idfa": attrs.get("usesIdfa"),
        "is_live": state in LIVE_STATES,
        "is_pipeline": state in PIPELINE_STATES,
        "blocks_redundant_recommendations": state in BLOCKING_RECOMMENDATION_STATES,
        "build": compact_build(builds[0] if builds else None),
        "localizations": [compact_localization(item) for item in localizations],
        "app_store_review_detail": public_review_detail(review_details[0] if review_details else None),
        "app_store_version_submission": compact_submission(submissions[0] if submissions else None),
        "app_store_version_phased_release": compact_phased_release(phased_releases[0] if phased_releases else None),
    }


def iso_timestamp(value: Any) -> float:
    if not isinstance(value, str) or not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def sort_version_key(version: dict[str, Any]) -> tuple[int, float]:
    state = version.get("app_store_state")
    priority = 0 if state in BLOCKING_RECOMMENDATION_STATES else 1 if state in PIPELINE_STATES else 2
    return priority, -iso_timestamp(version.get("created_date"))


def fetch_review_pipeline(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    path = (
        f"/apps/{app_id}/appStoreVersions"
        "?limit=200"
        "&include=appStoreVersionLocalizations,build,appStoreReviewDetail,"
        "appStoreVersionSubmission,appStoreVersionPhasedRelease"
        "&fields[appStoreVersions]=platform,versionString,appStoreState,appVersionState,"
        "reviewType,releaseType,earliestReleaseDate,usesIdfa,downloadable,createdDate,"
        "appStoreVersionLocalizations,build,appStoreReviewDetail,appStoreVersionSubmission,"
        "appStoreVersionPhasedRelease"
        "&fields[builds]=version,uploadedDate,processingState,minOsVersion,"
        "lsMinimumSystemVersion,computedMinMacOsVersion,expired,usesNonExemptEncryption"
        "&fields[appStoreVersionLocalizations]=locale,promotionalText,description,"
        "keywords,marketingUrl,supportUrl,whatsNew"
        "&fields[appStoreReviewDetails]=contactEmail,contactFirstName,contactLastName,"
        "contactPhone,demoAccountName,demoAccountPassword,notes"
        "&fields[appStoreVersionPhasedReleases]=phasedReleaseState,startDate,"
        "totalPauseDuration,currentDayNumber"
    )
    resp, error = safe_get(client, path)
    if error:
        return {"available": False, "source": "App Store Connect appStoreVersions", "error": error}
    if not isinstance(resp, dict):
        return {
            "available": False,
            "source": "App Store Connect appStoreVersions",
            "raw_type": type(resp).__name__,
        }

    included = included_by_type_and_id(resp)
    versions = [compact_version(item, included) for item in resp.get("data") or []]
    versions = sorted(versions, key=sort_version_key)
    pipeline_versions = [item for item in versions if item.get("is_pipeline")]
    blocking_versions = [item for item in versions if item.get("blocks_redundant_recommendations")]
    live_versions = [item for item in versions if item.get("is_live")]
    selected_versions = list(pipeline_versions)
    if live_versions and all(item.get("id") != live_versions[0].get("id") for item in selected_versions):
        selected_versions.append(live_versions[0])
    return {
        "available": True,
        "source": "App Store Connect appStoreVersions",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "has_pending_version": bool(pipeline_versions),
        "has_blocking_pipeline_change": bool(blocking_versions),
        "pipeline_states": sorted({item["app_store_state"] for item in pipeline_versions if item.get("app_store_state")}),
        "blocking_recommendation_states": sorted(
            {item["app_store_state"] for item in blocking_versions if item.get("app_store_state")}
        ),
        "version_count": len(versions),
        "included_version_count": len(selected_versions),
        "omitted_historical_version_count": max(len(versions) - len(selected_versions), 0),
        "pipeline_version_count": len(pipeline_versions),
        "versions": selected_versions,
        "automation_context": [
            "Lire ce bloc avant toute recommandation ASO, screenshots, metadata, pricing ou produit.",
            "Si has_blocking_pipeline_change vaut true, ne pas proposer comme prochaine action un changement deja contenu dans la version en attente/review.",
            "Comparer les localizations et le build de la version pipeline avec les metriques actuelles avant de conclure.",
        ],
    }


def enrich(metrics: dict[str, Any], client: asc.ASCClient) -> dict[str, Any]:
    metrics["analysis_instruction"] = ANALYSIS_INSTRUCTION
    metrics["review_pipeline_source"] = {
        "versions": "App Store Connect appStoreVersions endpoint, best effort",
        "sensitive_fields": "App Review contact, demo account and notes are redacted from committed JSON",
        "blocking_recommendation_states": sorted(BLOCKING_RECOMMENDATION_STATES),
    }
    for app in metrics.get("apps", []):
        app_id = ((app.get("app") or {}).get("app_id") or app.get("app_id") or "")
        if not app_id:
            app["review_pipeline"] = {
                "available": False,
                "source": "App Store Connect appStoreVersions",
                "error": "missing app_id",
            }
            continue
        app["review_pipeline"] = fetch_review_pipeline(client, app_id)
    return metrics


def main() -> None:
    metrics = load_metrics()
    config = asc.load_config()
    client = asc.ASCClient(config)
    save_metrics(enrich(metrics, client))


if __name__ == "__main__":
    main()
