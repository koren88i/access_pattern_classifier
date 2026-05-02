from __future__ import annotations

import random
from typing import Any

from workload_intelligence.simulator.scenario import QueryShape, Scenario


def sample_distribution(spec: dict[str, Any], rng: random.Random) -> int:
    distribution = spec["distribution"]
    if distribution == "fixed":
        value = float(spec["value"])
    elif distribution == "uniform":
        value = rng.uniform(float(spec["min"]), float(spec["max"]))
    elif distribution == "normal":
        value = rng.gauss(float(spec["mean"]), float(spec["stddev"]))
        value = max(float(spec["min"]), min(float(spec["max"]), value))
    else:
        raise ValueError(f"unsupported distribution: {distribution!r}")
    return max(0, int(round(value)))


def sample_response_metadata(
    scenario: Scenario,
    shape: QueryShape,
    rng: random.Random,
) -> dict[str, int]:
    merged = {**scenario.responses, **shape.responses}
    response = {
        "status_code": 200,
        "latency_ms": sample_distribution(merged["latency_ms"], rng),
        "response_bytes": sample_distribution(merged["response_bytes"], rng),
        "result_count": sample_distribution(merged["result_count"], rng),
    }
    return response


def shape_counts(scenario: Scenario) -> list[tuple[QueryShape, int]]:
    fractional: list[tuple[float, int, QueryShape, int]] = []
    allocated = 0
    for index, shape in enumerate(scenario.query_shapes):
        exact = scenario.events * shape.share / 100.0
        count = int(exact)
        allocated += count
        fractional.append((exact - count, index, shape, count))

    remaining = scenario.events - allocated
    by_fraction = sorted(fractional, key=lambda item: (-item[0], item[1]))
    extra_indexes = {item[1] for item in by_fraction[:remaining]}
    return [
        (shape, count + (1 if index in extra_indexes else 0))
        for _fraction, index, shape, count in fractional
    ]
