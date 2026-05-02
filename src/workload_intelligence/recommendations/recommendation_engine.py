from __future__ import annotations

import hashlib
import operator
from typing import Any, Callable

from workload_intelligence.specs import load_spec


OPS: dict[str, Callable[[float, float], bool]] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
}


def _get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _matches_expected(actual: Any, expected: Any) -> bool:
    if isinstance(expected, str):
        for prefix, op in OPS.items():
            marker = prefix + " "
            if expected.startswith(marker):
                return actual is not None and op(float(actual), float(expected[len(marker) :]))
    return actual == expected


def _condition_detail(path: str, actual: Any, expected: Any) -> dict[str, Any]:
    if isinstance(expected, str):
        for prefix, op in OPS.items():
            marker = prefix + " "
            if expected.startswith(marker):
                threshold = float(expected[len(marker) :])
                passed = actual is not None and op(float(actual), threshold)
                return {
                    "path": path,
                    "operator": prefix,
                    "threshold": str(threshold),
                    "threshold_number": threshold,
                    "observed_value": actual,
                    "observed_number": actual if isinstance(actual, (int, float)) else None,
                    "passed": passed,
                }
    return {
        "path": path,
        "operator": "==",
        "threshold": str(expected),
        "observed_value": actual,
        "observed_number": actual if isinstance(actual, (int, float)) else None,
        "passed": actual == expected,
    }


def _rule_condition_details(profile: dict[str, Any], rule: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _condition_detail(path, _get_path(profile, path), expected)
        for path, expected in rule["when"].items()
    ]


def _rule_matches(profile: dict[str, Any], rule: dict[str, Any]) -> bool:
    return all(detail["passed"] for detail in _rule_condition_details(profile, rule))


def _recommendation_id(profile: dict[str, Any], rule_id: str, index: int) -> str:
    raw = "|".join([str(profile.get("profile_id")), rule_id, str(index)])
    return "rec-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def recommend_for_profile(
    profile: dict[str, Any],
    rules_spec: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rules_spec = rules_spec or load_spec("recommendation-rules.yaml")
    recommendations = []
    for rule in rules_spec.get("rules", []):
        condition_details = _rule_condition_details(profile, rule)
        if all(detail["passed"] for detail in condition_details):
            then = rule["then"]
            index = len(recommendations)
            recommendations.append(
                {
                    "recommendation_id": _recommendation_id(profile, str(rule["id"]), index),
                    "type": then["type"],
                    "recommendation": then["recommendation"],
                    "target_technology": then.get("target_technology"),
                    "severity": then["severity"],
                    "confidence": then.get("confidence", 0.6),
                    "matched_rule_id": rule["id"],
                    "rule_conditions": condition_details,
                    "evidence": then.get("evidence", []),
                }
            )
    if recommendations:
        return recommendations
    return [
        {
            "recommendation_id": _recommendation_id(profile, "default_no_action", 0),
            "type": "no_action",
            "recommendation": "No architecture review rule matched",
            "target_technology": None,
            "severity": "low",
            "confidence": 0.5,
            "matched_rule_id": "default_no_action",
            "rule_conditions": [],
            "evidence": ["No recommendation threshold was crossed"],
        }
    ]
