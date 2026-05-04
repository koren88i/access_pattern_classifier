from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from workload_intelligence.aggregate.window_aggregator import MISSING_DIMENSION_VALUES
from workload_intelligence.exporters.elastic_constants import (
    INDEX_AGGREGATE_WINDOWS,
    INDEX_LINEAGE_EVENTS,
    INDEX_LINEAGE_RECOMMENDATIONS,
    INDEX_LINEAGE_TEMPLATES,
    INDEX_LINEAGE_VALIDATION,
    INDEX_PRIMITIVE_EVENTS,
    INDEX_PRIMITIVE_SIGNALS,
    INDEX_PROFILES,
    INDEX_RECOMMENDATIONS,
    INDEX_SIM_RUNS,
)


PROFILE_MATCH_DIMENSIONS = ("system_id", "customer_id", "platform", "database_or_index")
WINDOW_MATCH_DIMENSIONS = (*PROFILE_MATCH_DIMENSIONS, "template_id")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_id(*parts: Any) -> str:
    raw = "|".join(json.dumps(part, sort_keys=True, default=str) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _scope_tags(run_id: str, scenario: Any) -> dict[str, Any]:
    target = scenario.target
    return {
        "run_id": run_id,
        "scenario_name": scenario.name,
        "seed": scenario.seed,
        "system_id": target.system_id,
        "customer_id": target.customer_id,
        "platform": target.platform,
        "database_or_index": target.database_or_index,
    }


def _dimension_value(payload: dict[str, Any], dimension: str) -> str:
    value = payload.get(dimension)
    if value in (None, ""):
        return MISSING_DIMENSION_VALUES.get(dimension, f"unknown_{dimension}")
    return str(value)


def _event_scope_tags(event: dict[str, Any]) -> dict[str, Any]:
    return {
        dimension: _dimension_value(event, dimension)
        for dimension in PROFILE_MATCH_DIMENSIONS
    }


def _profile_scope_tags(profile: dict[str, Any]) -> dict[str, Any]:
    scope = profile.get("scope") or {}
    return {
        dimension: scope[dimension]
        for dimension in PROFILE_MATCH_DIMENSIONS
        if dimension in scope
    }


def _normalized_query_text(normalized_query: Any) -> str | None:
    if normalized_query is None:
        return None
    if isinstance(normalized_query, str):
        return normalized_query
    if isinstance(normalized_query, dict):
        sql = normalized_query.get("sql")
        if sql:
            return str(sql)
        command = normalized_query.get("command")
        key_pattern = normalized_query.get("key_pattern")
        if command and key_pattern:
            ttl_suffix = " ttl=true" if normalized_query.get("has_ttl") else ""
            return f"{command} {key_pattern}{ttl_suffix}"
    if isinstance(normalized_query, (dict, list)):
        return json.dumps(normalized_query, sort_keys=True, separators=(",", ":"))
    return str(normalized_query)


def _normalized_query_command(operation: dict[str, Any], normalized_query: Any) -> str | None:
    command = operation.get("command")
    if command:
        return str(command)
    if isinstance(normalized_query, dict) and normalized_query.get("command"):
        return str(normalized_query["command"])
    return None


def _query_payload(normalized_event: dict[str, Any], include_raw_query: bool) -> dict[str, Any]:
    operation = normalized_event.get("operation") or {}
    normalized_query = operation.get("normalized_query")
    payload = {
        "command": operation.get("command"),
        "endpoint": operation.get("endpoint"),
        "method": operation.get("method"),
        "normalized_query": normalized_query,
        "normalized_query_text": _normalized_query_text(normalized_query),
        "normalized_query_command": _normalized_query_command(operation, normalized_query),
    }
    if include_raw_query:
        raw_query = operation.get("raw_query")
        if isinstance(raw_query, (dict, list)):
            payload["raw_query_body"] = raw_query
        elif raw_query is not None:
            payload["raw_query_text"] = str(raw_query)
    return {key: value for key, value in payload.items() if value is not None}


def _primitive_event_doc(
    run_id: str,
    scenario: Any,
    primitive_event: dict[str, Any],
    normalized_event: dict[str, Any],
    include_raw_query: bool,
) -> dict[str, Any]:
    return {
        **_scope_tags(run_id, scenario),
        **_event_scope_tags(primitive_event),
        "event_id": primitive_event["event_id"],
        "timestamp": primitive_event["timestamp"],
        "template_id": primitive_event["template_id"],
        "database_or_index": primitive_event.get("database_or_index"),
        "latency_ms": primitive_event.get("latency_ms"),
        "response_bytes": primitive_event.get("response_bytes"),
        "result_count": primitive_event.get("result_count"),
        "primitive_signals": primitive_event.get("primitive_signals") or {},
        **_query_payload(normalized_event, include_raw_query),
    }


def _primitive_signal_docs(
    run_id: str,
    scenario: Any,
    primitive_event: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    tags = {**_scope_tags(run_id, scenario), **_event_scope_tags(primitive_event)}
    for primitive, signal in (primitive_event.get("primitive_signals") or {}).items():
        if not signal.get("matched"):
            continue
        yield {
            **tags,
            "event_id": primitive_event["event_id"],
            "timestamp": primitive_event["timestamp"],
            "template_id": primitive_event["template_id"],
            "primitive": primitive,
            "signal_weight": signal.get("signal_weight", 0.0),
            "rule_confidence": signal.get("rule_confidence", 0.0),
            "evidence": signal.get("evidence") or [],
            "rule_ids": signal.get("rule_ids") or [],
        }


def _aggregate_window_doc(run_id: str, scenario: Any, view_name: str, window: dict[str, Any]) -> dict[str, Any]:
    tags = _scope_tags(run_id, scenario)
    key = window.get("key") or {}
    return {
        **tags,
        "aggregate_window_id": window.get("aggregate_window_id"),
        "aggregation_view": view_name,
        "window_start": key.get("window_start"),
        "window_end": key.get("window_end"),
        "scope_key": key,
        "volume_metrics": window.get("volume_metrics") or {},
        "latency_metrics": window.get("latency_metrics") or {},
        "data_metrics": window.get("data_metrics") or {},
        "primitive_profile": window.get("primitive_profile") or {},
        "primitive_profiles": window.get("primitive_profiles") or {},
        "template_metrics": window.get("template_metrics") or {},
        "top_templates": window.get("top_templates") or [],
    }


def _profile_doc(run_id: str, scenario: Any, profile: dict[str, Any]) -> dict[str, Any]:
    return {
        **_scope_tags(run_id, scenario),
        **_profile_scope_tags(profile),
        "profile_id": profile.get("profile_id"),
        "aggregate_window_id": profile.get("aggregate_window_id"),
        "window_start": profile.get("scope", {}).get("window_start"),
        "window_end": profile.get("scope", {}).get("window_end"),
        "scope": profile.get("scope") or {},
        "volume": profile.get("volume") or {},
        "latency": profile.get("latency") or {},
        "primitive_profile": profile.get("primitive_profile") or {},
        "primitive_profiles": profile.get("primitive_profiles") or {},
        "access_pattern_scores": profile.get("access_pattern_scores") or {},
        "dominant_patterns": profile.get("dominant_patterns") or [],
        "evidence": profile.get("evidence") or {},
    }


def _recommendation_docs(run_id: str, scenario: Any, profile: dict[str, Any]) -> Iterable[dict[str, Any]]:
    tags = {**_scope_tags(run_id, scenario), **_profile_scope_tags(profile)}
    profile_id = profile.get("profile_id")
    scope = profile.get("scope") or {}
    for index, recommendation in enumerate(profile.get("recommendations") or []):
        yield {
            **tags,
            "recommendation_id": recommendation.get("recommendation_id"),
            "profile_id": profile_id,
            "aggregate_window_id": profile.get("aggregate_window_id"),
            "window_start": scope.get("window_start"),
            "window_end": scope.get("window_end"),
            "type": recommendation.get("type"),
            "recommendation": recommendation.get("recommendation"),
            "target_technology": recommendation.get("target_technology"),
            "severity": recommendation.get("severity"),
            "confidence": recommendation.get("confidence"),
            "matched_rule_id": recommendation.get("matched_rule_id"),
            "rule_conditions": recommendation.get("rule_conditions") or [],
            "evidence": recommendation.get("evidence") or [],
            "recommendation_index": index,
        }


def _matched_primitives(primitive_event: dict[str, Any]) -> list[dict[str, Any]]:
    matched = []
    for primitive, signal in (primitive_event.get("primitive_signals") or {}).items():
        if not signal.get("matched"):
            continue
        matched.append(
            {
                "primitive": primitive,
                "signal_weight": signal.get("signal_weight", 0.0),
                "rule_confidence": signal.get("rule_confidence", 0.0),
                "rule_ids": signal.get("rule_ids") or [],
                "evidence": signal.get("evidence") or [],
            }
        )
    return sorted(matched, key=lambda item: item["primitive"])


def _profile_events(profile: dict[str, Any], primitive_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scope = profile.get("scope") or {}
    return [
        event
        for event in primitive_events
        if _event_matches_scope(event, scope)
        and str(scope.get("window_start", "")) <= str(event.get("timestamp", ""))
        and str(event.get("timestamp", "")) < str(scope.get("window_end", ""))
    ]


def _event_matches_scope(event: dict[str, Any], scope: dict[str, Any]) -> bool:
    return all(
        dimension not in scope or _dimension_value(event, dimension) == str(scope[dimension])
        for dimension in PROFILE_MATCH_DIMENSIONS
    )


def _normalized_by_event_id(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(event.get("event_id")): event
        for event in report.get("normalized_events") or []
    }


def _source_numbers(profile: dict[str, Any], recommendation: dict[str, Any]) -> list[dict[str, Any]]:
    numbers = []
    for condition in recommendation.get("rule_conditions") or []:
        observed = condition.get("observed_value")
        if isinstance(observed, (int, float)):
            numbers.append({"path": condition.get("path"), "value": observed})
    volume = profile.get("volume") or {}
    for path, value in (
        ("volume.request_count", volume.get("request_count")),
        ("volume.top_templates_coverage", volume.get("top_templates_coverage")),
    ):
        if isinstance(value, (int, float)):
            numbers.append({"path": path, "value": value})
    return numbers


def _condition_summaries(recommendation: dict[str, Any]) -> list[str]:
    summaries = []
    for condition in recommendation.get("rule_conditions") or []:
        operator = condition.get("operator")
        threshold = condition.get("threshold")
        observed = condition.get("observed_value")
        path = condition.get("path")
        passed = "passed" if condition.get("passed") else "failed"
        summaries.append(f"{path}: observed {observed} {operator} {threshold} ({passed})")
    return summaries


def _lineage_recommendation_docs(
    run_id: str,
    scenario: Any,
    report: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    primitive_events = report.get("primitive_events") or []
    for profile in report.get("profiles") or []:
        matching_events = _profile_events(profile, primitive_events)
        top_templates = profile.get("evidence", {}).get("top_templates") or []
        top_template_ids = [template.get("template_id") for template in top_templates]
        sample_event_ids = [
            event["event_id"]
            for event in matching_events
            if not top_template_ids or event.get("template_id") in top_template_ids
        ][:10]
        for recommendation in profile.get("recommendations") or []:
            yield {
                **_scope_tags(run_id, scenario),
                **_profile_scope_tags(profile),
                "recommendation_id": recommendation.get("recommendation_id"),
                "profile_id": profile.get("profile_id"),
                "aggregate_window_id": profile.get("aggregate_window_id"),
                "window_start": profile.get("scope", {}).get("window_start"),
                "window_end": profile.get("scope", {}).get("window_end"),
                "matched_rule_id": recommendation.get("matched_rule_id"),
                "recommendation": recommendation.get("recommendation"),
                "type": recommendation.get("type"),
                "severity": recommendation.get("severity"),
                "confidence": recommendation.get("confidence"),
                "target_technology": recommendation.get("target_technology"),
                "rule_conditions": recommendation.get("rule_conditions") or [],
                "rule_condition_summary": _condition_summaries(recommendation),
                "source_numbers": _source_numbers(profile, recommendation),
                "top_template_ids": top_template_ids,
                "sample_event_ids": sample_event_ids,
                "evidence": recommendation.get("evidence") or [],
            }


def _lineage_template_docs(
    run_id: str,
    scenario: Any,
    report: dict[str, Any],
    include_raw_query: bool,
) -> Iterable[dict[str, Any]]:
    primitive_events = report.get("primitive_events") or []
    normalized_by_id = _normalized_by_event_id(report)
    for profile in report.get("profiles") or []:
        profile_events = _profile_events(profile, primitive_events)
        for template in profile.get("evidence", {}).get("top_templates") or []:
            template_id = template.get("template_id")
            matching = [event for event in profile_events if event.get("template_id") == template_id]
            sample_events = matching[:5]
            first_normalized = normalized_by_id.get(sample_events[0]["event_id"]) if sample_events else {}
            query = _query_payload(first_normalized or {}, include_raw_query)
            rule_ids = sorted(
                {
                    rule_id
                    for event in matching
                    for signal in (event.get("primitive_signals") or {}).values()
                    for rule_id in (signal.get("rule_ids") or [])
                }
            )
            primitive_summary = template.get("primitive_summary") or {}
            doc = {
                **_scope_tags(run_id, scenario),
                **_profile_scope_tags(profile),
                "profile_id": profile.get("profile_id"),
                "aggregate_window_id": profile.get("aggregate_window_id"),
                "template_id": template_id,
                "request_count": template.get("request_count"),
                "contribution": template.get("contribution"),
                "primitive_summary": primitive_summary,
                "matched_primitives": [
                    primitive
                    for primitive, score in sorted(primitive_summary.items())
                    if isinstance(score, (int, float)) and score > 0
                ],
                "matched_rule_ids": rule_ids,
                "sample_event_ids": [event["event_id"] for event in sample_events],
                **query,
            }
            if include_raw_query:
                raw_samples = []
                for event in sample_events[:3]:
                    normalized = normalized_by_id.get(event["event_id"], {})
                    raw_query = (normalized.get("operation") or {}).get("raw_query")
                    if raw_query is not None:
                        if isinstance(raw_query, (dict, list)):
                            raw_samples.append(json.dumps(raw_query, sort_keys=True))
                        else:
                            raw_samples.append(str(raw_query))
                doc["raw_query_samples"] = raw_samples
            yield doc


def _event_window_ids(event: dict[str, Any], report: dict[str, Any]) -> list[str]:
    ids = []
    timestamp = str(event.get("timestamp", ""))
    for windows in (report.get("aggregation_views") or {}).values():
        for window in windows:
            key = window.get("key") or {}
            if not (str(key.get("window_start", "")) <= timestamp < str(key.get("window_end", ""))):
                continue
            dimensions_match = True
            for dimension in WINDOW_MATCH_DIMENSIONS:
                if dimension in key and _dimension_value(event, dimension) != str(key[dimension]):
                    dimensions_match = False
                    break
            if dimensions_match and window.get("aggregate_window_id"):
                ids.append(window["aggregate_window_id"])
    return sorted(set(ids))


def _event_profile(event: dict[str, Any], report: dict[str, Any]) -> dict[str, Any] | None:
    timestamp = str(event.get("timestamp", ""))
    for profile in report.get("profiles") or []:
        scope = profile.get("scope") or {}
        if (
            _event_matches_scope(event, scope)
            and str(scope.get("window_start", "")) <= timestamp < str(scope.get("window_end", ""))
        ):
            return profile
    return None


def _lineage_event_docs(
    run_id: str,
    scenario: Any,
    report: dict[str, Any],
    include_raw_query: bool,
) -> Iterable[dict[str, Any]]:
    normalized_by_id = _normalized_by_event_id(report)
    for primitive_event in report.get("primitive_events") or []:
        profile = _event_profile(primitive_event, report)
        normalized = normalized_by_id.get(primitive_event["event_id"], {})
        yield {
            **_scope_tags(run_id, scenario),
            **_event_scope_tags(primitive_event),
            "event_id": primitive_event["event_id"],
            "timestamp": primitive_event["timestamp"],
            "template_id": primitive_event["template_id"],
            "aggregate_window_ids": _event_window_ids(primitive_event, report),
            "profile_id": profile.get("profile_id") if profile else None,
            "recommendation_ids": [
                recommendation.get("recommendation_id")
                for recommendation in (profile.get("recommendations") if profile else []) or []
            ],
            "latency_ms": primitive_event.get("latency_ms"),
            "response_bytes": primitive_event.get("response_bytes"),
            "result_count": primitive_event.get("result_count"),
            "matched_primitives": _matched_primitives(primitive_event),
            **_query_payload(normalized, include_raw_query),
        }


def _lineage_validation_doc(
    run_id: str,
    scenario: Any,
    report: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    recommendation_ids = [
        recommendation.get("recommendation_id")
        for profile in report.get("profiles") or []
        for recommendation in profile.get("recommendations") or []
    ]
    return {
        **_scope_tags(run_id, scenario),
        "validation_status": validation.get("status"),
        "validation_warnings": validation.get("warnings") or [],
        "expected_primitive_share": validation.get("expected_primitive_share") or {},
        "observed_primitive_share": validation.get("observed_primitive_share") or {},
        "observed_primitive_profile": validation.get("observed_primitive_profile") or {},
        "observed_access_pattern_scores": validation.get("observed_access_pattern_scores") or {},
        "dominant_patterns": validation.get("dominant_patterns") or [],
        "recommendation_ids": recommendation_ids,
    }


def export_actions(
    run_id: str,
    scenario: Any,
    events: list[dict[str, Any]],
    report: dict[str, Any],
    validation: dict[str, Any],
    run_dir: Path,
    include_raw_query: bool = False,
    generated_at: str | None = None,
) -> list[dict[str, Any]]:
    generated_at = generated_at or _now()
    normalized_events = report.get("normalized_events") or []
    primitive_events = report.get("primitive_events") or []
    actions = [
        {
            "_index": INDEX_SIM_RUNS,
            "_id": run_id,
            "_source": {
                **_scope_tags(run_id, scenario),
                "generated_at": generated_at,
                "event_count": len(events),
                "time_range": {
                    "start": scenario.time_range.start.isoformat().replace("+00:00", "Z"),
                    "end": scenario.time_range.end.isoformat().replace("+00:00", "Z"),
                },
                "validation_status": validation.get("status"),
                "validation_warning_count": len(validation.get("warnings") or []),
                "artifact_path": str(run_dir),
            },
        }
    ]

    for primitive_event, normalized_event in zip(primitive_events, normalized_events):
        actions.append(
            {
                "_index": INDEX_PRIMITIVE_EVENTS,
                "_id": f"{run_id}:{primitive_event['event_id']}",
                "_source": _primitive_event_doc(
                    run_id,
                    scenario,
                    primitive_event,
                    normalized_event,
                    include_raw_query,
                ),
            }
        )
        for signal_doc in _primitive_signal_docs(run_id, scenario, primitive_event):
            actions.append(
                {
                    "_index": INDEX_PRIMITIVE_SIGNALS,
                    "_id": f"{run_id}:{signal_doc['event_id']}:{signal_doc['primitive']}",
                    "_source": signal_doc,
                }
            )

    for view_name, windows in (report.get("aggregation_views") or {}).items():
        for window in windows:
            actions.append(
                {
                    "_index": INDEX_AGGREGATE_WINDOWS,
                    "_id": f"{run_id}:{view_name}:{_stable_id(window.get('key'))}",
                    "_source": _aggregate_window_doc(run_id, scenario, view_name, window),
                }
            )

    for profile in report.get("profiles") or []:
        profile_action_id = f"{run_id}:{profile.get('profile_id')}"
        actions.append(
            {
                "_index": INDEX_PROFILES,
                "_id": profile_action_id,
                "_source": _profile_doc(run_id, scenario, profile),
            }
        )
        for recommendation in _recommendation_docs(run_id, scenario, profile):
            actions.append(
                {
                    "_index": INDEX_RECOMMENDATIONS,
                    "_id": f"{profile_action_id}:{recommendation.get('recommendation_id')}",
                    "_source": recommendation,
                }
            )

    for recommendation in _lineage_recommendation_docs(run_id, scenario, report):
        actions.append(
            {
                "_index": INDEX_LINEAGE_RECOMMENDATIONS,
                "_id": recommendation["recommendation_id"],
                "_source": recommendation,
            }
        )

    for template in _lineage_template_docs(run_id, scenario, report, include_raw_query):
        actions.append(
            {
                "_index": INDEX_LINEAGE_TEMPLATES,
                "_id": f"{run_id}:{template['profile_id']}:{template['template_id']}",
                "_source": template,
            }
        )

    for event in _lineage_event_docs(run_id, scenario, report, include_raw_query):
        actions.append(
            {
                "_index": INDEX_LINEAGE_EVENTS,
                "_id": f"{run_id}:{event['event_id']}",
                "_source": event,
            }
        )

    validation_doc = _lineage_validation_doc(run_id, scenario, report, validation)
    actions.append(
        {
            "_index": INDEX_LINEAGE_VALIDATION,
            "_id": run_id,
            "_source": validation_doc,
        }
    )
    return actions
