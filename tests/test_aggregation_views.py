import copy
import json
from pathlib import Path

import pytest

from workload_intelligence.aggregate.window_aggregator import aggregate_daily_by
from workload_intelligence.pipeline import process_event_report
from workload_intelligence.ui.dashboard import (
    render_platform_market_analysis,
    render_primitive_weight_comparison,
    render_top_templates_by_system,
)


ROOT = Path(__file__).resolve().parents[1]


def _load(example: str):
    return json.loads((ROOT / "examples" / example).read_text(encoding="utf-8"))


def _primitive_event(
    event_id: str,
    system_id: str,
    customer_id: str,
    template_id: str,
    latency_ms: float,
    response_bytes: float,
    aggregation: float,
    text_search: float,
    database_or_index: str | None = "events",
):
    event = {
        "event_id": event_id,
        "platform": "elasticsearch",
        "system_id": system_id,
        "customer_id": customer_id,
        "timestamp": "2026-04-30T09:00:00Z",
        "template_id": template_id,
        "latency_ms": latency_ms,
        "response_bytes": response_bytes,
        "result_count": 1,
        "primitive_signals": {
            "aggregation": {"signal_weight": aggregation},
            "text_search": {"signal_weight": text_search},
        },
    }
    if database_or_index is not None:
        event["database_or_index"] = database_or_index
    return event


def test_primitive_profiles_support_request_latency_response_and_entity_weights():
    events = [
        _primitive_event("evt-1", "catalog-search", "acme", "tpl-search", 10, 50, 0.0, 1.0),
        _primitive_event("evt-2", "catalog-search", "acme", "tpl-search", 10, 50, 0.0, 1.0),
        _primitive_event("evt-3", "fraud-service", "beta", "tpl-dashboard", 1000, 900, 1.0, 0.0),
    ]

    window = aggregate_daily_by(events, group_by=("platform",), view_name="platform")[0]
    profiles = window["primitive_profiles"]

    assert profiles["request_count"]["aggregation"] == pytest.approx(1 / 3)
    assert profiles["latency_cost"]["aggregation"] == pytest.approx(1000 / 1020)
    assert profiles["response_volume"]["aggregation"] == pytest.approx(900 / 1000)
    assert profiles["unique_customers"]["aggregation"] == pytest.approx(0.5)
    assert window["volume_metrics"]["unique_system_count"] == 2
    assert window["volume_metrics"]["unique_customer_count"] == 2


def test_aggregate_daily_by_uses_unknown_values_for_missing_dimensions():
    event = _primitive_event("evt-1", "", "", "tpl-search", 10, 50, 0.0, 1.0, None)
    del event["system_id"]

    window = aggregate_daily_by(
        [event],
        group_by=("system_id", "customer_id", "platform", "database_or_index"),
        view_name="profile",
    )[0]

    assert window["key"]["system_id"] == "unknown_system"
    assert window["key"]["customer_id"] == "unknown_customer"
    assert window["key"]["platform"] == "elasticsearch"
    assert window["key"]["database_or_index"] == "unknown_database_or_index"
    assert window["volume_metrics"]["unique_system_count"] == 0
    assert window["volume_metrics"]["unique_customer_count"] == 0


def test_report_includes_daily_profile_system_platform_customer_and_template_views():
    text_search_events = copy.deepcopy(_load("elastic_text_search.json"))
    text_search_events[0]["identity"]["customer_id"] = "beta"
    raw_events = _load("elastic_dashboard_events.json") + text_search_events

    report = process_event_report(raw_events)
    views = report["aggregation_views"]

    assert set(views) == {"profile", "system", "platform", "customer", "template"}
    assert len(views["profile"]) == 2
    assert len(views["system"]) == 2
    assert len(views["customer"]) == 2
    assert len(views["template"]) == 2

    profile_key = views["profile"][0]["key"]
    assert {"system_id", "customer_id", "platform", "database_or_index"} <= set(profile_key)

    platform_window = views["platform"][0]
    assert platform_window["key"]["platform"] == "elasticsearch"
    assert platform_window["volume_metrics"]["request_count"] == 3
    assert platform_window["volume_metrics"]["unique_system_count"] == 2
    assert platform_window["volume_metrics"]["unique_customer_count"] == 2


def test_dashboard_helpers_render_sprint_three_views():
    text_search_events = copy.deepcopy(_load("elastic_text_search.json"))
    text_search_events[0]["identity"]["customer_id"] = "beta"
    report = process_event_report(_load("elastic_dashboard_events.json") + text_search_events)

    platform = render_platform_market_analysis(report["aggregation_views"]["platform"])
    templates = render_top_templates_by_system(report["aggregation_views"]["system"])
    weights = render_primitive_weight_comparison(report["aggregation_views"]["platform"])

    assert "elasticsearch" in platform
    assert "fraud-service" in templates
    assert "request_count" in weights
    assert "latency_cost" in weights
