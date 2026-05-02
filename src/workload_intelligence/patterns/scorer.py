from __future__ import annotations

from typing import Any

from workload_intelligence.specs import load_spec


def _feature_value(window: dict[str, Any], name: str) -> float:
    primitive_profile = window["primitive_profile"]
    volume = window["volume_metrics"]
    latency = window["latency_metrics"]
    templates = window["template_metrics"]
    data = window["data_metrics"]

    if name in primitive_profile:
        return float(primitive_profile[name])
    if name == "template_stability":
        return float(templates["template_stability"])
    if name == "low_template_stability":
        return 1.0 - float(templates["template_stability"])
    if name == "request_rate":
        return min(1.0, float(volume["request_count"]) / 1000.0)
    if name == "p95_latency_pressure":
        return min(1.0, float(latency["p95_latency_ms"]) / 1000.0)
    if name == "low_latency":
        return max(0.0, 1.0 - float(latency["p95_latency_ms"]) / 100.0)
    if name == "large_payload":
        avg_bytes = data.get("avg_response_bytes") or 0.0
        return min(1.0, float(avg_bytes) / 1_000_000.0)
    if name == "ttl_or_expire_usage":
        return float(primitive_profile.get("ttl_or_expire_usage", 0.0))
    return 0.0


def score_access_patterns(
    window: dict[str, Any],
    rules_spec: dict[str, Any] | None = None,
) -> dict[str, float]:
    rules_spec = rules_spec or load_spec("pattern-rules.yaml")
    scores: dict[str, float] = {}
    for pattern, rule in rules_spec.get("pattern_rules", {}).items():
        total = 0.0
        for feature, weight in (rule.get("score") or {}).items():
            total += _feature_value(window, feature) * float(weight)
        for feature, penalty in (rule.get("penalties") or {}).items():
            total += _feature_value(window, feature) * float(penalty)
        scores[pattern] = round(max(0.0, min(1.0, total)), 4)

    best_known = max(scores.values(), default=0.0)
    scores["unknown_mixed"] = round(max(0.0, min(1.0, 0.6 - best_known)), 4)
    return scores

