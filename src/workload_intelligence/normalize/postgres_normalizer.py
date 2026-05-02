from __future__ import annotations

import re
from typing import Any

from workload_intelligence.ingest.raw_event import RawUsageEvent, raw_event_to_dict
from workload_intelligence.normalize.template_fingerprint import template_id_for_normalized


COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
SINGLE_QUOTED_RE = re.compile(r"'(?:''|[^'])*'")
DOLLAR_PARAM_RE = re.compile(r"\$\d+")
NUMERIC_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
WHITESPACE_RE = re.compile(r"\s+")
COMMAND_RE = re.compile(r"^\s*([a-zA-Z]+)")
AGGREGATE_FUNCTION_RE = re.compile(r"\b(count|sum|avg|min|max)\s*\(", re.IGNORECASE)
PREDICATE_RE = re.compile(
    r"\b([a-z_][\w.]*)(?:\s*(?:=|<>|!=|<=|>=|<|>)\s*|\s+(?:i?like|similar\s+to)\s+|\s+in\s*\(|\s+between\s+)",
    re.IGNORECASE,
)
EQUALITY_FIELD_RE = re.compile(r"\b([a-z_][\w.]*)(?:\s*=\s*|\s+in\s*\()", re.IGNORECASE)
RANGE_FIELD_RE = re.compile(r"\b([a-z_][\w.]*)(?:\s*(?:<=|>=|<|>)\s*|\s+between\s+)", re.IGNORECASE)
LIKE_SEARCH_RE = re.compile(
    r"\b([a-z_][\w.]*)(?:\s+(?:i?like|similar\s+to)\s+)",
    re.IGNORECASE,
)
FULL_TEXT_SEARCH_RE = re.compile(
    r"@@|\b(?:to_tsvector|to_tsquery|plainto_tsquery|phraseto_tsquery|websearch_to_tsquery)\s*\(",
    re.IGNORECASE,
)
WHERE_END_RE = re.compile(
    r"\b(group\s+by|order\s+by|having|limit|offset|returning|union)\b",
    re.IGNORECASE,
)


def normalize_sql_template(sql: str) -> str:
    without_comments = COMMENT_RE.sub(" ", sql)
    without_literals = SINGLE_QUOTED_RE.sub("?", without_comments)
    without_params = DOLLAR_PARAM_RE.sub("?", without_literals)
    without_numbers = NUMERIC_RE.sub("?", without_params)
    return WHITESPACE_RE.sub(" ", without_numbers).strip().lower()


def _command(normalized_sql: str) -> str:
    match = COMMAND_RE.match(normalized_sql)
    return match.group(1).upper() if match else ""


def _clause_body(normalized_sql: str, start_pattern: str, end_pattern: re.Pattern[str]) -> str:
    match = re.search(start_pattern, normalized_sql, flags=re.IGNORECASE)
    if not match:
        return ""
    remainder = normalized_sql[match.end() :]
    end = end_pattern.search(remainder)
    return remainder[: end.start()].strip() if end else remainder.strip()


def _field_name(value: str) -> str:
    return value.split(".")[-1].lower()


def sql_features(normalized_sql: str) -> dict[str, Any]:
    where_body = _clause_body(normalized_sql, r"\bwhere\b", WHERE_END_RE)
    equality_fields = sorted({_field_name(match.group(1)) for match in EQUALITY_FIELD_RE.finditer(where_body)})
    range_fields = sorted({_field_name(match.group(1)) for match in RANGE_FIELD_RE.finditer(where_body)})
    text_search_fields = sorted({_field_name(match.group(1)) for match in LIKE_SEARCH_RE.finditer(where_body)})
    has_like_search = bool(text_search_fields)
    has_full_text_search = bool(FULL_TEXT_SEARCH_RE.search(normalized_sql))

    return {
        "command": _command(normalized_sql),
        "has_where": bool(where_body),
        "has_group_by": bool(re.search(r"\bgroup\s+by\b", normalized_sql, flags=re.IGNORECASE)),
        "has_order_by": bool(re.search(r"\border\s+by\b", normalized_sql, flags=re.IGNORECASE)),
        "has_limit": bool(re.search(r"\blimit\b", normalized_sql, flags=re.IGNORECASE)),
        "has_aggregate_function": bool(AGGREGATE_FUNCTION_RE.search(normalized_sql)),
        "has_like_search": has_like_search,
        "has_full_text_search": has_full_text_search,
        "has_text_search": has_like_search or has_full_text_search,
        "where_condition_count": len(list(PREDICATE_RE.finditer(where_body))),
        "equality_fields": equality_fields,
        "range_fields": range_fields,
        "text_search_fields": text_search_fields,
    }


def normalize_postgres_event(event: RawUsageEvent) -> dict[str, Any]:
    payload = raw_event_to_dict(event)
    raw_query = str(event.operation.get("raw_query") or event.operation.get("sql") or "")
    normalized_sql = normalize_sql_template(raw_query)
    features = sql_features(normalized_sql)
    command = str(event.operation.get("command") or features["command"]).upper()

    normalized_query = {
        "command": command,
        "sql": normalized_sql,
        "features": features,
    }
    payload["operation"]["command"] = command
    payload["operation"]["raw_query"] = raw_query
    payload["operation"]["normalized_query"] = normalized_query
    payload["operation"]["sql_features"] = features
    payload["template_id"] = template_id_for_normalized(
        {"platform": "postgres", "command": command, "sql": normalized_sql}
    )
    return payload
