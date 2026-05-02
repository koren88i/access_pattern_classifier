import json
from pathlib import Path

import pytest

from workload_intelligence.pipeline import primitive_events_from_raw, process_events
from workload_intelligence.simulator.capabilities import capability_payload
from workload_intelligence.simulator.generators import generate_events
from workload_intelligence.simulator.matcher_source import matcher_source_for
from workload_intelligence.simulator.runner import run_scenario
from workload_intelligence.simulator.scenario import ScenarioValidationError, load_scenario, scenario_from_text
from workload_intelligence.simulator.sampling import sample_distribution, sample_response_metadata
from workload_intelligence.simulator.web import HTML


ROOT = Path(__file__).resolve().parents[1]


def _scenario(name: str):
    return load_scenario(ROOT / "scenarios" / name)


def test_scenario_validation_rejects_unsupported_primitive():
    with pytest.raises(ScenarioValidationError, match="unsupported primitives"):
        scenario_from_text(
            """
name: invalid
seed: 1
target:
  platform: redis
  system_id: demo
  customer_id: acme
  database_or_index: cache
time_range:
  start: "2026-04-30T00:00:00Z"
  end: "2026-05-01T00:00:00Z"
events: 10
responses:
  latency_ms: { distribution: fixed, value: 1 }
  response_bytes: { distribution: fixed, value: 100 }
  result_count: { distribution: fixed, value: 1 }
query_shapes:
  - name: bad
    share: 100
    primitives: [aggregation]
"""
        )


def test_scenario_validation_rejects_bad_share_total():
    text = (ROOT / "scenarios" / "postgres_text_search.yaml").read_text(encoding="utf-8")
    with pytest.raises(ScenarioValidationError, match="sum to 100"):
        scenario_from_text(text.replace("share: 100", "share: 80"))


def test_generation_is_deterministic_for_same_seed():
    scenario = _scenario("postgres_text_search.yaml")

    assert generate_events(scenario) == generate_events(scenario)


def test_distribution_sampling_respects_bounds():
    import random

    rng = random.Random(42)
    values = [
        sample_distribution({"distribution": "normal", "mean": 80, "stddev": 100, "min": 20, "max": 90}, rng)
        for _ in range(50)
    ]

    assert min(values) >= 20
    assert max(values) <= 90


def test_generated_postgres_text_search_triggers_real_primitive_extraction():
    events = generate_events(_scenario("postgres_text_search.yaml"))
    primitive_events = primitive_events_from_raw(events[:1])
    signals = primitive_events[0]["primitive_signals"]

    assert signals["text_search"]["matched"] is True
    assert signals["sort_paginate"]["matched"] is True


def test_large_result_is_not_a_query_shape_primitive():
    with pytest.raises(ScenarioValidationError, match="unsupported primitives"):
        scenario_from_text(
            """
name: invalid_large_result_shape
seed: 1
target:
  platform: postgres
  system_id: demo
  customer_id: acme
  database_or_index: orders
time_range:
  start: "2026-04-30T00:00:00Z"
  end: "2026-05-01T00:00:00Z"
events: 10
responses:
  latency_ms: { distribution: fixed, value: 1 }
  response_bytes: { distribution: fixed, value: 100 }
  result_count: { distribution: fixed, value: 1 }
query_shapes:
  - name: bad
    share: 100
    primitives: [large_result]
"""
        )


def test_response_metadata_is_not_secretly_floored_by_query_primitives():
    import random

    scenario = scenario_from_text(
        """
name: scan_without_large_response
seed: 1
target:
  platform: postgres
  system_id: demo
  customer_id: acme
  database_or_index: orders
time_range:
  start: "2026-04-30T00:00:00Z"
  end: "2026-05-01T00:00:00Z"
events: 1
responses:
  latency_ms: { distribution: fixed, value: 1 }
  response_bytes: { distribution: fixed, value: 100 }
  result_count: { distribution: fixed, value: 1 }
query_shapes:
  - name: scan_shape
    share: 100
    primitives: [scan]
"""
    )

    response = sample_response_metadata(scenario, scenario.query_shapes[0], random.Random(7))

    assert response["result_count"] == 1
    assert response["response_bytes"] == 100


