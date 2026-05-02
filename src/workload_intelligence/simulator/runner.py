from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from workload_intelligence.pipeline import process_event_report
from workload_intelligence.simulator.generators import generate_events
from workload_intelligence.simulator.scenario import Scenario, load_scenario, scenario_from_text
from workload_intelligence.simulator.validation import validate_report
from workload_intelligence.specs import REPO_ROOT
from workload_intelligence.ui.dashboard import (
    render_dashboard_rows,
    render_platform_market_analysis,
    render_primitive_weight_comparison,
    render_top_templates_by_system,
)


DEFAULT_OUTPUT_ROOT = REPO_ROOT / "simulator_runs"


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return safe.strip("_") or "scenario"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_artifacts(
    scenario: Scenario,
    events: list[dict[str, Any]],
    output_root: Path,
    run_id: str | None = None,
) -> dict[str, Any]:
    report = process_event_report(
        events,
        include_primitive_events=True,
        include_normalized_events=True,
    )
    validation = validate_report(scenario, report)
    if run_id is None:
        run_id = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')}_{_safe_name(scenario.name)}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    (run_dir / "scenario.yaml").write_text(
        yaml.safe_dump(scenario.raw_payload, sort_keys=False),
        encoding="utf-8",
    )
    _write_json(run_dir / "events.json", events)
    _write_json(run_dir / "profiles.json", report["profiles"])
    _write_json(run_dir / "report.json", report)
    _write_json(run_dir / "validation.json", validation)

    dashboard = render_dashboard_rows(report["profiles"])
    platform = render_platform_market_analysis(report["aggregation_views"]["platform"])
    templates = render_top_templates_by_system(report["aggregation_views"]["system"])
    weights = render_primitive_weight_comparison(report["aggregation_views"]["system"])
    (run_dir / "dashboard.txt").write_text(dashboard, encoding="utf-8")
    (run_dir / "platform.txt").write_text(platform, encoding="utf-8")
    (run_dir / "templates.txt").write_text(templates, encoding="utf-8")
    (run_dir / "primitive-weights.txt").write_text(weights, encoding="utf-8")

    return {
        "run_id": run_dir.name,
        "run_dir": run_dir,
        "scenario": scenario,
        "events": events,
        "report": report,
        "validation": validation,
        "dashboard": dashboard,
    }


def run_scenario(
    scenario_path: Path,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    scenario = load_scenario(scenario_path)
    events = generate_events(scenario)
    return _write_artifacts(scenario, events, output_root, run_id=run_id)


def run_scenario_text(
    scenario_text: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
) -> dict[str, Any]:
    scenario = scenario_from_text(scenario_text)
    events = generate_events(scenario)
    return _write_artifacts(scenario, events, output_root, run_id=run_id)
