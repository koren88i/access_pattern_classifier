from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class PrimitiveSignal:
    matched: bool
    signal_weight: float
    rule_confidence: float
    evidence: list[str]
    rule_ids: list[str]


def empty_signal() -> PrimitiveSignal:
    return PrimitiveSignal(False, 0.0, 0.0, [], [])


def _unwrap_root(path: str) -> list[str]:
    if not path.startswith("$."):
        raise ValueError(f"only simple root paths are supported: {path}")
    return [part for part in path[2:].split(".") if part]


def path_get(payload: Any, path: str) -> Any:
    current = payload
    for part in _unwrap_root(path):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def path_exists(payload: dict[str, Any], path: str) -> bool:
    return path_get(payload, path) is not None


def iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def contains_any_key(value: Any, keys: set[str]) -> bool:
    return any(bool(keys.intersection(item.keys())) for item in iter_dicts(value))


def range_filter_field_matches(payload: dict[str, Any], fields: list[str]) -> bool:
    body = path_get(payload, "$.operation.raw_query") or {}
    wanted = set(fields)
    for item in iter_dicts(body):
        range_clause = item.get("range")
        if isinstance(range_clause, dict) and wanted.intersection(range_clause.keys()):
            return True
    return False


def term_filter_exists(payload: dict[str, Any]) -> bool:
    body = path_get(payload, "$.operation.raw_query") or {}
    return contains_any_key(body, {"term", "ids"})


def multi_filter_exists(payload: dict[str, Any], min_filters: int = 2) -> bool:
    body = path_get(payload, "$.operation.raw_query") or {}
    for item in iter_dicts(body):
        bool_clause = item.get("bool")
        if not isinstance(bool_clause, dict):
            continue
        filters = bool_clause.get("filter") or bool_clause.get("must")
        if isinstance(filters, list) and len(filters) >= min_filters:
            return True
    return False


def command_in(payload: dict[str, Any], commands: list[str]) -> bool:
    command = str(path_get(payload, "$.operation.command") or "").upper()
    return command in {item.upper() for item in commands}


def endpoint_contains(payload: dict[str, Any], values: list[str]) -> bool:
    endpoint = str(path_get(payload, "$.operation.endpoint") or "").lower()
    return any(value.lower() in endpoint for value in values)


def result_count_gte(payload: dict[str, Any], threshold: int) -> bool:
    result_count = path_get(payload, "$.response.result_count")
    return isinstance(result_count, (int, float)) and result_count >= threshold


def ttl_or_expire_signal(payload: dict[str, Any]) -> bool:
    return bool(path_get(payload, "$.operation.ttl_or_expire_signal"))


def _sql_features(payload: dict[str, Any]) -> dict[str, Any]:
    features = path_get(payload, "$.operation.sql_features")
    return features if isinstance(features, dict) else {}


def sql_command_in(payload: dict[str, Any], commands: list[str]) -> bool:
    command = str(_sql_features(payload).get("command") or path_get(payload, "$.operation.command") or "").upper()
    return command in {item.upper() for item in commands}


def sql_has_any_feature(payload: dict[str, Any], features: list[str]) -> bool:
    sql = _sql_features(payload)
    return any(bool(sql.get(feature)) for feature in features)


def sql_where_condition_count_gte(payload: dict[str, Any], threshold: int) -> bool:
    return int(_sql_features(payload).get("where_condition_count") or 0) >= threshold


def _sql_field_matches(payload: dict[str, Any], feature: str, fields: list[str]) -> bool:
    actual = {str(field).lower() for field in _sql_features(payload).get(feature, [])}
    wanted = {str(field).lower() for field in fields}
    return bool(actual.intersection(wanted))


def _condition_matches(payload: dict[str, Any], name: str, expected: Any) -> bool:
    if name == "path_exists":
        return path_exists(payload, expected)
    if name == "any_path_exists":
        return any(path_exists(payload, path) for path in expected)
    if name == "range_filter_field_matches":
        return range_filter_field_matches(payload, expected)
    if name == "term_filter_exists":
        return term_filter_exists(payload)
    if name == "multi_filter_exists":
        return multi_filter_exists(payload, int(expected or 2))
    if name == "body_contains_any_key":
        body = path_get(payload, "$.operation.raw_query") or {}
        return contains_any_key(body, set(expected))
    if name == "command_in":
        return command_in(payload, expected)
    if name == "endpoint_contains":
        return endpoint_contains(payload, expected)
    if name == "result_count_gte":
        return result_count_gte(payload, int(expected))
    if name == "ttl_or_expire_signal":
        return ttl_or_expire_signal(payload) is bool(expected)
    if name == "sql_command_in":
        return sql_command_in(payload, expected)
    if name == "sql_has_any_feature":
        return sql_has_any_feature(payload, expected)
    if name == "sql_where_condition_count_gte":
        return sql_where_condition_count_gte(payload, int(expected))
    if name == "sql_equality_field_matches":
        return _sql_field_matches(payload, "equality_fields", expected)
    if name == "sql_range_field_matches":
        return _sql_field_matches(payload, "range_fields", expected)
    raise ValueError(f"unsupported rule condition: {name}")


def rule_matches(payload: dict[str, Any], rule: dict[str, Any]) -> bool:
    if rule.get("platform") != path_get(payload, "$.platform.type"):
        return False
    conditions = rule.get("when") or {}
    return all(_condition_matches(payload, name, expected) for name, expected in conditions.items())