def test_simulator_run_writes_artifacts_and_validation(tmp_path):
    result = run_scenario(ROOT / "scenarios" / "postgres_text_search.yaml", output_root=tmp_path, run_id="run-1")
    run_dir = tmp_path / "run-1"

    assert result["validation"]["status"] == "ok"
    assert (run_dir / "events.json").exists()
    assert (run_dir / "report.json").exists()
    assert (run_dir / "dashboard.txt").exists()
    assert (run_dir / "validation.json").exists()
    assert "catalog-api" in (run_dir / "dashboard.txt").read_text(encoding="utf-8")

    events = json.loads((run_dir / "events.json").read_text(encoding="utf-8"))
    assert len(events) == 100


def test_capability_payload_marks_unsupported_primitives_for_ui():
    payload = capability_payload()
    redis_primitives = {
        item["name"]: item for item in payload["platforms"]["redis"]["primitives"]
    }

    assert redis_primitives["key_lookup"]["supported"] is True
    assert redis_primitives["key_lookup"]["description"]
    assert redis_primitives["aggregation"]["supported"] is False
    assert redis_primitives["aggregation"]["reason"]
    assert redis_primitives["aggregation"]["description"]


def test_capability_payload_keeps_response_derived_primitives_out_of_query_picker():
    payload = capability_payload()

    for platform in ("postgres", "elasticsearch", "redis"):
        picker_names = {
            item["name"]
            for item in payload["platforms"][platform]["primitives"]
        }
        response_signal_names = {
            item["name"]
            for item in payload["platforms"][platform]["response_derived_primitives"]
        }

        assert "large_result" not in picker_names
        assert "low_latency_sensitive" not in picker_names
        assert "large_result" in response_signal_names
        assert "low_latency_sensitive" in response_signal_names
        assert all(
            item["description"]
            for item in payload["platforms"][platform]["response_derived_primitives"]
        )


def test_capability_payload_exposes_response_metadata_controls():
    payload = capability_payload()
    metadata = payload["response_metadata"]
    distributions = {item["name"]: item for item in metadata["distributions"]}

    assert [metric["name"] for metric in metadata["metrics"]] == [
        "latency_ms",
        "response_bytes",
        "result_count",
    ]
    assert list(distributions) == ["fixed", "uniform", "normal"]
    assert [field["name"] for field in distributions["fixed"]["fields"]] == ["value"]
    assert [field["name"] for field in distributions["uniform"]["fields"]] == ["min", "max"]
    assert [field["name"] for field in distributions["normal"]["fields"]] == [
        "mean",
        "stddev",
        "min",
        "max",
    ]
    for metric in metadata["metrics"]:
        default = metric["defaults"][metric["default_distribution"]]
        required_fields = [
            field["name"]
            for field in distributions[metric["default_distribution"]]["fields"]
        ]
        assert default["distribution"] == metric["default_distribution"]
        assert all(field in default for field in required_fields)


def test_simulator_ui_contains_response_metadata_builder():
    assert 'id="responseMetadata"' in HTML
    assert "renderResponseMetadataControls" in HTML
    assert "responseMetadataYamlLines" in HTML
    assert "This control edits one query shape" in HTML
    assert "Add more shapes directly in Scenario YAML" in HTML


