from __future__ import annotations

from typing import Any

from workload_intelligence.simulator.sampling import shape_counts
from workload_intelligence.simulator.scenario import Scenario
from workload_intelligence.specs import load_spec


def _threshold_match_share(distribution: dict[str, Any], threshold: float) -> float:
    kind = distribution.get("distribution")
    if kind == "fixed":
        return 1.0 if float(distribution["value"]) >= threshold else 0.0
    if kind == "uniform":
        minimum = float(distribution["min"])
        maximum = float(distribution["max"])
        if maximum < threshold:
            return 0.0
        if minimum >= threshold:
            return 1.0
        if maximum == minimum:
            return 0.0
        return (maximum - threshold) / (maximum - minimum)
    if kind == "normal":
        minimum = float(distribution["min"])
        maximum = float(distribution["max"])
        mean = float(distribution["mean"])
        if maximum < threshold:
            return 0.0
        if minimum >= threshold:
            return 1.0
        return 1.0 if mean >= threshold else 0.5
    return 0.0


def _response_derived_primitive_share(scenario: Scenario) -> dict[str, float]:
    rules = load_spec("primitive-rules.yaml")["rules"]
    expected: dict[str, float] = {}
    for shape, count in shape_counts(scenario):
        merged_responses = {**scenario.responses, **shape.responses}
        result_count_distribution = merged_responses.get("result_count")
        if not result_count_distribution:
            continue
        contribution = count / scenario.events
        for rule in rules:
            if rule.get("platform") != scenario.target.platform:
                continue
            conditions = rule.get("when") or {}
            if "result_count_gte" not in conditions:
                continue
            primitive = str(rule["primitive"])
            match_share = _threshold_match_share(result_count_distribution, float(conditions["result_count_gte"]))
            if match_share > 0:
                expected[primitive] = expected.get(primitive, 0.0) + (contribution * match_share)
    return expected


def expected_primitive_share(scenario: Scenario) -> dict[str, float]:
    expected: dict[str, float] = {}
    for shape, count in shape_counts(scenario):
        contribution = count / scenario.events
        for primitive in shape.primitives:
            expected[primitive] = expected.get(primitive, 0.0) + contribution
    for primitive, share in _response_derived_primitive_share(scenario).items():
        expected[primitive] = max(expected.get(primitive, 0.0), share)
    return {primitive: round(value, 4) for primitive, value in sorted(expected.items())}


def validate_report(scenario: Scenario, report: dict[str, Any]) -> dict[str, Any]:
    profiles = report.get("profiles") or []
    profile = profiles[0] if profiles else {}
    observed = profile.get("primitive_profile") or {}
    expected = expected_primitive_share(scenario)
    warnings = []

    for primitive, expected_share in expected.items():
        observed_score = float(observed.get(primitive, 0.0))
        if observed_score < expected_share * 0.30:
            warnings.append(
                {
                    "kind": "primitive_under_detected",
                    "primitive": primitive,
                    "expected_share": expected_share,
                    "observed_score": round(observed_score, 4),
                }
            )

    for primitive, observed_score in sorted(observed.items()):
        if primitive not in expected and float(observed_score) > 0.20:
            warnings.append(
                {
                    "kind": "unexpected_primitive_detected",
                    "primitive": primitive,
                    "expected_share": 0.0,
                    "observed_score": round(float(observed_score), 4),
                }
            )

    return {
        "status": "warning" if warnings else "ok",
        "warnings": warnings,
        "expected_primitive_share": expected,
        "observed_primitive_profile": observed,
        "observed_access_pattern_scores": profile.get("access_pattern_scores") or {},
        "dominant_patterns": profile.get("dominant_patterns") or [],
        "recommendations": profile.get("recommendations") or [],
    }
