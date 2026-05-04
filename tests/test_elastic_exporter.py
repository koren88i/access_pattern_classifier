import json
import sys
from pathlib import Path

import pytest

from workload_intelligence.exporters import elastic
from workload_intelligence.exporters import kibana
from workload_intelligence.pipeline import process_event_report
from workload_intelligence.simulator import cli as simulator_cli
from workload_intelligence.simulator.generators import generate_events
from workload_intelligence.simulator.scenario import load_scenario
from workload_intelligence.simulator.validation import validate_report


ROOT = Path(__file__).resolve().parents[1]


def _load_example(name: str):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def _export_fixture():
    scenario = load_scenario(ROOT / "scenarios" / "postgres_text_search.yaml")
    events = generate_events(scenario)
    report = process_event_report(events, include_primitive_events=True, include_normalized_events=True)
    validation = validate_report(scenario, report)
    return scenario, events, report, validation


def _analytics_export_fixture():
    scenario = load_scenario(ROOT / "scenarios" / "postgres_analytics.yaml")
    events = generate_events(scenario)
    report = process_event_report(events, include_primitive_events=True, include_normalized_events=True)
    validation = validate_report(scenario, report)
    return scenario, events, report, validation


def test_export_actions_create_expected_indices_and_stable_ids(tmp_path):
    scenario, events, report, validation = _export_fixture()

    actions = elastic.export_actions(
        run_id="run-1",
        scenario=scenario,
        events=events,
        report=report,
        validation=validation,
        run_dir=tmp_path,
        generated_at="2026-05-01T00:00:00Z",
    )

    indices = {action["_index"] for action in actions}
    assert set(elastic.EXPORT_INDICES).issubset(indices)
    assert actions[0]["_index"] == elastic.INDEX_SIM_RUNS
    assert actions[0]["_id"] == "run-1"
    assert all(action["_id"] for action in actions)


def test_raw_query_is_omitted_by_default_and_included_by_flag(tmp_path):
    scenario, events, report, validation = _export_fixture()

    default_actions = elastic.export_actions("run-1", scenario, events, report, validation, tmp_path)
    debug_actions = elastic.export_actions(
        "run-1",
        scenario,
        events,
        report,
        validation,
        tmp_path,
        include_raw_query=True,
    )

    default_event = next(action for action in default_actions if action["_index"] == elastic.INDEX_PRIMITIVE_EVENTS)
    debug_event = next(action for action in debug_actions if action["_index"] == elastic.INDEX_PRIMITIVE_EVENTS)

    assert "raw_query_text" not in default_event["_source"]
    assert "raw_query_body" not in default_event["_source"]
    assert "raw_query_text" in debug_event["_source"]


def test_index_templates_include_core_mappings():
    templates = elastic.index_templates()

    primitive_event = templates[elastic.INDEX_PRIMITIVE_EVENTS]
    primitive_signal = templates[elastic.INDEX_PRIMITIVE_SIGNALS]

    assert primitive_event["timestamp"]["type"] == "date"
    assert primitive_event["run_id"]["type"] == "keyword"
    assert primitive_event["normalized_query"]["type"] == "flattened"
    assert primitive_event["normalized_query_text"]["type"] == "text"
    assert primitive_event["normalized_query_command"]["type"] == "keyword"
    assert primitive_event["primitive_signals"]["type"] == "flattened"
    assert primitive_signal["primitive"]["type"] == "keyword"
    assert primitive_signal["database_or_index"]["type"] == "keyword"
    assert primitive_signal["signal_weight"]["type"] == "double"
    assert primitive_signal["rule_confidence"]["type"] == "double"
    assert templates[elastic.INDEX_LINEAGE_RECOMMENDATIONS]["recommendation_id"]["type"] == "keyword"
    assert templates[elastic.INDEX_LINEAGE_EVENTS]["event_id"]["type"] == "keyword"
    assert templates[elastic.INDEX_LINEAGE_TEMPLATES]["normalized_query_text"]["type"] == "text"
    assert templates[elastic.INDEX_LINEAGE_EVENTS]["normalized_query_text"]["type"] == "text"


