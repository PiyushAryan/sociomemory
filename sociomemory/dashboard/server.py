from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from sociomemory.dashboard.export import DashboardService

WEB_DIST_DIR = Path(__file__).parent / "web" / "dist"


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "SociomemoryDashboard/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api("GET", parsed.path, parse_qs(parsed.query))
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        self._handle_api("POST", parsed.path, parse_qs(parsed.query))

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        self._handle_api("DELETE", parsed.path, parse_qs(parsed.query))

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[sociomemory-dashboard] {self.address_string()} - {fmt % args}")

    def _serve_static(self, path: str) -> None:
        root = _frontend_root()
        if path in {"", "/"}:
            file_path = root / "index.html"
        else:
            file_path = root / path.lstrip("/")
            if not file_path.exists():
                file_path = root / "index.html"

        if not file_path.exists() or not file_path.is_file():
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        payload = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_api(self, method: str, path: str, query: dict[str, list[str]]) -> None:
        try:
            payload = self._run_async(self._route(method, path, query))
        except LookupError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # pragma: no cover - intentionally user-facing
            self._send_json(
                {"error": type(exc).__name__, "detail": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR
            )
            return
        self._send_json(payload)

    async def _route(self, method: str, path: str, query: dict[str, list[str]]) -> dict[str, Any]:
        if method == "GET" and path == "/api/health":
            return {"status": "ok"}

        async with _service() as service:
            if method == "GET" and path == "/api/children":
                return await service.list_children(limit=_int_query(query, "limit", 100))

            parts = [unquote(part) for part in path.split("/") if part]
            if len(parts) < 3 or parts[0] != "api" or parts[1] != "children":
                raise LookupError(path)

            child_id = parts[2]
            action = parts[3:] if len(parts) > 3 else []

            if method == "GET" and action == ["summary"]:
                return await service.summary(child_id)
            if method == "GET" and action == ["graph"]:
                return await service.graph_export(
                    child_id=child_id,
                    start_id=_str_query(query, "start_id"),
                    max_depth=_int_query(query, "max_depth", 3),
                    min_confidence=_float_query(query, "min_confidence", 0.0),
                    limit=_int_query(query, "limit", 200),
                )
            if method == "GET" and len(action) == 2 and action[0] == "nodes":
                return await service.node_detail(child_id, action[1])
            if method == "GET" and action == ["stale"]:
                return await service.stale_nodes(child_id)
            if method == "GET" and action == ["profile"]:
                return await service.profile(child_id)
            if method == "GET" and action == ["context"]:
                return await service.context(child_id)
            if method == "GET" and action == ["coaching"]:
                return await service.coaching(child_id)
            if method == "GET" and action == ["privacy", "export"]:
                return await service.privacy_export(child_id)
            if method == "DELETE" and action == ["privacy"]:
                return await service.privacy_erase(child_id)
            if method == "POST" and action == ["ingest"]:
                body = self._read_json()
                return await service.ingest(
                    child_id=child_id,
                    text=str(body.get("text", "")),
                    source=str(body.get("source", "conversation")),
                )
            if method == "POST" and action == ["person"]:
                body = self._read_json()
                places = body.get("places")
                if isinstance(places, str):
                    places = [p.strip() for p in places.split(",")]
                return await service.ingest_person(
                    child_id=child_id,
                    name=_opt_str(body.get("name")),
                    area=_opt_str(body.get("area")),
                    school=_opt_str(body.get("school")),
                    places=[p for p in (places or []) if p],
                    notes=_opt_str(body.get("notes")),
                )
            if method == "POST" and action == ["episodes", "segment"]:
                return await service.segment_episodes(child_id)
            if method == "POST" and action == ["location", "acquire"]:
                body = self._read_json()
                return await service.acquire_location(
                    child_id=child_id,
                    lat=_required_float(body.get("lat"), "lat"),
                    lng=_required_float(body.get("lng"), "lng"),
                    accuracy_m=_optional_float(body.get("accuracy_m")),
                )

            raise LookupError(path)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _run_async(coro):
        return asyncio.run(coro)


class _service:
    def __init__(self) -> None:
        self.service = DashboardService.from_env()

    async def __aenter__(self) -> DashboardService:
        await self.service.connect()
        return self.service

    async def __aexit__(self, *args: Any) -> None:
        await self.service.close()


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _str_query(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    return values[0] if values and values[0] else None


def _int_query(query: dict[str, list[str]], key: str, default: int) -> int:
    values = query.get(key)
    return int(values[0]) if values and values[0] else default


def _float_query(query: dict[str, list[str]], key: str, default: float) -> float:
    values = query.get(key)
    return float(values[0]) if values and values[0] else default


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _required_float(value: Any, name: str) -> float:
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    return float(value)


def _frontend_root() -> Path:
    return WEB_DIST_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local sociomemory graph explorer.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"sociomemory graph explorer running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping sociomemory graph explorer.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