def test_matcher_source_exposes_real_code_for_platform_primitive():
    source = matcher_source_for("postgres", "text_search", ["text_search", "sort_paginate"])

    assert source["platform"] == "postgres"
    assert source["primitive"] == "text_search"
    assert "ILIKE" in source["sample"]["generated_operation"]["raw_query"]
    assert source["sample"]["normalized_matcher_input"]["operation"]["sql_features"]["has_like_search"] is True
    assert source["sample"]["selected_primitive_signal"]["matched"] is True
    assert source["sample"]["selected_primitive_signal"]["rule_ids"] == ["postgres_text_search_predicate"]
    assert any(
        rule["id"] == "postgres_text_search_predicate"
        and "sql_has_any_feature" in rule["source"]
        for rule in source["rules"]
    )
    code_by_name = {block["name"]: block for block in source["code"]}

    assert "_postgres_operation" in code_by_name
    assert "text_search" in code_by_name["_postgres_operation"]["source"]
    assert "normalize_postgres_event" in code_by_name
    assert "sql_features" in code_by_name
    assert "rule_matches" in code_by_name
    assert "_condition_matches" in code_by_name
    assert "sql_has_any_feature" in code_by_name


def test_matcher_source_does_not_force_unchecked_primitive_into_sample():
    source = matcher_source_for("postgres", "text_search", ["sort_paginate"])

    assert source["inactive"] is True
    assert source["sample"] is None
    assert source["rules"] == []
    assert source["code"] == []


def test_matcher_source_highlights_relevant_fields_for_key_lookup():
    postgres = matcher_source_for("postgres", "key_lookup", ["key_lookup"])
    postgres_conditions = postgres["sample"]["relevant_matcher_fields"][0]["conditions"]

    assert postgres_conditions[0]["condition"] == "sql_command_in"
    assert postgres_conditions[0]["fields"][0]["path"] == "$.operation.sql_features.command"
    assert postgres_conditions[0]["fields"][0]["value"] == "SELECT"
    assert postgres_conditions[1]["condition"] == "sql_equality_field_matches"
    assert postgres_conditions[1]["fields"][0]["path"] == "$.operation.sql_features.equality_fields"
    assert postgres_conditions[1]["fields"][0]["value"] == ["id"]
    assert all(condition["matched"] for condition in postgres_conditions)

    redis = matcher_source_for("redis", "key_lookup", ["key_lookup"])
    redis_conditions = redis["sample"]["relevant_matcher_fields"][0]["conditions"]

    assert redis_conditions[0]["condition"] == "command_in"
    assert redis_conditions[0]["fields"][0]["path"] == "$.operation.command"
    assert redis_conditions[0]["fields"][0]["value"] == "GET"
    assert redis_conditions[0]["matched"] is True


def test_simulator_ui_contains_matcher_source_column():
    assert 'id="matcherSource"' in HTML
    assert "loadMatcherSource" in HTML
    assert "/api/matcher-source" in HTML
    assert "Tick a primitive flag" in HTML
    assert "activePrimitive" in HTML
    assert "payload.inactive" in HTML
    assert "stopPropagation" in HTML
    assert "Generated platform query" in HTML
    assert "Rule condition trace" in HTML
    assert "Normalized matcher input" in HTML
    assert "highlightedJson" in HTML
    assert "relevantMatcherPaths" in HTML
    assert "json-line" in HTML
    assert '" highlight"' in HTML
    assert "Primitive Rule" in HTML
    assert "Advanced source code" in HTML
    assert HTML.index('id="matcherSource"') < HTML.index('<label for="yaml">Scenario YAML</label>')


def test_acceptance_scenarios_drive_expected_recommendations():
    cases = [
        ("postgres_text_search.yaml", "catalog-api", "search_text", "postgres_text_search_review"),
        ("postgres_analytics.yaml", "reporting-api", "analytical_serving", "postgres_heavy_analytics"),
        ("redis_cache.yaml", "session-api", "cache", "redis_cache_no_action"),
        ("redis_durable_state.yaml", "job-state-api", "oltp", "redis_possible_durable_state"),
        ("elastic_analytics.yaml", "fraud-service", "analytical_serving", "elastic_as_analytical_serving"),
    ]

    for scenario_name, system_id, pattern, recommendation in cases:
        profile = process_events(generate_events(_scenario(scenario_name)))[0]
        assert profile["scope"]["system_id"] == system_id
        assert profile["dominant_patterns"][0]["pattern"] == pattern
        assert profile["recommendations"][0]["matched_rule_id"] == recommendation
