from __future__ import annotations

import json
import random
from datetime import timedelta
from typing import Any

from workload_intelligence.simulator.sampling import sample_response_metadata, shape_counts
from workload_intelligence.simulator.scenario import QueryShape, Scenario, Target


def _iso_z(value) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _platform_payload(target: Target) -> dict[str, Any]:
    if target.platform == "postgres":
        return {
            "type": "postgres",
            "database": target.database_or_index,
            "index_or_table": target.database_or_index,
        }
    if target.platform == "elasticsearch":
        return {
            "type": "elasticsearch",
            "index_or_table": target.database_or_index,
        }
    if target.platform == "redis":
        return {
            "type": "redis",
            "database": target.database_or_index,
        }
    raise ValueError(f"unsupported platform: {target.platform}")


def _identity_payload(target: Target) -> dict[str, Any]:
    identity = {"system_id": target.system_id}
    if target.customer_id:
        identity["customer_id"] = target.customer_id
    return identity


def _postgres_operation(shape: QueryShape, target: Target, index: int) -> dict[str, Any]:
    primitives = set(shape.primitives)
    table = target.database_or_index
    literal = index + 1000

    if "point_write" in primitives:
        sql = (
            f"INSERT INTO {table} (id, customer_id, status, created_at) "
            f"VALUES ({literal}, {literal + 1}, 'active', now())"
        )
        return {"command": "INSERT", "raw_query": sql}
    if "update_write" in primitives:
        sql = f"UPDATE {table} SET status = 'processed' WHERE id = {literal}"
        return {"command": "UPDATE", "raw_query": sql}

    select_clause = "id, customer_id, status, created_at"
    where_parts: list[str] = []
    group_clause = ""
    order_clause = ""

    if "aggregation" in primitives:
        select_clause = "customer_id, date_trunc('hour', created_at) AS bucket, count(*) AS events"
        group_clause = " GROUP BY customer_id, date_trunc('hour', created_at)"
    if "key_lookup" in primitives:
        where_parts.append(f"id = {literal}")
    if "time_series" in primitives:
        day = (index % 27) + 1
        where_parts.append(f"created_at >= '2026-04-{day:02d}T00:00:00Z'")
        where_parts.append(f"created_at < '2026-04-{day + 1:02d}T00:00:00Z'")
    elif "range_lookup" in primitives:
        where_parts.append(f"amount_cents >= {100 + index}")
        where_parts.append(f"amount_cents < {500 + index}")
    if "text_search" in primitives:
        term = ("running shoes", "winter coat", "refund policy", "travel bag")[index % 4]
        where_parts.append(f"title ILIKE '%{term}%'")
    if "multi_filter" in primitives:
        where_parts.append("status = 'paid'")
        if len(where_parts) < 2:
            where_parts.append("region = 'us'")
    if "sort_paginate" in primitives:
        order_clause = " ORDER BY created_at DESC LIMIT 20"

    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = f"SELECT {select_clause} FROM {table}{where_clause}{group_clause}{order_clause}"
    return {"command": "SELECT", "raw_query": sql}


def _elastic_operation(shape: QueryShape, target: Target, index: int) -> dict[str, Any]:
    primitives = set(shape.primitives)
    filters: list[dict[str, Any]] = []
    body: dict[str, Any] = {}

    if "key_lookup" in primitives:
        filters.append({"term": {"customer_id": f"cust-{index % 50}"}})
    if "time_series" in primitives:
        day = (index % 27) + 1
        filters.append(
            {
                "range": {
                    "@timestamp": {
                        "gte": f"2026-04-{day:02d}T00:00:00Z",
                        "lt": f"2026-04-{day + 1:02d}T00:00:00Z",
                    }
                }
            }
        )
    elif "range_lookup" in primitives:
        filters.append({"range": {"amount_cents": {"gte": 100 + index, "lt": 500 + index}}})
    if "multi_filter" in primitives:
        filters.append({"term": {"status": "paid"}})
        if len(filters) < 2:
            filters.append({"term": {"region": "us"}})
    if "geo_search" in primitives:
        filters.append({"geo_distance": {"distance": "10km", "location": {"lat": 40.7, "lon": -74.0}}})

    if "scan" in primitives:
        body["query"] = {"match_all": {}}
    elif "text_search" in primitives:
        body["query"] = {"match": {"message": f"search phrase {index % 10}"}}
    elif filters:
        body["query"] = {"bool": {"filter": filters}}

    if "vector_search" in primitives:
        body["knn"] = {
            "field": "embedding",
            "query_vector": [0.12, 0.34, 0.56],
            "k": 10,
            "num_candidates": 100,
        }
    if "aggregation" in primitives:
        body["aggs"] = {"by_status": {"terms": {"field": "status"}}}
    if "sort_paginate" in primitives:
        body["sort"] = [{"created_at": {"order": "desc"}}]
        body["from"] = (index % 5) * 20
        body["size"] = 20

    return {
        "command": "SEARCH",
        "method": "POST",
        "endpoint": f"/{target.database_or_index}/_search",
        "raw_query": body,
    }


def _redis_operation(shape: QueryShape, target: Target, index: int) -> dict[str, Any]:
    primitives = set(shape.primitives)
    key = f"{target.system_id}:key:{index % 25}"
    value = f"value-{index}"

    if "batch_write" in primitives:
        args = ["MSET", key, value, f"{key}:extra", f"{value}:extra"]
    elif "point_write" in primitives and "ttl_or_expire_usage" in primitives:
        args = ["SETEX", key, "300", value]
    elif "point_write" in primitives:
        args = ["SET", key, value]
    elif "ttl_or_expire_usage" in primitives:
        args = ["EXPIRE", key, "300"]
    else:
        args = ["GET", key]

    return {
        "command": args[0],
        "args": args,
        "key": key,
        "key_pattern": f"{target.system_id}:key:*",
        "raw_query": " ".join(args),
    }


def operation_for_shape(shape: QueryShape, target: Target, index: int) -> dict[str, Any]:
    if target.platform == "postgres":
        return _postgres_operation(shape, target, index)
    if target.platform == "elasticsearch":
        return _elastic_operation(shape, target, index)
    if target.platform == "redis":
        return _redis_operation(shape, target, index)
    raise ValueError(f"unsupported platform: {target.platform}")


def generate_events(scenario: Scenario) -> list[dict[str, Any]]:
    rng = random.Random(scenario.seed)
    shapes: list[QueryShape] = []
    for shape, count in shape_counts(scenario):
        shapes.extend([shape] * count)
    rng.shuffle(shapes)

    span = scenario.time_range.end - scenario.time_range.start
    events: list[dict[str, Any]] = []
    for index, shape in enumerate(shapes):
        offset = span * (index / max(1, scenario.events))
        timestamp = scenario.time_range.start + offset
        operation = operation_for_shape(shape, scenario.target, index)
        response = sample_response_metadata(scenario, shape, rng)
        raw_query = operation.get("raw_query", "")
        request_bytes = len(raw_query) if isinstance(raw_query, str) else len(json.dumps(raw_query, sort_keys=True))

        events.append(
            {
                "event_id": f"sim-{scenario.name}-{index + 1:06d}",
                "timestamp": _iso_z(timestamp),
                "identity": _identity_payload(scenario.target),
                "platform": _platform_payload(scenario.target),
                "operation": operation,
                "request": {"request_bytes": request_bytes},
                "response": response,
            }
        )
    return events
