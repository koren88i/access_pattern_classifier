import json
from pathlib import Path

from workload_intelligence.ingest.raw_event import raw_event_from_dict
from workload_intelligence.normalize.dispatcher import normalize_event
from workload_intelligence.primitives.extractor import extract_primitives


ROOT = Path(__file__).resolve().parents[1]


def _first_primitive_event(example: str):
    raw = json.loads((ROOT / "examples" / example).read_text(encoding="utf-8"))[0]
    return extract_primitives(normalize_event(raw_event_from_dict(raw)))


def test_elasticsearch_dashboard_primitives_match_spec_case():
    primitive_event = _first_primitive_event("elastic_dashboard_events.json")
    signals = primitive_event["primitive_signals"]

    assert signals["aggregation"]["matched"] is True
    assert signals["aggregation"]["signal_weight"] >= 0.8
    assert signals["time_series"]["matched"] is True
    assert signals["time_series"]["signal_weight"] >= 0.6
    assert signals["key_lookup"]["matched"] is True
    assert signals["key_lookup"]["signal_weight"] >= 0.2
    assert signals["text_search"]["matched"] is False
    assert signals["aggregation"]["evidence"]


def test_elasticsearch_text_search_primitives_match_spec_case():
    primitive_event = _first_primitive_event("elastic_text_search.json")
    signals = primitive_event["primitive_signals"]

    assert signals["text_search"]["matched"] is True
    assert signals["text_search"]["signal_weight"] >= 0.8
    assert signals["aggregation"]["matched"] is False