def test_ensure_index_templates_installs_template_for_every_export_index():
    calls = []

    class FakeIndices:
        def put_index_template(self, **kwargs):
            calls.append(kwargs)

    class FakeClient:
        indices = FakeIndices()

    elastic.ensure_index_templates(FakeClient())

    templates = elastic.index_templates()
    assert [call["name"] for call in calls] == [
        f"{index_name}-template"
        for index_name in templates
    ]
    assert [call["index_patterns"] for call in calls] == [
        [index_name]
        for index_name in templates
    ]
    assert all(call["template"]["mappings"]["dynamic"] is True for call in calls)
    assert calls[0]["template"]["mappings"]["properties"] == templates[elastic.INDEX_SIM_RUNS]


def test_missing_elasticsearch_client_has_clear_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "elasticsearch", None)

    with pytest.raises(elastic.ElasticExportError, match="python -m pip install elasticsearch"):
        elastic._load_elasticsearch_client()


def test_simulator_cli_index_elastic_calls_exporter(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_index_run(**kwargs):
        calls.append(kwargs)
        return {"indexed": 3, "indices": ["workload-sim-runs"]}

    monkeypatch.setattr(simulator_cli, "index_run", fake_index_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_workload_simulator.py",
            str(ROOT / "scenarios" / "postgres_text_search.yaml"),
            "--output-dir",
            str(tmp_path),
            "--index-elastic",
            "--elasticsearch-url",
            "http://example.test:9200",
        ],
    )

    simulator_cli.main()

    assert calls
    assert calls[0]["elasticsearch_url"] == "http://example.test:9200"
    assert calls[0]["include_raw_query"] is False
    assert "Indexed 3 documents" in capsys.readouterr().out


def test_lineage_recommendation_backtrace_contains_threshold_math(tmp_path):
    scenario, events, report, validation = _analytics_export_fixture()

    actions = elastic.export_actions("run-analytics", scenario, events, report, validation, tmp_path)
    doc = next(
        action["_source"]
        for action in actions
        if action["_index"] == elastic.INDEX_LINEAGE_RECOMMENDATIONS
    )

    assert doc["matched_rule_id"] == "postgres_heavy_analytics"
    assert doc["recommendation_id"].startswith("rec-")
    assert doc["profile_id"].startswith("prof-")
    assert doc["aggregate_window_id"].startswith("agg-")
    condition_by_path = {condition["path"]: condition for condition in doc["rule_conditions"]}
    assert condition_by_path["primitive_profile.aggregation"]["observed_number"] >= 0.8
    assert condition_by_path["primitive_profile.aggregation"]["threshold_number"] == 0.5
    assert condition_by_path["primitive_profile.scan"]["passed"] is True
    assert doc["top_template_ids"]
    assert doc["sample_event_ids"]


def test_lineage_template_docs_include_raw_samples_only_when_requested(tmp_path):
    scenario, events, report, validation = _analytics_export_fixture()

    default_actions = elastic.export_actions("run-analytics", scenario, events, report, validation, tmp_path)
    debug_actions = elastic.export_actions(
        "run-analytics",
        scenario,
        events,
        report,
        validation,
        tmp_path,
        include_raw_query=True,
    )
    default_doc = next(
        action["_source"] for action in default_actions if action["_index"] == elastic.INDEX_LINEAGE_TEMPLATES
    )
    debug_doc = next(
        action["_source"] for action in debug_actions if action["_index"] == elastic.INDEX_LINEAGE_TEMPLATES
    )

    assert "raw_query_samples" not in default_doc
    assert "raw_query_text" not in default_doc
    assert default_doc["normalized_query_command"] == "SELECT"
    assert default_doc["normalized_query_text"].startswith("select customer_id")
    assert debug_doc["raw_query_samples"]
    assert "raw_query_text" in debug_doc
    assert "postgres_aggregation_group_by" in debug_doc["matched_rule_ids"]


