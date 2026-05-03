from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from workload_intelligence.ingest.raw_event import raw_event_from_dict
from workload_intelligence.normalize.dispatcher import normalize_event
from workload_intelligence.normalize import elastic_normalizer, postgres_normalizer, redis_normalizer
from workload_intelligence.primitives import extractor, rule_engine
from workload_intelligence.simulator import generators
from workload_intelligence.simulator.scenario import QueryShape, Scenario, Target, TimeRange
from workload_intelligence.specs import REPO_ROOT, load_spec


FunctionRef = Callable[..., Any]


GENERATOR_FUNCTIONS: dict[str, FunctionRef] = {
    "elasticsearch": generators._elastic_operation,
    "postgres": generators._postgres_operation,
    "redis": generators._redis_operation,
}

NORMALIZER_FUNCTIONS: dict[str, list[FunctionRef]] = {
    "elasticsearch": [
        elastic_normalizer.normalize_elasticsearch_event,
    ],
    "postgres": [
        postgres_normalizer.normalize_sql_template,
        postgres_normalizer.sql_features,
        postgres_normalizer.normalize_postgres_event,
    ],
    "redis": [
        redis_normalizer.redis_has_ttl_signal,
        redis_normalizer.normalize_redis_event,
    ],
}

CONDITION_FUNCTIONS: dict[str, list[FunctionRef]] = {
    name: list(condition.source_functions)
    for name, condition in rule_engine.CONDITION_REGISTRY.items()
}


def _relative_path(path: str | None) -> str:
    if not path:
        return ""
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _function_block(role: str, function: FunctionRef) -> dict[str, str]:
    return {
        "role": role,
        "name": function.__name__,
        "path": _relative_path(inspect.getsourcefile(function)),
        "source": inspect.getsource(function).rstrip(),
    }


def _rule_block(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(rule["id"]),
        "path": "specs/primitive-rules.yaml",
        "conditions": list((rule.get("when") or {}).keys()),
        "source": yaml.safe_dump({"rules": [rule]}, sort_keys=False).rstrip(),
    }


def _rules_for(platform: str, primitive: str) -> list[dict[str, Any]]:
    return [
        rule
        for rule in load_spec("primitive-rules.yaml").get("rules", [])
        if rule.get("platform") == platform and rule.get("primitive") == primitive
    ]


