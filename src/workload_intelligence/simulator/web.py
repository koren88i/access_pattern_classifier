from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from workload_intelligence.simulator.capabilities import capability_payload
from workload_intelligence.simulator.matcher_source import matcher_source_for
from workload_intelligence.simulator.runner import DEFAULT_OUTPUT_ROOT, run_scenario_text
from workload_intelligence.simulator.scenario import ScenarioValidationError
from workload_intelligence.simulator.ui_page import HTML


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def _text_response(handler: BaseHTTPRequestHandler, status: int, text: str, content_type: str = "text/plain") -> None:
    encoded = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", f"{content_type}; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def make_handler(output_root: Path):
    root = output_root.resolve()

    class SimulatorHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                _text_response(self, HTTPStatus.OK, HTML, content_type="text/html")
                return
            if self.path == "/api/capabilities":
                _json_response(self, HTTPStatus.OK, capability_payload())
                return
            if self.path.startswith("/api/matcher-source"):
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                platform = query.get("platform", [""])[0]
                primitive = query.get("primitive", [""])[0]
                selected_primitives = [
                    item
                    for item in query.get("primitives", [""])[0].split(",")
                    if item
                ]
                if not platform or not primitive:
                    _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "platform and primitive are required"})
                    return
                _json_response(self, HTTPStatus.OK, matcher_source_for(platform, primitive, selected_primitives))
                return
            if self.path.startswith("/runs/"):
                self._serve_artifact()
                return
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/api/run":
                _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            scenario_text = self.rfile.read(length).decode("utf-8")
            try:
                result = run_scenario_text(scenario_text, output_root=root)
            except ScenarioValidationError as exc:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            artifacts = [
                {"name": name, "href": f"/runs/{result['run_id']}/{name}"}
                for name in (
                    "scenario.yaml",
                    "events.json",
                    "profiles.json",
                    "report.json",
                    "dashboard.txt",
                    "platform.txt",
                    "templates.txt",
                    "primitive-weights.txt",
                    "validation.json",
                )
            ]
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "run_id": result["run_id"],
                    "dashboard": result["dashboard"],
                    "validation": result["validation"],
                    "artifacts": artifacts,
                },
            )

        def _serve_artifact(self) -> None:
            relative = unquote(self.path.removeprefix("/runs/"))
            candidate = (root / relative).resolve()
            if root not in candidate.parents:
                _json_response(self, HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            if not candidate.is_file():
                _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            content_type = "application/json" if candidate.suffix == ".json" else "text/plain"
            _text_response(self, HTTPStatus.OK, candidate.read_text(encoding="utf-8"), content_type=content_type)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return SimulatorHandler


def serve_ui(
    host: str = "127.0.0.1",
    port: int = 8765,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), make_handler(output_root))
    print(f"Workload simulator UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
