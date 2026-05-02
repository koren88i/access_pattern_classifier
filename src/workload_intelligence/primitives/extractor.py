from __future__ import annotations

from collections import defaultdict
from typing import Any

from workload_intelligence.primitives.rule_engine import PrimitiveSignal, empty_signal, rule_matches
from workload_intelligence.specs import load_spec


def primitive_names() -> list[str]:
    ontology = load_spec("primitive-ontology.yaml")["PrimitiveIntent"]
    names: list[str] = []
    for group in ontology.values():
        names.extend(group)
    return names


def extract_primitives(
    normalized_event: dict[str, Any],
    rules_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rules_spec = rules_spec or load_spec("primitive-rules.yaml")
    collected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rule in rules_spec.get("rules", []):
        if rule_matches(normalized_event, rule):
            collected[rule["primitive"]].append(rule)

    signals: dict[str, PrimitiveSignal] = {name: empty_signal() for name in primitive_names()}
    for primitive, matches in collected.items():
        best_signal_weight = max(float(rule.get("signal_weight", 0.0)) for rule in matches)
        best_rule_confidence = max(float(rule.get("rule_confidence", 0.0)) for rule in matches)
        signals[primitive] = PrimitiveSignal(
            matched=True,
            signal_weight=best_signal_weight,
            rule_confidence=best_rule_confidence,
            evidence=[str(rule["evidence"]) for rule in matches],
            rule_ids=[str(rule["id"]) for rule in matches],
        )

    return {
        "event_id": normalized_event["event_id"],
        "platform": normalized_event["platform"]["type"],
        "system_id": normalized_event["identity"]["system_id"],
        "customer_id": normalized_event["identity"].get("customer_id"),
        "database_or_index": (
            normalized_event["platform"].get("index_or_table")
            or normalized_event["platform"].get("database")
        ),
        "timestamp": normalized_event["timestamp"],
        "template_id": normalized_event["template_id"],
        "latency_ms": normalized_event["response"]["latency_ms"],
        "response_bytes": normalized_event["response"].get("response_bytes"),
        "result_count": normalized_event["response"].get("result_count"),
        "primitive_signals": {
            name: {
                "matched": signal.matched,
                "signal_weight": signal.signal_weight,
                "rule_confidence": signal.rule_confidence,
                "evidence": signal.evidence,
                "rule_ids": signal.rule_ids,
            }
            for name, signal in signals.items()
        },
    }
