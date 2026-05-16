from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from workload_intelligence.exporters.elastic import (
    DEFAULT_ELASTICSEARCH_URL,
    ElasticExportError,
    index_run,
)
from workload_intelligence.exporters.kibana import DEFAULT_KIBANA_URL, setup_data_views
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


def _iso_utc(value: Any) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_run_request(handler: BaseHTTPRequestHandler, body: str) -> dict[str, Any]:
    content_type = handler.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return {
            "scenario_text": body,
            "index_elastic": False,
            "include_raw_query": False,
            "setup_kibana_data_views": False,
            "elasticsearch_url": DEFAULT_ELASTICSEARCH_URL,
            "kibana_url": DEFAULT_KIBANA_URL,
        }
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ScenarioValidationError("request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ScenarioValidationError("request body must be a JSON object")
    scenario_text = payload.get("scenario") or payload.get("scenario_text")
    if not isinstance(scenario_text, str) or not scenario_text.strip():
        raise ScenarioValidationError("scenario is required")
    index_elastic = bool(payload.get("index_elastic"))
    return {
        "scenario_text": scenario_text,
        "index_elastic": index_elastic,
        "include_raw_query": bool(payload.get("include_raw_query")),
        "setup_kibana_data_views": bool(payload.get("setup_kibana_data_views", index_elastic)),
        "elasticsearch_url": str(payload.get("elasticsearch_url") or DEFAULT_ELASTICSEARCH_URL),
        "kibana_url": str(payload.get("kibana_url") or DEFAULT_KIBANA_URL),
    }


def _artifact_links(run_id: str) -> list[dict[str, str]]:
    return [
        {"name": name, "href": f"/runs/{run_id}/{name}"}
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


def _export_to_elastic(result: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    scenario = result["scenario"]
    payload: dict[str, Any] = {
        "status": "ok",
        "elasticsearch_url": request["elasticsearch_url"],
        "kibana_url": request["kibana_url"],
        "time_range": {
            "start": _iso_utc(scenario.time_range.start),
            "end": _iso_utc(scenario.time_range.end),
        },
    }
    try:
        export_result = index_run(
            run_id=result["run_id"],
            scenario=scenario,
            events=result["events"],
            report=result["report"],
            validation=result["validation"],
            run_dir=result["run_dir"],
            elasticsearch_url=request["elasticsearch_url"],
            include_raw_query=request["include_raw_query"],
        )
    except ElasticExportError as exc:
        return {**payload, "status": "error", "error": str(exc)}

    payload.update(
        {
            "indexed": export_result["indexed"],
            "indices": export_result["indices"],
            "include_raw_query": request["include_raw_query"],
        }
    )
    if request["setup_kibana_data_views"]:
        try:
            payload["data_views"] = setup_data_views(request["kibana_url"])
        except ElasticExportError as exc:
            payload["status"] = "warning"
            payload["warning"] = f"Indexed data, but Kibana data-view setup failed: {exc}"
    return payload


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
            body = self.rfile.read(length).decode("utf-8")
            try:
                request = _parse_run_request(self, body)
                result = run_scenario_text(request["scenario_text"], output_root=root)
            except ScenarioValidationError as exc:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            elastic_export = _export_to_elastic(result, request) if request["index_elastic"] else None
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "run_id": result["run_id"],
                    "dashboard": result["dashboard"],
                    "validation": result["validation"],
                    "artifacts": _artifact_links(result["run_id"]),
                    "elastic_export": elastic_export,
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
