from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from workload_intelligence.simulator.capabilities import platform_names, response_distributions, unsupported_reasons


REQUIRED_RESPONSE_METRICS = ("latency_ms", "response_bytes", "result_count")


class ScenarioValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Target:
    platform: str
    system_id: str
    customer_id: str | None
    database_or_index: str


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class QueryShape:
    name: str
    share: float
    primitives: list[str]
    responses: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class Scenario:
    name: str
    seed: int
    target: Target
    time_range: TimeRange
    events: int
    responses: dict[str, dict[str, Any]]
    query_shapes: list[QueryShape]
    raw_payload: dict[str, Any]


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ScenarioValidationError(f"{field} must be an ISO timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScenarioValidationError(f"{field} is not a valid ISO timestamp") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ScenarioValidationError(f"{key} must be a mapping")
    return value


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ScenarioValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _validate_distribution(metric: str, spec: Any, *, required: bool) -> dict[str, Any] | None:
    if spec is None:
        if required:
            raise ScenarioValidationError(f"responses.{metric} is required")
        return None
    if not isinstance(spec, dict):
        raise ScenarioValidationError(f"responses.{metric} must be a mapping")
    distributions = response_distributions()
    distribution = spec.get("distribution")
    if distribution not in distributions:
        supported = ", ".join(distributions)
        raise ScenarioValidationError(f"responses.{metric}.distribution must be one of {supported}")
    required_fields = [
        str(field["name"])
        for field in distributions[str(distribution)].get("fields") or []
    ]
    missing = [name for name in required_fields if name not in spec]
    if missing:
        raise ScenarioValidationError(
            f"responses.{metric}.{', '.join(missing)} required for {distribution} distribution"
        )
    if "stddev" in spec and float(spec["stddev"]) < 0:
        raise ScenarioValidationError(f"responses.{metric}.stddev must be >= 0")
    if "min" in spec and "max" in spec and float(spec["min"]) > float(spec["max"]):
        raise ScenarioValidationError(f"responses.{metric}.min must be <= max")
    return dict(spec)


def _validate_responses(payload: dict[str, Any], *, required: bool) -> dict[str, dict[str, Any]]:
    responses: dict[str, dict[str, Any]] = {}
    for metric in REQUIRED_RESPONSE_METRICS:
        validated = _validate_distribution(metric, payload.get(metric), required=required)
        if validated is not None:
            responses[metric] = validated
    unexpected = set(payload) - set(REQUIRED_RESPONSE_METRICS)
    if unexpected:
        raise ScenarioValidationError(f"unsupported response metrics: {sorted(unexpected)}")
    return responses


def scenario_from_payload(payload: dict[str, Any]) -> Scenario:
    if not isinstance(payload, dict):
        raise ScenarioValidationError("scenario must be a mapping")

    name = _require_string(payload, "name")
    seed = int(payload.get("seed", 0))
    events = int(payload.get("events", 0))
    if events <= 0:
        raise ScenarioValidationError("events must be a positive integer")

    target_payload = _require_mapping(payload, "target")
    platform = _require_string(target_payload, "platform")
    if platform not in platform_names():
        raise ScenarioValidationError(f"target.platform must be one of {platform_names()}")
    target = Target(
        platform=platform,
        system_id=_require_string(target_payload, "system_id"),
        customer_id=target_payload.get("customer_id"),
        database_or_index=_require_string(target_payload, "database_or_index"),
    )

    time_payload = _require_mapping(payload, "time_range")
    time_range = TimeRange(
        start=parse_timestamp(time_payload.get("start"), "time_range.start"),
        end=parse_timestamp(time_payload.get("end"), "time_range.end"),
    )
    if time_range.end <= time_range.start:
        raise ScenarioValidationError("time_range.end must be after time_range.start")

    responses = _validate_responses(_require_mapping(payload, "responses"), required=True)

    shapes_payload = payload.get("query_shapes")
    if not isinstance(shapes_payload, list) or not shapes_payload:
        raise ScenarioValidationError("query_shapes must be a non-empty list")
    query_shapes: list[QueryShape] = []
    total_share = 0.0
    for index, shape_payload in enumerate(shapes_payload):
        if not isinstance(shape_payload, dict):
            raise ScenarioValidationError(f"query_shapes[{index}] must be a mapping")
        shape_name = _require_string(shape_payload, "name")
        share = float(shape_payload.get("share", 0))
        if share <= 0:
            raise ScenarioValidationError(f"query_shapes[{index}].share must be positive")
        primitives = shape_payload.get("primitives")
        if not isinstance(primitives, list) or not primitives:
            raise ScenarioValidationError(f"query_shapes[{index}].primitives must be a non-empty list")
        normalized_primitives = [str(primitive) for primitive in primitives]
        reasons = unsupported_reasons(platform, normalized_primitives)
        if reasons:
            raise ScenarioValidationError(f"{shape_name} uses unsupported primitives: {'; '.join(reasons)}")
        shape_responses = _validate_responses(shape_payload.get("responses") or {}, required=False)
        query_shapes.append(
            QueryShape(
                name=shape_name,
                share=share,
                primitives=normalized_primitives,
                responses=shape_responses,
            )
        )
        total_share += share

    if abs(total_share - 100.0) > 0.001:
        raise ScenarioValidationError(f"query shape shares must sum to 100, got {total_share:g}")

    return Scenario(
        name=name,
        seed=seed,
        target=target,
        time_range=time_range,
        events=events,
        responses=responses,
        query_shapes=query_shapes,
        raw_payload=dict(payload),
    )


def load_scenario(path: Path) -> Scenario:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    return scenario_from_payload(loaded or {})


def scenario_from_text(text: str) -> Scenario:
    return scenario_from_payload(yaml.safe_load(text) or {})
