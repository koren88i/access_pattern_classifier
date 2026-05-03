from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


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


@dataclass(frozen=True)
class RuleCondition:
    matches: Callable[[dict[str, Any], Any], bool]
    source_functions: tuple[Callable[..., Any], ...]


def _any_path_exists_matches(payload: dict[str, Any], expected: Any) -> bool:
    return any(path_exists(payload, path) for path in expected)


def _body_contains_any_key_matches(payload: dict[str, Any], expected: Any) -> bool:
    body = path_get(payload, "$.operation.raw_query") or {}
    return contains_any_key(body, set(expected))


def _multi_filter_exists_matches(payload: dict[str, Any], expected: Any) -> bool:
    return multi_filter_exists(payload, int(expected or 2))


def _term_filter_exists_matches(payload: dict[str, Any], _expected: Any) -> bool:
    return term_filter_exists(payload)


def _result_count_gte_matches(payload: dict[str, Any], expected: Any) -> bool:
    return result_count_gte(payload, int(expected))


def _ttl_or_expire_signal_matches(payload: dict[str, Any], expected: Any) -> bool:
    return ttl_or_expire_signal(payload) is bool(expected)


def _sql_where_condition_count_gte_matches(payload: dict[str, Any], expected: Any) -> bool:
    return sql_where_condition_count_gte(payload, int(expected))


def _sql_equality_field_matches(payload: dict[str, Any], expected: Any) -> bool:
    return _sql_field_matches(payload, "equality_fields", expected)


def _sql_range_field_matches(payload: dict[str, Any], expected: Any) -> bool:
    return _sql_field_matches(payload, "range_fields", expected)


CONDITION_REGISTRY: dict[str, RuleCondition] = {
    "any_path_exists": RuleCondition(_any_path_exists_matches, (path_exists,)),
    "body_contains_any_key": RuleCondition(
        _body_contains_any_key_matches,
        (contains_any_key, iter_dicts),
    ),
    "command_in": RuleCondition(command_in, (command_in,)),
    "endpoint_contains": RuleCondition(endpoint_contains, (endpoint_contains,)),
    "multi_filter_exists": RuleCondition(
        _multi_filter_exists_matches,
        (multi_filter_exists, iter_dicts),
    ),
    "path_exists": RuleCondition(path_exists, (path_exists,)),
    "range_filter_field_matches": RuleCondition(
        range_filter_field_matches,
        (range_filter_field_matches, iter_dicts),
    ),
    "result_count_gte": RuleCondition(_result_count_gte_matches, (result_count_gte,)),
    "sql_command_in": RuleCondition(sql_command_in, (sql_command_in, _sql_features)),
    "sql_equality_field_matches": RuleCondition(
        _sql_equality_field_matches,
        (_sql_field_matches, _sql_features),
    ),
    "sql_has_any_feature": RuleCondition(
        sql_has_any_feature,
        (sql_has_any_feature, _sql_features),
    ),
    "sql_range_field_matches": RuleCondition(
        _sql_range_field_matches,
        (_sql_field_matches, _sql_features),
    ),
    "sql_where_condition_count_gte": RuleCondition(
        _sql_where_condition_count_gte_matches,
        (sql_where_condition_count_gte, _sql_features),
    ),
    "term_filter_exists": RuleCondition(
        _term_filter_exists_matches,
        (term_filter_exists, contains_any_key, iter_dicts),
    ),
    "ttl_or_expire_signal": RuleCondition(
        _ttl_or_expire_signal_matches,
        (ttl_or_expire_signal,),
    ),
}


def _condition_matches(payload: dict[str, Any], name: str, expected: Any) -> bool:
    condition = CONDITION_REGISTRY.get(name)
    if not condition:
        raise ValueError(f"unsupported rule condition: {name}")
    return condition.matches(payload, expected)


def rule_matches(payload: dict[str, Any], rule: dict[str, Any]) -> bool:
    if rule.get("platform") != path_get(payload, "$.platform.type"):
        return False
    conditions = rule.get("when") or {}
    return all(_condition_matches(payload, name, expected) for name, expected in conditions.items())
