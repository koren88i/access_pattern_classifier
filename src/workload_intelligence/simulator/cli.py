from __future__ import annotations

import argparse
from pathlib import Path

from workload_intelligence.exporters.elastic import (
    DEFAULT_ELASTICSEARCH_URL,
    ElasticExportError,
    index_run,
)
from workload_intelligence.exporters.kibana import DEFAULT_KIBANA_URL, setup_data_views, setup_lineage_dashboard
from workload_intelligence.simulator.runner import DEFAULT_OUTPUT_ROOT, run_scenario
from workload_intelligence.simulator.web import serve_ui


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic workload telemetry and run dashboards.")
    parser.add_argument("scenario", nargs="?", type=Path, help="Scenario YAML to run.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Directory for simulator run artifacts.")
    parser.add_argument("--ui", action="store_true", help="Start the local scenario editor UI.")
    parser.add_argument("--host", default="127.0.0.1", help="UI host.")
    parser.add_argument("--port", type=int, default=8765, help="UI port.")
    parser.add_argument("--index-elastic", action="store_true", help="Index this simulator run into Elasticsearch.")
    parser.add_argument(
        "--elasticsearch-url",
        default=DEFAULT_ELASTICSEARCH_URL,
        help="Elasticsearch URL for --index-elastic.",
    )
    parser.add_argument(
        "--include-raw-query",
        action="store_true",
        help="Include raw query text/body in Elasticsearch documents.",
    )
    parser.add_argument(
        "--setup-kibana-data-views",
        action="store_true",
        help="Create Kibana data views for workload indices.",
    )
    parser.add_argument(
        "--setup-kibana-dashboard",
        action="store_true",
        help="Create the Kibana lineage dashboard and saved searches.",
    )
    parser.add_argument("--kibana-url", default=DEFAULT_KIBANA_URL, help="Kibana URL for data-view setup.")
    args = parser.parse_args()

    if args.ui:
        serve_ui(host=args.host, port=args.port, output_root=args.output_dir)
        return
    if args.scenario is None:
        parser.error("provide a scenario YAML file or use --ui")

    result = run_scenario(args.scenario, output_root=args.output_dir)
    if args.index_elastic:
        try:
            export_result = index_run(
                run_id=result["run_id"],
                scenario=result["scenario"],
                events=result["events"],
                report=result["report"],
                validation=result["validation"],
                run_dir=result["run_dir"],
                elasticsearch_url=args.elasticsearch_url,
                include_raw_query=args.include_raw_query,
            )
        except ElasticExportError as exc:
            raise SystemExit(f"Elasticsearch export failed: {exc}") from exc
        print(f"Indexed {export_result['indexed']} documents into {', '.join(export_result['indices'])}")
    if args.setup_kibana_data_views:
        try:
            created = setup_data_views(args.kibana_url)
        except ElasticExportError as exc:
            raise SystemExit(f"Kibana setup failed: {exc}") from exc
        print(f"Configured Kibana data views: {', '.join(created)}")
    if args.setup_kibana_dashboard:
        try:
            dashboard = setup_lineage_dashboard(args.kibana_url)
        except ElasticExportError as exc:
            raise SystemExit(f"Kibana dashboard setup failed: {exc}") from exc
        print(f"Configured Kibana dashboard: {dashboard['title']} ({dashboard['url']})")
    print(f"Run artifacts: {result['run_dir']}")
    print()
    print(result["dashboard"])
