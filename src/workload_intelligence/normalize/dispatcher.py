from __future__ import annotations

from typing import Any

from workload_intelligence.ingest.raw_event import RawUsageEvent
from workload_intelligence.normalize.elastic_normalizer import normalize_elasticsearch_event
from workload_intelligence.normalize.postgres_normalizer import normalize_postgres_event
from workload_intelligence.normalize.redis_normalizer import normalize_redis_event


def normalize_event(event: RawUsageEvent) -> dict[str, Any]:
    if event.platform_type == "elasticsearch":
        return normalize_elasticsearch_event(event)
    if event.platform_type == "redis":
        return normalize_redis_event(event)
    if event.platform_type == "postgres":
        return normalize_postgres_event(event)
    raise ValueError(f"no normalizer implemented for platform {event.platform_type!r}")
