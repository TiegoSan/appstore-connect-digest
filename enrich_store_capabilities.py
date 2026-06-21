#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import appstore_analytics as asc

ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "strategy" / "latest-metrics.json"


def load_metrics() -> dict[str, Any]:
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def save_metrics(payload: dict[str, Any]) -> None:
    METRICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_get(client: asc.ASCClient, path: str) -> tuple[Any | None, str | None]:
    try:
        return client.get(path), None
    except Exception as exc:
        return None, str(exc)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def attrs(resource: dict[str, Any]) -> dict[str, Any]:
    return resource.get("attributes") if isinstance(resource.get("attributes"), dict) else {}


def relationships(resource: dict[str, Any]) -> dict[str, Any]:
    return resource.get("relationships") if isinstance(resource.get("relationships"), dict) else {}


def relationship_count(resource: dict[str, Any], name: str) -> int | None:
    relation = relationships(resource).get(name)
    if not isinstance(relation, dict):
        return None
    data = relation.get("data")
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return 1
    meta_total = (((relation.get("meta") or {}).get("paging") or {}).get("total"))
    return meta_total if isinstance(meta_total, int) else None


def compact_iap(resource: dict[str, Any]) -> dict[str, Any]:
    item_attrs = attrs(resource)
    return {
        "id": resource.get("id"),
        "type": resource.get("type"),
        "name": item_attrs.get("name"),
        "product_id": item_attrs.get("productId"),
        "in_app_purchase_type": item_attrs.get("inAppPurchaseType"),
        "state": item_attrs.get("state"),
        "review_note": bool(item_attrs.get("reviewNote")),
        "family_sharable": item_attrs.get("familySharable"),
    }


def compact_subscription_group(resource: dict[str, Any]) -> dict[str, Any]:
    group_attrs = attrs(resource)
    return {
        "id": resource.get("id"),
        "reference_name": group_attrs.get("referenceName"),
        "subscriptions_count": relationship_count(resource, "subscriptions"),
    }


def compact_subscription(resource: dict[str, Any]) -> dict[str, Any]:
    sub_attrs = attrs(resource)
    return {
        "id": resource.get("id"),
        "name": sub_attrs.get("name"),
        "product_id": sub_attrs.get("productId"),
        "state": sub_attrs.get("state"),
        "subscription_period": sub_attrs.get("subscriptionPeriod"),
        "family_sharable": sub_attrs.get("familySharable"),
        "group_level": sub_attrs.get("groupLevel"),
    }


def compact_game_center_detail(resource: dict[str, Any]) -> dict[str, Any]:
    detail_attrs = attrs(resource)
    return {
        "id": resource.get("id"),
        "type": resource.get("type"),
        "state": detail_attrs.get("gameCenterState") or detail_attrs.get("state"),
        "achievements_count": relationship_count(resource, "gameCenterAchievements"),
        "leaderboards_count": relationship_count(resource, "gameCenterLeaderboards"),
        "challenges_count": relationship_count(resource, "gameCenterChallenges"),
        "activities_count": relationship_count(resource, "gameCenterActivities"),
        "app_versions_count": relationship_count(resource, "gameCenterAppVersions"),
    }


def collection_payload(source: str, resp: Any, compact) -> dict[str, Any]:
    if not isinstance(resp, dict):
        return {"available": False, "source": source, "raw_type": type(resp).__name__}
    data = resp.get("data") or []
    if isinstance(data, dict):
        data = [data]
    items = [compact(item) for item in data if isinstance(item, dict)]
    total = (((resp.get("meta") or {}).get("paging") or {}).get("total"))
    return {
        "available": True,
        "source": source,
        "fetched_at": now_iso(),
        "total": total if isinstance(total, int) else len(items),
        "returned": len(items),
        "items": items[:25],
        "omitted_count": max(len(items) - 25, 0),
    }


def fetch_with_fallbacks(client: asc.ASCClient, source: str, candidates: list[str], compact) -> dict[str, Any]:
    errors = []
    for path in candidates:
        resp, error = safe_get(client, path)
        if error:
            errors.append({"path": path, "error": error})
            continue
        payload = collection_payload(source, resp, compact)
        payload["endpoint"] = path
        if errors:
            payload["fallback_errors"] = errors
        return payload
    return {"available": False, "source": source, "errors": errors}


