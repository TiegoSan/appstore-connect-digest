#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DEFAULT_SITE_ROOT = Path("/Users/gautier/GogoLabs/Apps/Gogolabs.fr")


def env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, str(default))).expanduser()


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def run_step(command: list[str], env: dict[str, str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=240)
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def refresh_metrics(site_root: Path) -> tuple[int, dict[str, object]]:
    env = os.environ.copy()
    env.update(load_dotenv(ROOT / ".env"))
    missing = [
        name
        for name in ["ASC_ISSUER_ID", "ASC_KEY_ID"]
        if not env.get(name) and not env.get(name.replace("ASC_", "APPSTORE_CONNECT_"))
    ]
    if not env.get("ASC_PRIVATE_KEY") and not env.get("ASC_PRIVATE_KEY_PATH") and not env.get("APPSTORE_CONNECT_PRIVATE_KEY_PATH"):
        missing.append("ASC_PRIVATE_KEY or ASC_PRIVATE_KEY_PATH")
    if missing:
        return 400, {"ok": False, "error": "missing_credentials", "missing": missing}
    commands = [
        ["python3", "collect_latest_metrics.py"],
        ["python3", "enrich_review_metrics.py"],
        ["python3", "enrich_pricing_metrics.py"],
        ["python3", "enrich_market_metrics.py"],
        ["python3", "appstore_dashboard.py", "--copy-to-site", str(site_root / "private" / "appstore")],
    ]
    steps = []
    for command in commands:
        step = run_step(command, env)
        steps.append(step)
        if step["returncode"] != 0:
            return 500, {"ok": False, "failed": step["command"], "steps": steps}
    return 200, {"ok": True, "steps": steps}


class DashboardHandler(SimpleHTTPRequestHandler):
    site_root = DEFAULT_SITE_ROOT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.site_root), **kwargs)

    def end_headers(self) -> None:
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        if self.path.startswith("/private/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/private/appstore/api/health":
            self.send_json(200, {"ok": True, "service": "appstore-dashboard"})
            return
        if parsed.path == "/private":
            self.send_response(308)
            self.send_header("Location", "/private/")
            self.end_headers()
            return
        if parsed.path == "/private/":
            self.send_response(308)
            self.send_header("Location", "/private/appstore/")
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/private/appstore/api/refresh":
            self.send_error(404)
            return
        status, payload = refresh_metrics(self.site_root)
        self.send_json(status, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the private App Store dashboard with a local API refresh endpoint.")
    parser.add_argument("--site-root", type=Path, default=env_path("APPSTORE_DASHBOARD_SITE_ROOT", DEFAULT_SITE_ROOT))
    parser.add_argument("--host", default=os.environ.get("APPSTORE_DASHBOARD_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=env_int("APPSTORE_DASHBOARD_PORT", 4173))
    args = parser.parse_args()

    DashboardHandler.site_root = args.site_root
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Serving {args.site_root} on http://{args.host}:{args.port}/")
    print("Refresh endpoint: POST /private/appstore/api/refresh")
    server.serve_forever()


if __name__ == "__main__":
    main()
