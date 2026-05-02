import json
from pathlib import Path

from workload_intelligence.ingest.raw_event import raw_event_from_dict
from workload_intelligence.normalize.dispatcher import normalize_event
from workload_intelligence.normalize.postgres_normalizer import normalize_sql_template, sql_features
from workload_intelligence.primitives.extractor import extract_primitives


ROOT = Path(__file__).resolve().parents[1]


def _load(example: str):
    return json.loads((ROOT / "examples" / example).read_text(encoding="utf-8"))


def _first_primitive_event(example: str):
    raw = _load(example)[0]
    return extract_primitives(normalize_event(raw_event_from_dict(raw)))


def test_postgres_lookup_primitives_match_spec_case():
    primitive_event = _first_primitive_event("postgres_lookup_events.json")
    signals = primitive_event["primitive_signals"]

    assert signals["key_lookup"]["matched"] is True
    assert signals["key_lookup"]["signal_weight"] >= 0.7
    assert signals["aggregation"]["matched"] is False
    assert signals["scan"]["matched"] is False


def test_postgres_group_by_scan_primitives_match_spec_case():
    primitive_event = _first_primitive_event("postgres_analytics_events.json")
    signals = primitive_event["primitive_signals"]

    assert signals["aggregation"]["matched"] is True
    assert signals["aggregation"]["signal_weight"] >= 0.8
    assert signals["scan"]["matched"] is True
    assert signals["scan"]["signal_weight"] >= 0.6
    assert signals["range_lookup"]["matched"] is True
    assert signals["range_lookup"]["signal_weight"] >= 0.5
    assert signals["time_series"]["matched"] is True
    assert signals["time_series"]["signal_weight"] >= 0.6
    assert signals["multi_filter"]["matched"] is True


def test_postgres_sql_literals_do_not_change_template_id():
    first, second = _load("postgres_analytics_events.json")

    first_normalized = normalize_event(raw_event_from_dict(first))
    second_normalized = normalize_event(raw_event_from_dict(second))

    assert first_normalized["template_id"] == second_normalized["template_id"]
    assert "'2026-04-01" not in first_normalized["operation"]["normalized_query"]["sql"]


def test_postgres_text_search_primitives_match_spec_case():
    primitive_event = _first_primitive_event("postgres_text_search_events.json")
    signals = primitive_event["primitive_signals"]

    assert signals["text_search"]["matched"] is True
    assert signals["text_search"]["signal_weight"] >= 0.8
    assert signals["sort_paginate"]["matched"] is True
    assert signals["aggregation"]["matched"] is False


def test_postgres_full_text_search_features_are_detected():
    normalized = normalize_sql_template(
        "SELECT id FROM docs WHERE to_tsvector('english', body) @@ plainto_tsquery('english', 'refund')"
    )
    features = sql_features(normalized)

    assert features["has_full_text_search"] is True
    assert features["has_text_search"] is True