def _sample_scenario(platform: str, primitives: list[str]) -> Scenario:
    target = Target(
        platform=platform,
        system_id="demo-api",
        customer_id="acme",
        database_or_index="events" if platform == "elasticsearch" else "orders",
    )
    responses = {
        "latency_ms": {"distribution": "fixed", "value": 80},
        "response_bytes": {"distribution": "fixed", "value": 10000},
        "result_count": {"distribution": "fixed", "value": 25},
    }
    shape = QueryShape(name="inspected_shape", share=100.0, primitives=primitives, responses={})
    return Scenario(
        name="matcher_inspection",
        seed=1,
        target=target,
        time_range=TimeRange(
            start=datetime(2026, 4, 30, tzinfo=timezone.utc),
            end=datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
        events=1,
        responses=responses,
        query_shapes=[shape],
        raw_payload={},
    )


def _field_value(payload: dict[str, Any], path: str) -> Any:
    return rule_engine.path_get(payload, path)


def _condition_relevant_fields(payload: dict[str, Any], name: str, expected: Any) -> list[dict[str, Any]]:
    if name == "path_exists":
        return [{"path": expected, "value": _field_value(payload, expected)}]
    if name == "any_path_exists":
        return [{"path": path, "value": _field_value(payload, path)} for path in expected]
    if name == "command_in":
        return [{"path": "$.operation.command", "value": _field_value(payload, "$.operation.command")}]
    if name == "endpoint_contains":
        return [{"path": "$.operation.endpoint", "value": _field_value(payload, "$.operation.endpoint")}]
    if name == "result_count_gte":
        return [{"path": "$.response.result_count", "value": _field_value(payload, "$.response.result_count")}]
    if name == "ttl_or_expire_signal":
        return [
            {
                "path": "$.operation.ttl_or_expire_signal",
                "value": _field_value(payload, "$.operation.ttl_or_expire_signal"),
            }
        ]
    if name == "sql_command_in":
        return [
            {"path": "$.operation.sql_features.command", "value": _field_value(payload, "$.operation.sql_features.command")},
            {"path": "$.operation.command", "value": _field_value(payload, "$.operation.command")},
        ]
    if name == "sql_has_any_feature":
        return [
            {
                "path": f"$.operation.sql_features.{feature}",
                "value": _field_value(payload, f"$.operation.sql_features.{feature}"),
            }
            for feature in expected
        ]
    if name == "sql_where_condition_count_gte":
        return [
            {
                "path": "$.operation.sql_features.where_condition_count",
                "value": _field_value(payload, "$.operation.sql_features.where_condition_count"),
            }
        ]
    if name == "sql_equality_field_matches":
        return [
            {
                "path": "$.operation.sql_features.equality_fields",
                "value": _field_value(payload, "$.operation.sql_features.equality_fields"),
            }
        ]
    if name == "sql_range_field_matches":
        return [
            {
                "path": "$.operation.sql_features.range_fields",
                "value": _field_value(payload, "$.operation.sql_features.range_fields"),
            }
        ]
    if name in {"body_contains_any_key", "term_filter_exists", "multi_filter_exists", "range_filter_field_matches"}:
        return [{"path": "$.operation.raw_query", "value": _field_value(payload, "$.operation.raw_query")}]
    return [{"path": "$", "value": payload}]


def _relevant_matcher_fields(payload: dict[str, Any], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relevant: list[dict[str, Any]] = []
    for rule in rules:
        conditions = []
        for name, expected in (rule.get("when") or {}).items():
            conditions.append(
                {
                    "condition": name,
                    "expected": expected,
                    "matched": rule_engine._condition_matches(payload, name, expected),
                    "fields": _condition_relevant_fields(payload, name, expected),
                }
            )
        relevant.append(
            {
                "rule_id": str(rule["id"]),
                "matched": rule_engine.rule_matches(payload, rule),
                "conditions": conditions,
            }
        )
    return relevant


def _sample_match(
    platform: str,
    primitive: str,
    selected_primitives: list[str],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    primitives = list(dict.fromkeys(selected_primitives))
    event = generators.generate_events(_sample_scenario(platform, primitives))[0]
    normalized = normalize_event(raw_event_from_dict(event))
    primitive_event = extractor.extract_primitives(normalized)
    return {
        "selected_primitives": primitives,
        "generated_operation": event["operation"],
        "relevant_matcher_fields": _relevant_matcher_fields(normalized, rules),
        "normalized_matcher_input": {
            "platform": normalized["platform"],
            "operation": normalized["operation"],
            "response": normalized["response"],
            "template_id": normalized["template_id"],
        },
        "selected_primitive_signal": primitive_event["primitive_signals"][primitive],
    }


def matcher_source_for(
    platform: str,
    primitive: str,
    selected_primitives: list[str] | None = None,
) -> dict[str, Any]:
    selected_primitives = selected_primitives or []
    if primitive not in selected_primitives:
        return {
            "platform": platform,
            "primitive": primitive,
            "inactive": True,
            "selected_primitives": selected_primitives,
            "sample": None,
            "rules": [],
            "code": [],
        }

    rules = _rules_for(platform, primitive)
    condition_names = sorted(
        {
            condition
            for rule in rules
            for condition in (rule.get("when") or {}).keys()
        }
    )

    code_blocks: list[dict[str, str]] = []
    generator = GENERATOR_FUNCTIONS.get(platform)
    if generator:
        code_blocks.append(_function_block("simulator query generator", generator))

    for normalizer in NORMALIZER_FUNCTIONS.get(platform, []):
        code_blocks.append(_function_block("platform normalizer", normalizer))

    code_blocks.extend(
        [
            _function_block("primitive extractor", extractor.extract_primitives),
            _function_block("rule evaluator", rule_engine.rule_matches),
            _function_block("condition dispatcher", rule_engine._condition_matches),
        ]
    )

    seen_functions = {(block["path"], block["name"]) for block in code_blocks}
    for condition_name in condition_names:
        for function in CONDITION_FUNCTIONS.get(condition_name, []):
            key = (_relative_path(inspect.getsourcefile(function)), function.__name__)
            if key in seen_functions:
                continue
            code_blocks.append(_function_block(f"condition: {condition_name}", function))
            seen_functions.add(key)

    return {
        "platform": platform,
        "primitive": primitive,
        "sample": _sample_match(platform, primitive, selected_primitives, rules),
        "rules": [_rule_block(rule) for rule in rules],
        "code": code_blocks,
    }