def test_lineage_event_docs_link_forward_to_profile_and_recommendation(tmp_path):
    scenario, events, report, validation = _analytics_export_fixture()

    actions = elastic.export_actions(
        "run-analytics",
        scenario,
        events,
        report,
        validation,
        tmp_path,
        include_raw_query=True,
    )
    doc = next(action["_source"] for action in actions if action["_index"] == elastic.INDEX_LINEAGE_EVENTS)

    assert doc["aggregate_window_ids"]
    assert doc["profile_id"].startswith("prof-")
    assert doc["recommendation_ids"]
    assert doc["normalized_query_command"] == "SELECT"
    assert doc["normalized_query_text"].startswith("select customer_id")
    assert "raw_query_text" in doc
    primitives = {item["primitive"]: item for item in doc["matched_primitives"]}
    assert {"aggregation", "scan", "time_series"}.issubset(primitives)
    assert primitives["aggregation"]["signal_weight"] >= 0.8
    assert primitives["aggregation"]["rule_confidence"] >= 0.8


def test_lineage_links_use_full_profile_scope(tmp_path):
    scenario = load_scenario(ROOT / "scenarios" / "elastic_analytics.yaml")
    dashboard_events = _load_example("elastic_dashboard_events.json")
    text_search_events = _load_example("elastic_text_search.json")
    text_search_events[0]["identity"]["system_id"] = "fraud-service"
    text_search_events[0]["identity"]["customer_id"] = "beta"
    events = dashboard_events + text_search_events
    report = process_event_report(events, include_primitive_events=True, include_normalized_events=True)

    actions = elastic.export_actions("run-mixed", scenario, events, report, {}, tmp_path)
    profiles_by_scope = {
        (
            profile["scope"]["customer_id"],
            profile["scope"]["database_or_index"],
        ): profile
        for profile in report["profiles"]
    }
    acme_profile = profiles_by_scope[("acme", "transactions")]
    beta_profile = profiles_by_scope[("beta", "products")]
    lineage_events = {
        action["_source"]["event_id"]: action["_source"]
        for action in actions
        if action["_index"] == elastic.INDEX_LINEAGE_EVENTS
    }

    assert lineage_events["evt-elastic-dashboard-1"]["profile_id"] == acme_profile["profile_id"]
    assert lineage_events["evt-elastic-text-1"]["profile_id"] == beta_profile["profile_id"]
    assert lineage_events["evt-elastic-text-1"]["customer_id"] == "beta"
    assert lineage_events["evt-elastic-text-1"]["database_or_index"] == "products"

    acme_recommendation = next(
        action["_source"]
        for action in actions
        if action["_index"] == elastic.INDEX_LINEAGE_RECOMMENDATIONS
        and action["_source"]["profile_id"] == acme_profile["profile_id"]
    )
    beta_template = next(
        action["_source"]
        for action in actions
        if action["_index"] == elastic.INDEX_LINEAGE_TEMPLATES
        and action["_source"]["profile_id"] == beta_profile["profile_id"]
    )

    assert "evt-elastic-text-1" not in acme_recommendation["sample_event_ids"]
    assert beta_template["sample_event_ids"] == ["evt-elastic-text-1"]


def test_lineage_validation_doc_connects_expected_observed_and_recommendations(tmp_path):
    scenario, events, report, validation = _analytics_export_fixture()

    actions = elastic.export_actions("run-analytics", scenario, events, report, validation, tmp_path)
    doc = next(action["_source"] for action in actions if action["_index"] == elastic.INDEX_LINEAGE_VALIDATION)

    assert doc["validation_status"] == "ok"
    assert doc["expected_primitive_share"]["aggregation"] == 1.0
    assert doc["observed_primitive_share"]["aggregation"] == 1.0
    assert doc["observed_primitive_share"]["range_lookup"] == 1.0
    assert doc["observed_primitive_profile"]["range_lookup"] == pytest.approx(0.55)
    assert doc["observed_primitive_profile"]["aggregation"] >= 0.8
    assert doc["recommendation_ids"]


def test_kibana_data_views_include_lineage_indices():
    assert elastic.INDEX_LINEAGE_RECOMMENDATIONS in kibana.DATA_VIEWS
    assert elastic.INDEX_LINEAGE_TEMPLATES in kibana.DATA_VIEWS
    assert elastic.INDEX_LINEAGE_EVENTS in kibana.DATA_VIEWS
    assert elastic.INDEX_LINEAGE_VALIDATION in kibana.DATA_VIEWS


