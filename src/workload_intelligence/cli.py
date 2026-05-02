from __future__ import annotations

import argparse
import json
from pathlib import Path

from workload_intelligence.pipeline import process_event_report, process_events
from workload_intelligence.ui.dashboard import (
    render_dashboard_rows,
    render_platform_market_analysis,
    render_primitive_weight_comparison,
    render_top_templates_by_system,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process synthetic workload telemetry.")
    parser.add_argument("events", type=Path, help="Path to a JSON file containing a list of raw events.")
    parser.add_argument("--json", action="store_true", help="Print workload profiles as JSON.")
    parser.add_argument("--report-json", action="store_true", help="Print profiles and aggregation views as JSON.")
    parser.add_argument(
        "--view",
        choices=("profiles", "platform", "templates", "primitive-weights"),
        default="profiles",
        help="Rendered dashboard view to print.",
    )
    args = parser.parse_args()

    raw_events = json.loads(args.events.read_text(encoding="utf-8"))
    if args.json:
        profiles = process_events(raw_events)
        print(json.dumps(profiles, indent=2, sort_keys=True))
    elif args.report_json:
        print(json.dumps(process_event_report(raw_events), indent=2, sort_keys=True))
    elif args.view == "platform":
        report = process_event_report(raw_events)
        print(render_platform_market_analysis(report["aggregation_views"]["platform"]))
    elif args.view == "templates":
        report = process_event_report(raw_events)
        print(render_top_templates_by_system(report["aggregation_views"]["system"]))
    elif args.view == "primitive-weights":
        report = process_event_report(raw_events)
        print(render_primitive_weight_comparison(report["aggregation_views"]["system"]))
    else:
        profiles = process_events(raw_events)
        print(render_dashboard_rows(profiles))


if __name__ == "__main__":
    main()
