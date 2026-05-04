from __future__ import annotations

from typing import Any

from workload_intelligence.aggregate.window_aggregator import aggregate_daily, aggregate_daily_views
from workload_intelligence.ingest.raw_event import raw_event_from_dict
from workload_intelligence.normalize.dispatcher import normalize_event
from workload_intelligence.primitives.extractor import extract_primitives
from workload_intelligence.profiles.profile_builder import build_profiles


def normalized_events_from_raw(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_event(raw_event_from_dict(event)) for event in raw_events]


def primitive_events_from_normalized(normalized_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [extract_primitives(event) for event in normalized_events]


def primitive_events_from_raw(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return primitive_events_from_normalized(normalized_events_from_raw(raw_events))


def process_events(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primitive_events = primitive_events_from_raw(raw_events)
    windows = aggregate_daily(primitive_events)
    return build_profiles(windows)


def process_event_report(
    raw_events: list[dict[str, Any]],
    include_primitive_events: bool = False,
    include_normalized_events: bool = False,
) -> dict[str, Any]:
    normalized_events = normalized_events_from_raw(raw_events)
    primitive_events = primitive_events_from_normalized(normalized_events)
    aggregation_views = aggregate_daily_views(primitive_events)
    report = {
        "profiles": build_profiles(aggregation_views["profile"]),
        "aggregation_views": aggregation_views,
    }
    if include_primitive_events:
        report["primitive_events"] = primitive_events
    if include_normalized_events:
        report["normalized_events"] = normalized_events
    return report