def test_kibana_lineage_dashboard_saved_object_payload(monkeypatch):
    calls = []

    def fake_setup_saved_searches(kibana_url):
        assert kibana_url == "http://kibana.test"
        return list(kibana.SAVED_SEARCHES)

    def fake_data_view_ids(kibana_url):
        assert kibana_url == "http://kibana.test"
        return {title: f"id-{index}" for index, title in enumerate(kibana.DATA_VIEWS)}

    def fake_post_saved_object(kibana_url, object_type, object_id, attributes, references):
        calls.append(
            {
                "kibana_url": kibana_url,
                "object_type": object_type,
                "object_id": object_id,
                "attributes": attributes,
                "references": references,
            }
        )
        return {}

    monkeypatch.setattr(kibana, "setup_saved_searches", fake_setup_saved_searches)
    monkeypatch.setattr(kibana, "_data_view_ids", fake_data_view_ids)
    monkeypatch.setattr(kibana, "_post_saved_object", fake_post_saved_object)

    result = kibana.setup_lineage_dashboard("http://kibana.test")

    assert result["dashboard_id"] == kibana.DASHBOARD_ID
    assert len(calls) == 1
    call = calls[0]
    assert call["object_type"] == "dashboard"
    assert call["object_id"] == kibana.DASHBOARD_ID
    panels = json.loads(call["attributes"]["panelsJSON"])
    assert len(panels) == 5
    assert panels[0]["type"] == "search"
    assert call["references"][0]["id"] == "workload-lineage-event-lookup"
    assert len(call["references"]) == 8
    controls = call["attributes"]["controlGroupInput"]
    control_panels = json.loads(controls["panelsJSON"])
    assert control_panels["lineage-run-selector"]["explicitInput"]["fieldName"] == "run_id"
    assert control_panels["lineage-event-id-lookup"]["explicitInput"]["fieldName"] == "event_id"
    assert control_panels["lineage-template-id-selector"]["explicitInput"]["fieldName"] == "template_id"
    assert all(ref["type"] == "index-pattern" for ref in call["references"][-3:])


def test_kibana_saved_searches_reference_data_views(monkeypatch):
    calls = []

    def fake_setup_data_views(kibana_url):
        assert kibana_url == "http://kibana.test"
        return []

    def fake_data_view_ids(kibana_url):
        return {title: f"id-{index}" for index, title in enumerate(kibana.DATA_VIEWS)}

    def fake_post_saved_object(kibana_url, object_type, object_id, attributes, references):
        calls.append(
            {
                "object_type": object_type,
                "object_id": object_id,
                "attributes": attributes,
                "references": references,
            }
        )
        return {}

    monkeypatch.setattr(kibana, "setup_data_views", fake_setup_data_views)
    monkeypatch.setattr(kibana, "_data_view_ids", fake_data_view_ids)
    monkeypatch.setattr(kibana, "_post_saved_object", fake_post_saved_object)

    created = kibana.setup_saved_searches("http://kibana.test")

    assert created == list(kibana.SAVED_SEARCHES)
    assert len(calls) == len(kibana.SAVED_SEARCHES)
    assert all(call["object_type"] == "search" for call in calls)
    assert all(call["references"][0]["type"] == "index-pattern" for call in calls)

    by_id = {call["object_id"]: call for call in calls}
    lookup_columns = by_id["workload-lineage-event-lookup"]["attributes"]["columns"]
    template_columns = by_id["workload-lineage-template-evidence"]["attributes"]["columns"]
    event_columns = by_id["workload-lineage-event-forward-trace"]["attributes"]["columns"]
    validation_columns = by_id["workload-lineage-validation-check"]["attributes"]["columns"]
    assert "event_id" in lookup_columns
    assert "normalized_query_text" in lookup_columns
    assert "raw_query_text" in lookup_columns
    assert "recommendation_ids" in lookup_columns
    assert "normalized_query_text" in template_columns
    assert "normalized_query.sql" not in template_columns
    assert "normalized_query_text" in event_columns
    assert "observed_primitive_share" in validation_columns
    assert "observed_primitive_profile" in validation_columns
