from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_ELASTICSEARCH_URL = os.environ.get("WORKLOAD_ELASTICSEARCH_URL", "http://localhost:9200")
DEFAULT_KIBANA_URL = os.environ.get("WORKLOAD_KIBANA_URL", "http://localhost:5601")

INDEX_SIM_RUNS = "workload-sim-runs"
INDEX_PRIMITIVE_EVENTS = "workload-primitive-events"
INDEX_PRIMITIVE_SIGNALS = "workload-primitive-signals"
INDEX_AGGREGATE_WINDOWS = "workload-aggregate-windows"
INDEX_PROFILES = "workload-profiles"
INDEX_RECOMMENDATIONS = "workload-recommendations"
INDEX_LINEAGE_RECOMMENDATIONS = "workload-lineage-recommendations"
INDEX_LINEAGE_TEMPLATES = "workload-lineage-templates"
INDEX_LINEAGE_EVENTS = "workload-lineage-events"
INDEX_LINEAGE_VALIDATION = "workload-lineage-validation"

EXPORT_INDICES = (
    INDEX_SIM_RUNS,
    INDEX_PRIMITIVE_EVENTS,
    INDEX_PRIMITIVE_SIGNALS,
    INDEX_AGGREGATE_WINDOWS,
    INDEX_PROFILES,
    INDEX_RECOMMENDATIONS,
    INDEX_LINEAGE_RECOMMENDATIONS,
    INDEX_LINEAGE_TEMPLATES,
    INDEX_LINEAGE_EVENTS,
    INDEX_LINEAGE_VALIDATION,
)


class ElasticExportError(RuntimeError):
    pass


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
    tags = _scope_tags(run_id, scenario)
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
    tags = _scope_tags(run_id, scenario)
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
        if event.get("system_id") == scope.get("system_id")
        and event.get("platform") == scope.get("platform")
        and str(scope.get("window_start", "")) <= str(event.get("timestamp", ""))
        and str(event.get("timestamp", "")) < str(scope.get("window_end", ""))
    ]


def _profile_system_window(profile: dict[str, Any], report: dict[str, Any]) -> dict[str, Any] | None:
    aggregate_window_id = profile.get("aggregate_window_id")
    if aggregate_window_id:
        for window in (report.get("aggregation_views") or {}).get("system", []):
            if window.get("aggregate_window_id") == aggregate_window_id:
                return window
    scope = profile.get("scope") or {}
    for window in (report.get("aggregation_views") or {}).get("system", []):
        key = window.get("key") or {}
        if (
            key.get("system_id") == scope.get("system_id")
            and key.get("platform") == scope.get("platform")
            and key.get("window_start") == scope.get("window_start")
            and key.get("window_end") == scope.get("window_end")
        ):
            return window
    return None


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
            for dimension in ("system_id", "platform", "customer_id", "template_id"):
                if dimension in key and str(event.get(dimension)) != str(key[dimension]):
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
            event.get("system_id") == scope.get("system_id")
            and event.get("platform") == scope.get("platform")
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


