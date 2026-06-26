#!/usr/bin/env python3
"""Fetch App Store Connect Analytics download reports.

Usage:
  python3 appstore_analytics.py list-apps
  python3 appstore_analytics.py downloads perroquet
  python3 appstore_analytics.py downloads coupez --create-snapshot
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import jwt
except ImportError as exc:
    raise SystemExit("PyJWT manquant. Installer avec: python3 -m pip install PyJWT cryptography") from exc

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "appstore_config.json"
ENV_PATH = ROOT / ".env"
BASE_URL = "https://api.appstoreconnect.apple.com/v1"


def load_local_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config() -> dict[str, Any]:
    load_local_env()
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)
    config["issuer_id"] = os.environ.get("ASC_ISSUER_ID") or os.environ.get("APPSTORE_CONNECT_ISSUER_ID") or config.get("issuer_id")
    config["key_id"] = os.environ.get("ASC_KEY_ID") or os.environ.get("APPSTORE_CONNECT_KEY_ID") or config.get("key_id")

    private_key = os.environ.get("ASC_PRIVATE_KEY") or os.environ.get("APPSTORE_CONNECT_PRIVATE_KEY")
    if private_key:
        if not config["key_id"]:
            raise RuntimeError("ASC_KEY_ID/APPSTORE_CONNECT_KEY_ID manquant.")
        key_dir = Path(os.environ.get("RUNNER_TEMP", ROOT))
        key_dir.mkdir(parents=True, exist_ok=True)
        key_path = key_dir / f"AuthKey_{config['key_id']}.p8"
        key_path.write_text(private_key.replace("\\n", "\n"), encoding="utf-8")
        key_path.chmod(0o600)
        config["private_key_path"] = str(key_path)
        return config

    env_key_path = os.environ.get("ASC_PRIVATE_KEY_PATH") or os.environ.get("APPSTORE_CONNECT_PRIVATE_KEY_PATH")
    if env_key_path:
        config["private_key_path"] = env_key_path

    if not config.get("private_key_path") and config.get("key_id"):
        config["private_key_path"] = f"AuthKey_{config['key_id']}.p8"
    if not config.get("private_key_path"):
        return config

    key_path = Path(config["private_key_path"])
    if not key_path.is_absolute():
        key_path = ROOT / key_path
    config["private_key_path"] = str(key_path)
    return config


def make_token(config: dict[str, Any]) -> str:
    if not config.get("issuer_id"):
        raise RuntimeError("ASC_ISSUER_ID/APPSTORE_CONNECT_ISSUER_ID manquant.")
    if not config.get("key_id"):
        raise RuntimeError("ASC_KEY_ID/APPSTORE_CONNECT_KEY_ID manquant.")
    if not config.get("private_key_path"):
        raise RuntimeError("ASC_PRIVATE_KEY ou ASC_PRIVATE_KEY_PATH manquant.")
    with open(config["private_key_path"], "r", encoding="utf-8") as f:
        private_key = f.read()
    now = int(time.time())
    payload = {
        "iss": config["issuer_id"],
        "iat": now,
        "exp": now + 20 * 60,
        "aud": "appstoreconnect-v1",
    }
    headers = {"kid": config["key_id"], "typ": "JWT"}
    return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)


class ASCClient:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.token = make_token(config)

    def request(self, method: str, path_or_url: str, body: dict[str, Any] | None = None, auth: bool = True) -> Any:
        url = path_or_url if path_or_url.startswith("http") else BASE_URL + path_or_url
        cmd = ["curl", "-g", "-sS", "-w", "\n__HTTP_STATUS__:%{http_code}\n", "-X", method]
        if auth:
            cmd.extend(["-H", f"Authorization: Bearer {self.token}"])
        if body is not None:
            cmd.extend(["-H", "Content-Type: application/json", "--data-binary", json.dumps(body)])
        cmd.append(url)

        proc = subprocess.run(cmd, capture_output=True, timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))

        marker = b"\n__HTTP_STATUS__:"
        raw, sep, status_raw = proc.stdout.rpartition(marker)
        if not sep:
            raise RuntimeError("curl response missing HTTP status marker")
        status = int(status_raw.strip() or b"0")
        if status >= 400:
            payload = raw.decode("utf-8", errors="replace")
            try:
                details = json.loads(payload)
            except Exception:
                details = payload
            raise RuntimeError(f"HTTP {status} {method} {url}: {details}")
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return raw

    def get(self, path_or_url: str, auth: bool = True) -> Any:
        return self.request("GET", path_or_url, auth=auth)

    def post(self, path: str, body: dict[str, Any]) -> Any:
        return self.request("POST", path, body=body)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "app"


def resolve_app(config: dict[str, Any], app_ref: str) -> dict[str, str]:
    apps = config.get("apps", {})
    if app_ref in apps:
        return apps[app_ref]
    for key, app in apps.items():
        if app_ref == app.get("app_id") or app_ref.lower() == app.get("name", "").lower():
            return app
    known = ", ".join(sorted(apps))
    raise SystemExit(f"App inconnue: {app_ref}. Apps connues: {known}")


def list_apps(config: dict[str, Any]) -> None:
    for key, app in sorted(config.get("apps", {}).items()):
        print(f"{key:18} {app['app_id']}  {app['name']}  {app['bundle_id']}")


def ensure_report_request(client: ASCClient, app_id: str, access_type: str) -> str:
    body = {
        "data": {
            "type": "analyticsReportRequests",
            "attributes": {"accessType": access_type},
            "relationships": {"app": {"data": {"type": "apps", "id": app_id}}},
        }
    }
    resp = client.post("/analyticsReportRequests", body)
    return resp["data"]["id"]


def ensure_snapshot(client: ASCClient, app_id: str) -> str:
    return ensure_report_request(client, app_id, "ONE_TIME_SNAPSHOT")


def ensure_ongoing(client: ASCClient, app_id: str) -> str:
    return ensure_report_request(client, app_id, "ONGOING")


def get_report_requests(client: ASCClient, app_id: str) -> list[dict[str, Any]]:
    resp = client.get(f"/apps/{app_id}/analyticsReportRequests?limit=200")
    return resp.get("data", [])


def get_reports(client: ASCClient, request_id: str) -> list[dict[str, Any]]:
    resp = client.get(f"/analyticsReportRequests/{request_id}/reports?limit=200")
    return resp.get("data", [])


def get_instances(client: ASCClient, report_id: str) -> list[dict[str, Any]]:
    resp = client.get(f"/analyticsReports/{report_id}/instances?limit=200")
    return resp.get("data", [])


SEGMENT_LIMIT_ATTEMPTS: tuple[int | None, ...] = (200, 100, 50, 10, 1, None)
RETRIABLE_SEGMENT_STATUSES = {"500"}


class SegmentFetchError(RuntimeError):
    def __init__(self, instance_id: str, attempts: list[dict[str, Any]]):
        self.instance_id = instance_id
        self.attempts = attempts
        details = "; ".join(f"limit={item['limit']} -> {item['status']}" for item in attempts)
        super().__init__(f"segment fetch failed for {instance_id}: {details}")


def http_status_from_error(error: Exception) -> str | None:
    match = re.search(r"HTTP\s+(\d+)", str(error))
    return match.group(1) if match else None


def segment_path(instance_id: str, limit: int | None) -> str:
    suffix = "" if limit is None else f"?limit={limit}"
    return f"/analyticsReportInstances/{instance_id}/segments{suffix}"


def segment_limit_label(limit: int | None) -> str:
    return "default" if limit is None else str(limit)


def collect_segment_pages(client: ASCClient, response: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    segments = list(response.get("data") or [])
    page_count = 1
    next_url = (response.get("links") or {}).get("next")
    while next_url:
        response = client.get(next_url)
        segments.extend(response.get("data") or [])
        page_count += 1
        next_url = (response.get("links") or {}).get("next")
    return segments, page_count


def get_segments(client: ASCClient, instance_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for limit in SEGMENT_LIMIT_ATTEMPTS:
        label = segment_limit_label(limit)
        try:
            response = client.get(segment_path(instance_id, limit))
            segments, page_count = collect_segment_pages(client, response)
            attempts.append({"limit": label, "status": "200"})
            return segments, {
                "selected_limit": label,
                "attempts": attempts,
                "page_count": page_count,
                "recovered_from_500": len(attempts) > 1,
            }
        except Exception as exc:
            status = http_status_from_error(exc) or "error"
            attempts.append({
                "limit": label,
                "status": status,
                "error": str(exc),
            })
            if status not in RETRIABLE_SEGMENT_STATUSES:
                raise SegmentFetchError(instance_id, attempts) from exc
    raise SegmentFetchError(instance_id, attempts)


def download_segment(client: ASCClient, url: str) -> tuple[list[str], list[dict[str, str]], str]:
    raw = client.get(url, auth=False)
    if isinstance(raw, str):
        data = raw.encode("utf-8")
    else:
        data = raw
    try:
        text = gzip.decompress(data).decode("utf-8-sig")
    except Exception:
        text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return reader.fieldnames or [], list(reader), text


def count_field_value(row: dict[str, str], field: str) -> int:
    raw = (row.get(field) or "0").replace(",", "")
    return int(raw) if raw.isdigit() else 0


def count_value(row: dict[str, str]) -> int:
    return count_field_value(row, "Counts")


ROW_VALUE_FIELDS = {"Counts", "Unique Counts"}


def row_identity(row: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, value or "") for key, value in row.items() if key not in ROW_VALUE_FIELDS))


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: dict[tuple[tuple[str, str], ...], dict[str, str]] = {}
    for row in rows:
        deduped[row_identity(row)] = row
    return list(deduped.values())


def merged_request_rows(rows_by_request_type: dict[str, list[dict[str, str]]]) -> tuple[list[dict[str, str]], str]:
    snapshot_rows = dedupe_rows(rows_by_request_type.get("ONE_TIME_SNAPSHOT") or [])
    ongoing_rows = dedupe_rows(rows_by_request_type.get("ONGOING") or [])
    if snapshot_rows and ongoing_rows:
        return dedupe_rows(snapshot_rows + ongoing_rows), "ONE_TIME_SNAPSHOT+ONGOING"
    if ongoing_rows:
        return ongoing_rows, "ONGOING"
    if snapshot_rows:
        return snapshot_rows, "ONE_TIME_SNAPSHOT"
    return [], "NONE"


def aggregate(rows: list[dict[str, str]], dim: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if dim in row:
            counter[row.get(dim) or ""] += count_value(row)
    return dict(counter)


def aggregate_field(rows: list[dict[str, str]], dim: str, field: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if dim in row:
            counter[row.get(dim) or ""] += count_field_value(row, field)
    return dict(counter)


def aggregate_download_type_by_date(rows: list[dict[str, str]], download_type: str) -> dict[str, int]:
    return aggregate([row for row in rows if row.get("Download Type") == download_type], "Date")


def filter_event(rows: list[dict[str, str]], event: str) -> list[dict[str, str]]:
    return [row for row in rows if row.get("Event") == event]


def pct(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator * 100, 2)


def top_sorted(data: dict[str, int]) -> dict[str, int]:
    return dict(sorted(data.items(), key=lambda kv: (-kv[1], kv[0])))


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def markdown_report(app: dict[str, str], result: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Rapport téléchargements - {app['name']}")
    lines.append("")
    lines.append(f"Genere le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} via App Store Connect API.")
    lines.append("")
    lines.append("## Synthese")
    lines.append("")
    lines.append(f"- App Apple Identifier: `{app['app_id']}`")
    lines.append(f"- Bundle ID: `{app['bundle_id']}`")
    lines.append(f"- SKU: `{app['sku']}`")
    lines.append(f"- Total standard: **{result.get('standard_total', 0)}**")
    lines.append(f"- First-time downloads: **{result.get('first_time_downloads', 0)}**")
    if result.get("engagement_available"):
        lines.append(f"- Impressions: **{result.get('impressions', 0)}**")
        lines.append(f"- Impressions uniques: **{result.get('unique_impressions', 0)}**")
        lines.append(f"- Vues page produit: **{result.get('product_page_views', 0)}**")
        lines.append(f"- Vues page produit uniques: **{result.get('unique_product_page_views', 0)}**")
        lines.append(f"- Taps: **{result.get('taps', 0)}**")
        conversion_rate = result.get("conversion_rate")
        if conversion_rate is not None:
            lines.append(f"- Conversion first-time / impressions uniques: **{conversion_rate}%**")
        lines.append(f"- Page view rate / impressions uniques: **{result.get('page_view_rate') or 0}%**")
    lines.append("")

    for section, title in [
        ("by_download_type", "Par Type"),
        ("by_date", "Par Date"),
        ("by_territory", "Par Pays"),
        ("by_source_type", "Par Source"),
        ("by_device", "Par Device"),
        ("by_app_version", "Par Version App"),
        ("by_platform_version", "Par Version OS"),
    ]:
        data = result.get(section) or {}
        if data:
            lines.append(f"## {title}")
            lines.append("")
            lines.append(render_table(["Dimension", "Count"], [[k or "(vide)", v] for k, v in top_sorted(data).items()]))
            lines.append("")

    if result.get("engagement_available"):
        lines.append("## Engagement App Store")
        lines.append("")
        rows = [
            ["Impression", result.get("impressions", 0), result.get("unique_impressions", 0)],
            ["Page view", result.get("product_page_views", 0), result.get("unique_product_page_views", 0)],
            ["Tap", result.get("taps", 0), result.get("unique_taps", 0)],
        ]
        lines.append(render_table(["Event", "Count", "Unique"], rows))
        lines.append("")

        for section, title in [
            ("impressions_by_source_type", "Impressions par Source"),
            ("impressions_by_page_type", "Impressions par Page"),
            ("impressions_by_territory", "Impressions par Pays"),
            ("impressions_by_device", "Impressions par Device"),
            ("product_page_views_by_source_type", "Vues Page Produit par Source"),
            ("product_page_views_by_territory", "Vues Page Produit par Pays"),
        ]:
            data = result.get(section) or {}
            if data:
                lines.append(f"## {title}")
                lines.append("")
                lines.append(render_table(["Dimension", "Count"], [[k or "(vide)", v] for k, v in top_sorted(data).items()]))
                lines.append("")

    details = result.get("reports", [])
    if details:
        lines.append("## Rapports Apple")
        lines.append("")
        rows = []
        for report in details:
            rows.append([
                report.get("request_type"),
                report.get("name"),
                report.get("granularity"),
                report.get("processing_date"),
                report.get("row_count"),
                report.get("counts_total"),
            ])
        lines.append(render_table(["Request", "Rapport", "Granularite", "Processing", "Rows", "Counts"], rows))
        lines.append("")

    return "\n".join(lines)


def collect_downloads(config: dict[str, Any], app: dict[str, str], create_snapshot: bool) -> dict[str, Any]:
    client = ASCClient(config)
    app_id = app["app_id"]
    requests = get_report_requests(client, app_id)
    if not requests and create_snapshot:
        new_id = ensure_snapshot(client, app_id)
        requests = get_report_requests(client, app_id)
        print(f"Snapshot cree: {new_id}", file=sys.stderr)
    has_ongoing = any(r.get("attributes", {}).get("accessType") == "ONGOING" for r in requests)
    if create_snapshot and not has_ongoing:
        new_id = ensure_ongoing(client, app_id)
        requests = get_report_requests(client, app_id)
        print(f"Ongoing cree: {new_id}", file=sys.stderr)

    result: dict[str, Any] = {
        "app": app,
        "standard_total": 0,
        "first_time_downloads": 0,
        "by_date": {},
        "by_download_type": {},
        "by_territory": {},
        "by_source_type": {},
        "by_page_type": {},
        "by_device": {},
        "by_platform_version": {},
        "by_app_version": {},
        "engagement_available": False,
        "impressions": 0,
        "unique_impressions": 0,
        "product_page_views": 0,
        "unique_product_page_views": 0,
        "taps": 0,
        "unique_taps": 0,
        "conversion_rate": None,
        "conversion_first_time_downloads": 0,
        "conversion_date_overlap": [],
        "page_view_rate": None,
        "tap_rate": None,
        "engagement_by_event": {},
        "engagement_unique_by_event": {},
        "impressions_by_date": {},
        "impressions_by_source_type": {},
        "impressions_by_page_type": {},
        "impressions_by_territory": {},
        "impressions_by_device": {},
        "impressions_by_platform_version": {},
        "product_page_views_by_date": {},
        "product_page_views_by_source_type": {},
        "product_page_views_by_page_type": {},
        "product_page_views_by_territory": {},
        "product_page_views_by_device": {},
        "reports": [],
    }

    report_rows_by_request_type: dict[str, list[dict[str, str]]] = {"ONGOING": [], "ONE_TIME_SNAPSHOT": []}
    engagement_rows_by_request_type: dict[str, list[dict[str, str]]] = {"ONGOING": [], "ONE_TIME_SNAPSHOT": []}
    segment_errors: list[dict[str, Any]] = []
    all_report_summaries = []
    request_order = {"ONE_TIME_SNAPSHOT": 0, "ONGOING": 1}
    requests = sorted(requests, key=lambda r: request_order.get(r.get("attributes", {}).get("accessType"), 9))

    for request in requests:
        request_id = request["id"]
        request_type = request.get("attributes", {}).get("accessType")
        reports = get_reports(client, request_id)
        analytics_reports = [
            r for r in reports
            if r.get("attributes", {}).get("name") in {
                "App Downloads Standard",
                "App Store Discovery and Engagement Standard",
            }
        ]
        for report in analytics_reports:
            name = report.get("attributes", {}).get("name")
            instances = get_instances(client, report["id"])
            for instance in instances:
                attrs = instance.get("attributes", {})
                if attrs.get("granularity") != "DAILY":
                    continue
                rows: list[dict[str, str]] = []
                columns: list[str] = []
                segment_count = 0
                segment_fetch: dict[str, Any] = {}
                try:
                    segments, segment_fetch = get_segments(client, instance["id"])
                except SegmentFetchError as exc:
                    segment_errors.append({
                        "request_type": request_type,
                        "request_id": request_id,
                        "report_id": report["id"],
                        "name": name,
                        "instance_id": instance["id"],
                        "granularity": attrs.get("granularity"),
                        "processing_date": attrs.get("processingDate"),
                        "error": str(exc),
                        "attempts": exc.attempts,
                    })
                    continue
                for segment in segments:
                    url = segment.get("attributes", {}).get("url")
                    if not url:
                        continue
                    try:
                        columns, seg_rows, _text = download_segment(client, url)
                    except Exception as exc:
                        segment_errors.append({
                            "request_type": request_type,
                            "request_id": request_id,
                            "report_id": report["id"],
                            "name": name,
                            "instance_id": instance["id"],
                            "granularity": attrs.get("granularity"),
                            "processing_date": attrs.get("processingDate"),
                            "segment_id": segment.get("id"),
                            "error": str(exc),
                        })
                        continue
                    rows.extend(seg_rows)
                    segment_count += 1
                counts_total = sum(count_value(row) for row in rows)
                summary = {
                    "request_type": request_type,
                    "request_id": request_id,
                    "report_id": report["id"],
                    "name": name,
                    "instance_id": instance["id"],
                    "granularity": attrs.get("granularity"),
                    "processing_date": attrs.get("processingDate"),
                    "segment_count": segment_count,
                    "row_count": len(rows),
                    "counts_total": counts_total,
                    "columns": columns,
                    "segment_fetch_limit": segment_fetch.get("selected_limit"),
                    "segment_fetch_attempts": segment_fetch.get("attempts") or [],
                    "segment_fetch_page_count": segment_fetch.get("page_count"),
                    "segment_fetch_recovered_from_500": bool(segment_fetch.get("recovered_from_500")),
                }
                all_report_summaries.append(summary)
                if name == "App Downloads Standard" and attrs.get("granularity") == "DAILY":
                    report_rows_by_request_type.setdefault(request_type or "", []).extend(rows)
                if name == "App Store Discovery and Engagement Standard" and attrs.get("granularity") == "DAILY":
                    engagement_rows_by_request_type.setdefault(request_type or "", []).extend(rows)

    result["reports"] = all_report_summaries
    result["segment_errors"] = segment_errors
    report_rows, standard_source_request_type = merged_request_rows(report_rows_by_request_type)
    result["standard_source_request_type"] = standard_source_request_type
    result["standard_total"] = sum(count_value(row) for row in report_rows)
    result["by_date"] = aggregate(report_rows, "Date")
    result["first_time_downloads_by_date"] = aggregate_download_type_by_date(report_rows, "First-time download")
    result["by_download_type"] = aggregate(report_rows, "Download Type")
    result["by_territory"] = aggregate(report_rows, "Territory")
    result["by_source_type"] = aggregate(report_rows, "Source Type")
    result["by_page_type"] = aggregate(report_rows, "Page Type")
    result["by_device"] = aggregate(report_rows, "Device")
    result["by_platform_version"] = aggregate(report_rows, "Platform Version")
    result["by_app_version"] = aggregate(report_rows, "App Version")
    result["first_time_downloads"] = result["by_download_type"].get("First-time download", 0)
    result["raw_standard_rows"] = report_rows

    engagement_rows, engagement_source_request_type = merged_request_rows(engagement_rows_by_request_type)
    result["engagement_source_request_type"] = engagement_source_request_type
    impression_rows = filter_event(engagement_rows, "Impression")
    product_page_view_rows = filter_event(engagement_rows, "Page view")
    tap_rows = filter_event(engagement_rows, "Tap")
    result["engagement_available"] = bool(engagement_rows)
    result["engagement_by_event"] = aggregate(engagement_rows, "Event")
    result["engagement_unique_by_event"] = aggregate_field(engagement_rows, "Event", "Unique Counts")
    result["impressions"] = sum(count_value(row) for row in impression_rows)
    result["unique_impressions"] = sum(count_field_value(row, "Unique Counts") for row in impression_rows)
    result["product_page_views"] = sum(count_value(row) for row in product_page_view_rows)
    result["unique_product_page_views"] = sum(count_field_value(row, "Unique Counts") for row in product_page_view_rows)
    result["taps"] = sum(count_value(row) for row in tap_rows)
    result["unique_taps"] = sum(count_field_value(row, "Unique Counts") for row in tap_rows)
    engagement_dates = {row.get("Date") for row in engagement_rows if row.get("Date")}
    conversion_download_rows = [
        row for row in report_rows
        if row.get("Date") in engagement_dates and row.get("Download Type") == "First-time download"
    ]
    conversion_dates = sorted({row.get("Date") for row in conversion_download_rows if row.get("Date")})
    conversion_first_time_downloads = sum(count_value(row) for row in conversion_download_rows)
    result["conversion_first_time_downloads"] = conversion_first_time_downloads
    result["conversion_date_overlap"] = conversion_dates
    result["conversion_rate"] = pct(conversion_first_time_downloads, result["unique_impressions"]) if conversion_dates else None
    result["page_view_rate"] = pct(result["product_page_views"], result["unique_impressions"])
    result["tap_rate"] = pct(result["taps"], result["unique_impressions"])
    result["impressions_by_date"] = aggregate(impression_rows, "Date")
    result["impressions_by_source_type"] = aggregate(impression_rows, "Source Type")
    result["impressions_by_page_type"] = aggregate(impression_rows, "Page Type")
    result["impressions_by_territory"] = aggregate(impression_rows, "Territory")
    result["impressions_by_device"] = aggregate(impression_rows, "Device")
    result["impressions_by_platform_version"] = aggregate(impression_rows, "Platform Version")
    result["product_page_views_by_date"] = aggregate(product_page_view_rows, "Date")
    result["product_page_views_by_source_type"] = aggregate(product_page_view_rows, "Source Type")
    result["product_page_views_by_page_type"] = aggregate(product_page_view_rows, "Page Type")
    result["product_page_views_by_territory"] = aggregate(product_page_view_rows, "Territory")
    result["product_page_views_by_device"] = aggregate(product_page_view_rows, "Device")
    result["raw_engagement_rows"] = engagement_rows
    return result


def save_outputs(app_ref: str, app: dict[str, str], result: dict[str, Any]) -> tuple[Path, Path]:
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(app_ref or app["name"])
    json_path = out_dir / f"{slug}-downloads-{stamp}.json"
    md_path = out_dir / f"{slug}-downloads-{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(app, result), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="App Store Connect Analytics helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-apps")
    downloads = sub.add_parser("downloads")
    downloads.add_argument("app", help="cle config, app id ou nom exact")
    downloads.add_argument("--create-snapshot", action="store_true", help="cree un ONE_TIME_SNAPSHOT si aucun rapport n'existe")
    downloads.add_argument("--json", action="store_true", help="affiche le JSON complet sur stdout")
    args = parser.parse_args()

    config = load_config()
    if args.cmd == "list-apps":
        list_apps(config)
        return

    if args.cmd == "downloads":
        app = resolve_app(config, args.app)
        result = collect_downloads(config, app, args.create_snapshot)
        json_path, md_path = save_outputs(args.app, app, result)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"JSON: {json_path}")
            print(f"Markdown: {md_path}")
            print(f"Total standard: {result['standard_total']}")
            print(f"First-time downloads: {result['first_time_downloads']}")
            if result.get("engagement_available"):
                print(f"Impressions: {result['impressions']}")
                print(f"Unique impressions: {result['unique_impressions']}")
                print(f"Product page views: {result['product_page_views']}")
                print(f"Unique product page views: {result['unique_product_page_views']}")
                print(f"Taps: {result['taps']}")


if __name__ == "__main__":
    main()
