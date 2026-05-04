import json
from pathlib import Path

from workload_intelligence.pipeline import process_events
from workload_intelligence.ui.dashboard import render_dashboard_rows


ROOT = Path(__file__).resolve().parents[1]


def _load(example: str):
    return json.loads((ROOT / "examples" / example).read_text(encoding="utf-8"))


def test_elasticsearch_dashboard_events_produce_analytical_serving_profile():
    profiles = process_events(_load("elastic_dashboard_events.json"))

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile["scope"]["system_id"] == "fraud-service"
    assert profile["scope"]["customer_id"] == "acme"
    assert profile["scope"]["database_or_index"] == "transactions"
    assert profile["dominant_patterns"][0]["pattern"] == "analytical_serving"
    assert profile["access_pattern_scores"]["analytical_serving"] > 0.6
    assert profile["volume"]["unique_template_count"] == 1
    assert profile["volume"]["top_templates_coverage"] == 1.0
    assert profile["recommendations"][0]["matched_rule_id"] == "elastic_as_analytical_serving"
    assert "analytical serving" in profile["recommendations"][0]["recommendation"]


def test_dashboard_renderer_outputs_one_debug_row():
    profiles = process_events(_load("elastic_dashboard_events.json"))
    rendered = render_dashboard_rows(profiles)

    assert "Customer" in rendered
    assert "Database/Index" in rendered
    assert "fraud-service" in rendered
    assert "acme" in rendered
    assert "transactions" in rendered
    assert "analytical_serving" in rendered
    assert "Evaluate analytical serving layer" in rendered


def test_redis_get_setex_traffic_classifies_as_cache():
    profile = process_events(_load("redis_cache_events.json"))[0]

    assert profile["scope"]["customer_id"] == "unknown_customer"
    assert profile["scope"]["database_or_index"] == "unknown_database_or_index"
    assert profile["dominant_patterns"][0]["pattern"] == "cache"
    assert profile["access_pattern_scores"]["cache"] > 0.55
    assert profile["recommendations"][0]["type"] == "no_action"


def test_redis_get_set_without_ttl_requests_review():
    profile = process_events(_load("redis_state_events.json"))[0]

    assert profile["primitive_profile"]["ttl_or_expire_usage"] == 0.0
    assert profile["recommendations"][0]["matched_rule_id"] == "redis_possible_durable_state"
    assert profile["recommendations"][0]["type"] == "review_required"


def test_postgres_scan_group_by_requests_analytics_review():
    profile = process_events(_load("postgres_analytics_events.json"))[0]

    assert profile["scope"]["system_id"] == "reporting-api"
    assert profile["scope"]["customer_id"] == "acme"
    assert profile["scope"]["database_or_index"] == "orders"
    assert profile["dominant_patterns"][0]["pattern"] == "analytical_serving"
    assert profile["primitive_profile"]["aggregation"] >= 0.8
    assert profile["primitive_profile"]["scan"] >= 0.6
    assert profile["recommendations"][0]["matched_rule_id"] == "postgres_heavy_analytics"
    assert profile["recommendations"][0]["type"] == "technology_mismatch_candidate"


def test_postgres_lookup_has_no_architecture_review_rule():
    profile = process_events(_load("postgres_lookup_events.json"))[0]

    assert profile["dominant_patterns"][0]["pattern"] == "oltp"
    assert profile["recommendations"][0]["matched_rule_id"] == "default_no_action"


def test_postgres_text_search_requests_search_review():
    profile = process_events(_load("postgres_text_search_events.json"))[0]

    assert profile["scope"]["system_id"] == "catalog-api"
    assert profile["scope"]["customer_id"] == "acme"
    assert profile["scope"]["database_or_index"] == "catalog_items"
    assert profile["dominant_patterns"][0]["pattern"] == "search_text"
    assert profile["primitive_profile"]["text_search"] >= 0.8
    assert profile["recommendations"][0]["matched_rule_id"] == "postgres_text_search_review"
    assert profile["recommendations"][0]["type"] == "review_required"


def test_profiles_split_same_system_platform_by_customer_and_database():
    dashboard_events = _load("elastic_dashboard_events.json")
    text_search_events = _load("elastic_text_search.json")
    text_search_events[0]["identity"]["system_id"] = "fraud-service"
    text_search_events[0]["identity"]["customer_id"] = "beta"

    profiles = process_events(dashboard_events + text_search_events)
    by_scope = {
        (
            profile["scope"]["system_id"],
            profile["scope"]["customer_id"],
            profile["scope"]["platform"],
            profile["scope"]["database_or_index"],
        ): profile
        for profile in profiles
    }

    assert set(by_scope) == {
        ("fraud-service", "acme", "elasticsearch", "transactions"),
        ("fraud-service", "beta", "elasticsearch", "products"),
    }

    analytics_profile = by_scope[("fraud-service", "acme", "elasticsearch", "transactions")]
    search_profile = by_scope[("fraud-service", "beta", "elasticsearch", "products")]

    assert analytics_profile["recommendations"][0]["matched_rule_id"] == "elastic_as_analytical_serving"
    assert search_profile["recommendations"][0]["matched_rule_id"] == "default_no_action"
    assert analytics_profile["volume"]["request_count"] == 2
    assert search_profile["volume"]["request_count"] == 1
    assert len(analytics_profile["evidence"]["top_templates"]) == 1
    assert len(search_profile["evidence"]["top_templates"]) == 1