def index_templates() -> dict[str, dict[str, Any]]:
    keyword = {"type": "keyword"}
    date = {"type": "date"}
    double = {"type": "double"}
    integer = {"type": "integer"}
    flattened = {"type": "flattened"}
    text = {"type": "text"}
    condition = {
        "type": "nested",
        "properties": {
            "path": keyword,
            "operator": keyword,
            "threshold": keyword,
            "threshold_number": double,
            "observed_value": {"type": "keyword"},
            "observed_number": double,
            "passed": {"type": "boolean"},
        },
    }
    source_number = {
        "type": "nested",
        "properties": {"path": keyword, "value": double},
    }
    matched_primitive = {
        "type": "nested",
        "properties": {
            "primitive": keyword,
            "signal_weight": double,
            "rule_confidence": double,
            "rule_ids": keyword,
            "evidence": text,
        },
    }
    common = {
        "run_id": keyword,
        "scenario_name": keyword,
        "seed": integer,
        "system_id": keyword,
        "customer_id": keyword,
        "platform": keyword,
    }
    return {
        INDEX_SIM_RUNS: {
            "generated_at": date,
            "event_count": integer,
            "validation_status": keyword,
            "validation_warning_count": integer,
            "artifact_path": keyword,
            "time_range": flattened,
            **common,
        },
        INDEX_PRIMITIVE_EVENTS: {
            "event_id": keyword,
            "timestamp": date,
            "template_id": keyword,
            "database_or_index": keyword,
            "latency_ms": double,
            "response_bytes": double,
            "result_count": double,
            "command": keyword,
            "endpoint": keyword,
            "method": keyword,
            "normalized_query": flattened,
            "normalized_query_text": text,
            "normalized_query_command": keyword,
            "raw_query_body": flattened,
            "raw_query_text": text,
            "primitive_signals": flattened,
            **common,
        },
        INDEX_PRIMITIVE_SIGNALS: {
            "event_id": keyword,
            "timestamp": date,
            "template_id": keyword,
            "primitive": keyword,
            "signal_weight": double,
            "rule_confidence": double,
            "evidence": text,
            "rule_ids": keyword,
            **common,
        },
        INDEX_AGGREGATE_WINDOWS: {
            "aggregate_window_id": keyword,
            "aggregation_view": keyword,
            "window_start": date,
            "window_end": date,
            "scope_key": flattened,
            "volume_metrics": flattened,
            "latency_metrics": flattened,
            "data_metrics": flattened,
            "primitive_profile": flattened,
            "primitive_profiles": flattened,
            "template_metrics": flattened,
            "top_templates": flattened,
            **common,
        },
        INDEX_PROFILES: {
            "profile_id": keyword,
            "aggregate_window_id": keyword,
            "window_start": date,
            "window_end": date,
            "scope": flattened,
            "volume": flattened,
            "latency": flattened,
            "primitive_profile": flattened,
            "primitive_profiles": flattened,
            "access_pattern_scores": flattened,
            "dominant_patterns": flattened,
            "evidence": flattened,
            **common,
        },
        INDEX_RECOMMENDATIONS: {
            "recommendation_id": keyword,
            "profile_id": keyword,
            "aggregate_window_id": keyword,
            "window_start": date,
            "window_end": date,
            "type": keyword,
            "recommendation": text,
            "target_technology": text,
            "severity": keyword,
            "confidence": double,
            "matched_rule_id": keyword,
            "rule_conditions": condition,
            "evidence": text,
            "recommendation_index": integer,
            **common,
        },
        INDEX_LINEAGE_RECOMMENDATIONS: {
            "recommendation_id": keyword,
            "profile_id": keyword,
            "aggregate_window_id": keyword,
            "window_start": date,
            "window_end": date,
            "matched_rule_id": keyword,
            "recommendation": text,
            "type": keyword,
            "severity": keyword,
            "confidence": double,
            "target_technology": text,
            "rule_conditions": condition,
            "rule_condition_summary": text,
            "source_numbers": source_number,
            "top_template_ids": keyword,
            "sample_event_ids": keyword,
            "evidence": text,
            **common,
        },
        INDEX_LINEAGE_TEMPLATES: {
            "profile_id": keyword,
            "aggregate_window_id": keyword,
            "template_id": keyword,
            "request_count": integer,
            "contribution": double,
            "primitive_summary": flattened,
            "matched_primitives": keyword,
            "matched_rule_ids": keyword,
            "sample_event_ids": keyword,
            "normalized_query": flattened,
            "normalized_query_text": text,
            "normalized_query_command": keyword,
            "raw_query_body": flattened,
            "raw_query_text": text,
            "raw_query_samples": text,
            **common,
        },
        INDEX_LINEAGE_EVENTS: {
            "event_id": keyword,
            "timestamp": date,
            "template_id": keyword,
            "aggregate_window_ids": keyword,
            "profile_id": keyword,
            "recommendation_ids": keyword,
            "latency_ms": double,
            "response_bytes": double,
            "result_count": double,
            "matched_primitives": matched_primitive,
            "normalized_query": flattened,
            "normalized_query_text": text,
            "normalized_query_command": keyword,
            "raw_query_body": flattened,
            "raw_query_text": text,
            **common,
        },
        INDEX_LINEAGE_VALIDATION: {
            "validation_status": keyword,
            "validation_warnings": {"type": "nested", "dynamic": True},
            "expected_primitive_share": flattened,
            "observed_primitive_share": flattened,
            "observed_primitive_profile": flattened,
            "observed_access_pattern_scores": flattened,
            "dominant_patterns": {"type": "nested", "dynamic": True},
            "recommendation_ids": keyword,
            **common,
        },
    }


def _load_elasticsearch_client() -> tuple[Any, Any]:
    try:
        from elasticsearch import Elasticsearch, helpers
    except ImportError as exc:
        raise ElasticExportError(
            "The official Elasticsearch Python client is required for --index-elastic. "
            "Install it with: python -m pip install elasticsearch"
        ) from exc
    return Elasticsearch, helpers


def create_elasticsearch_client(url: str = DEFAULT_ELASTICSEARCH_URL) -> Any:
    Elasticsearch, _helpers = _load_elasticsearch_client()
    client = Elasticsearch(url)
    try:
        if not client.ping():
            raise ElasticExportError(f"Elasticsearch did not respond at {url}")
    except Exception as exc:
        if isinstance(exc, ElasticExportError):
            raise
        raise ElasticExportError(f"Could not connect to Elasticsearch at {url}: {exc}") from exc
    return client


def ensure_index_templates(client: Any) -> None:
    for index_name, properties in index_templates().items():
        client.indices.put_index_template(
            name=f"{index_name}-template",
            index_patterns=[index_name],
            template={"mappings": {"dynamic": True, "properties": properties}},
        )


def index_run(
    run_id: str,
    scenario: Any,
    events: list[dict[str, Any]],
    report: dict[str, Any],
    validation: dict[str, Any],
    run_dir: Path,
    elasticsearch_url: str = DEFAULT_ELASTICSEARCH_URL,
    include_raw_query: bool = False,
) -> dict[str, Any]:
    client = create_elasticsearch_client(elasticsearch_url)
    _Elasticsearch, helpers = _load_elasticsearch_client()
    ensure_index_templates(client)
    actions = export_actions(
        run_id=run_id,
        scenario=scenario,
        events=events,
        report=report,
        validation=validation,
        run_dir=run_dir,
        include_raw_query=include_raw_query,
    )
    try:
        indexed, errors = helpers.bulk(client, actions, refresh=True, raise_on_error=False)
    except Exception as exc:
        raise ElasticExportError(f"Bulk indexing failed: {exc}") from exc
    if errors:
        raise ElasticExportError(f"Bulk indexing completed with errors: {errors[:3]}")
    return {"indexed": indexed, "indices": sorted({action["_index"] for action in actions})}
