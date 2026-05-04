from __future__ import annotations

import hashlib
import json
from typing import Any

from workload_intelligence.patterns.scorer import score_access_patterns
from workload_intelligence.recommendations.recommendation_engine import recommend_for_profile


PROFILE_SCOPE_KEYS = (
    "system_id",
    "customer_id",
    "platform",
    "database_or_index",
    "window_start",
    "window_end",
)


def _profile_id(scope: dict[str, Any]) -> str:
    raw = json.dumps(
        {key: scope.get(key) for key in PROFILE_SCOPE_KEYS},
        sort_keys=True,
        default=str,
    )
    return "prof-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _scope_from_window(window: dict[str, Any]) -> dict[str, Any]:
    key = window["key"]
    return {
        scope_key: key[scope_key]
        for scope_key in PROFILE_SCOPE_KEYS
        if scope_key in key
    }


def _dominant_patterns(scores: dict[str, float]) -> list[dict[str, Any]]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        {
            "pattern": pattern,
            "score": score,
            "confidence": round(min(1.0, score + 0.1), 4),
        }
        for pattern, score in ordered
        if score >= 0.2
    ][:3]


def _explanation(window: dict[str, Any], scores: dict[str, float]) -> list[str]:
    primitive_profile = window["primitive_profile"]
    strongest = sorted(primitive_profile.items(), key=lambda item: item[1], reverse=True)[:4]
    lines = [
        f"{int(value * 100)}% {name} signal across requests"
        for name, value in strongest
        if value > 0
    ]
    coverage = window["template_metrics"]["top_templates_coverage"]
    lines.append(f"Top templates cover {int(coverage * 100)}% of traffic")
    dominant = max(scores.items(), key=lambda item: item[1])
    lines.append(f"Highest access-pattern score is {dominant[0]} at {dominant[1]:.2f}")
    return lines


def build_profiles(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for window in windows:
        scope = _scope_from_window(window)
        pattern_scores = score_access_patterns(window)
        profile = {
            "profile_id": _profile_id(scope),
            "aggregate_window_id": window.get("aggregate_window_id"),
            "scope": scope,
            "volume": {
                **window["volume_metrics"],
                "top_templates_coverage": window["template_metrics"]["top_templates_coverage"],
            },
            "latency": window["latency_metrics"],
            "primitive_profile": window["primitive_profile"],
            "primitive_profiles": window.get("primitive_profiles", {"request_count": window["primitive_profile"]}),
            "access_pattern_scores": pattern_scores,
            "dominant_patterns": _dominant_patterns(pattern_scores),
            "evidence": {
                "top_templates": window["top_templates"],
                "explanation": _explanation(window, pattern_scores),
            },
        }
        profile["recommendations"] = recommend_for_profile(profile)
        profiles.append(profile)
    return profiles