def fetch_in_app_purchases(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    return fetch_with_fallbacks(
        client,
        "App Store Connect in-app purchases",
        [
            f"/apps/{app_id}/inAppPurchases?limit=200",
            f"https://api.appstoreconnect.apple.com/v2/inAppPurchases?filter[app]={app_id}&limit=200",
        ],
        compact_iap,
    )


def fetch_subscription_groups(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    return fetch_with_fallbacks(
        client,
        "App Store Connect subscription groups",
        [
            f"/apps/{app_id}/subscriptionGroups?include=subscriptions&limit=200&limit[subscriptions]=200",
            f"/subscriptionGroups?filter[app]={app_id}&include=subscriptions&limit=200&limit[subscriptions]=200",
        ],
        compact_subscription_group,
    )


def fetch_subscriptions(client: asc.ASCClient, group_payload: dict[str, Any]) -> dict[str, Any]:
    subscriptions = []
    errors = []
    for group in group_payload.get("items") or []:
        group_id = group.get("id")
        if not group_id:
            continue
        path = f"/subscriptionGroups/{group_id}/subscriptions?limit=200"
        resp, error = safe_get(client, path)
        if error:
            errors.append({"group_id": group_id, "error": error})
            continue
        payload = collection_payload("App Store Connect subscriptions", resp, compact_subscription)
        subscriptions.extend(payload.get("items") or [])
    return {
        "available": bool(subscriptions) or bool(group_payload.get("available")),
        "source": "App Store Connect subscriptions",
        "fetched_at": now_iso(),
        "returned": len(subscriptions),
        "items": subscriptions[:25],
        "omitted_count": max(len(subscriptions) - 25, 0),
        "errors": errors,
    }


def fetch_game_center(client: asc.ASCClient, app_id: str) -> dict[str, Any]:
    resp, error = safe_get(client, f"/apps/{app_id}/gameCenterDetail")
    if error:
        return {"available": False, "source": "App Store Connect gameCenterDetail", "error": error}
    if not isinstance(resp, dict):
        return {
            "available": False,
            "source": "App Store Connect gameCenterDetail",
            "raw_type": type(resp).__name__,
        }
    data = resp.get("data") or {}
    if not isinstance(data, dict) or not data:
        return {
            "available": False,
            "source": "App Store Connect gameCenterDetail",
            "error": "missing gameCenterDetail data",
        }
    detail = compact_game_center_detail(data)
    return {
        "available": True,
        "source": "App Store Connect gameCenterDetail",
        "fetched_at": now_iso(),
        **detail,
    }


def unavailable(source: str, error: str) -> dict[str, Any]:
    return {"available": False, "source": source, "error": error}


def enrich(metrics: dict[str, Any], client: asc.ASCClient | None = None, api_error: str | None = None) -> dict[str, Any]:
    metrics["store_capabilities_source"] = {
        "in_app_purchases": "App Store Connect inAppPurchases endpoints, best effort",
        "subscriptions": "App Store Connect subscriptionGroups/subscriptions endpoints, best effort",
        "game_center": "App Store Connect gameCenterDetail endpoint, read-only best effort",
    }
    if api_error:
        metrics["store_capabilities_source"]["api_status"] = {"available": False, "error": api_error}

    for app in metrics.get("apps", []):
        app_id = ((app.get("app") or {}).get("app_id") or app.get("app_id") or "")
        if not app_id:
            app["in_app_purchases"] = unavailable("App Store Connect in-app purchases", "missing app_id")
            app["subscriptions"] = unavailable("App Store Connect subscriptions", "missing app_id")
            app["game_center"] = unavailable("App Store Connect gameCenterDetail", "missing app_id")
            continue
        if not client:
            app["in_app_purchases"] = unavailable("App Store Connect in-app purchases", api_error or "API unavailable")
            app["subscriptions"] = unavailable("App Store Connect subscriptions", api_error or "API unavailable")
            app["game_center"] = unavailable("App Store Connect gameCenterDetail", api_error or "API unavailable")
            continue

        iap = fetch_in_app_purchases(client, app_id)
        subscription_groups = fetch_subscription_groups(client, app_id)
        subscriptions = fetch_subscriptions(client, subscription_groups) if subscription_groups.get("available") else {
            "available": False,
            "source": "App Store Connect subscriptions",
            "error": "subscription groups unavailable",
        }
        app["in_app_purchases"] = iap
        app["subscriptions"] = {
            "available": bool(subscription_groups.get("available") or subscriptions.get("available")),
            "source": "App Store Connect subscriptionGroups/subscriptions",
            "groups": subscription_groups,
            "subscriptions": subscriptions,
        }
        app["game_center"] = fetch_game_center(client, app_id)
    return metrics


def main() -> None:
    metrics = load_metrics()
    try:
        config = asc.load_config()
        client = asc.ASCClient(config)
        save_metrics(enrich(metrics, client))
    except Exception as exc:
        save_metrics(enrich(metrics, None, str(exc)))


if __name__ == "__main__":
    main()
