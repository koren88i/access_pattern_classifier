from __future__ import annotations

from typing import Any

from workload_intelligence.specs import load_spec

RESPONSE_METADATA_CONDITIONS = {
    "latency_ms_gte",
    "latency_ms_lte",
    "response_bytes_gte",
    "response_bytes_lte",
    "result_count_gte",
    "result_count_lte",
}


def primitive_names() -> list[str]:
    ontology = load_spec("primitive-ontology.yaml")["PrimitiveIntent"]
    names: list[str] = []
    for group in ontology.values():
        names.extend(group)
    return names


def primitive_descriptions() -> dict[str, str]:
    return load_spec("primitive-ontology.yaml").get("PrimitiveDescriptions", {})


def load_capabilities() -> dict[str, Any]:
    return load_spec("simulator-capabilities.yaml")


def response_metadata_capability() -> dict[str, Any]:
    return load_capabilities().get("response_metadata", {})


def response_distributions() -> dict[str, dict[str, Any]]:
    distributions = response_metadata_capability().get("distributions") or []
    return {str(distribution["name"]): distribution for distribution in distributions}


def platform_names() -> list[str]:
    return sorted(load_capabilities().get("platforms", {}).keys())


def platform_capability(platform: str) -> dict[str, Any]:
    capabilities = load_capabilities().get("platforms", {})
    if platform not in capabilities:
        raise ValueError(f"unsupported simulator platform: {platform!r}")
    return capabilities[platform]


def unsupported_reasons(platform: str, primitives: list[str]) -> list[str]:
    capability = platform_capability(platform)
    supported = set(capability.get("supported_primitives") or [])
    unsupported = capability.get("unsupported_primitives") or {}
    reasons = []
    for primitive in primitives:
        if primitive not in primitive_names():
            reasons.append(f"unknown primitive {primitive!r}")
        elif primitive not in supported:
            reasons.append(str(unsupported.get(primitive) or f"{primitive} is not supported for {platform}"))

    requested = set(primitives)
    for combination in capability.get("unsupported_combinations") or []:
        combo = set(combination.get("primitives") or [])
        if combo and combo.issubset(requested):
            reasons.append(str(combination.get("reason") or f"unsupported primitive combination: {sorted(combo)}"))
    return reasons


def _response_derived_primitives_by_platform() -> dict[str, set[str]]:
    derived: dict[str, set[str]] = {}
    for rule in load_spec("primitive-rules.yaml")["rules"]:
        conditions = set((rule.get("when") or {}).keys())
        if not conditions.intersection(RESPONSE_METADATA_CONDITIONS):
            continue
        platform = str(rule["platform"])
        derived.setdefault(platform, set()).add(str(rule["primitive"]))
    return derived


def capability_payload() -> dict[str, Any]:
    names = primitive_names()
    descriptions = primitive_descriptions()
    platforms: dict[str, Any] = {}
    response_metadata = response_metadata_capability()
    response_derived_by_platform = _response_derived_primitives_by_platform()
    for platform, capability in load_capabilities().get("platforms", {}).items():
        supported = set(capability.get("supported_primitives") or [])
        unsupported = capability.get("unsupported_primitives") or {}
        response_derived = set(capability.get("response_derived_primitives") or [])
        response_derived.update(response_derived_by_platform.get(platform, set()))
        response_only = response_derived - supported
        platforms[platform] = {
            "display_name": capability.get("display_name", platform),
            "supported_primitives": sorted(supported),
            "primitives": [
                {
                    "name": primitive,
                    "description": descriptions[primitive],
                    "supported": primitive in supported,
                    "reason": None if primitive in supported else unsupported.get(primitive, "Not supported yet."),
                }
                for primitive in names
                if primitive not in response_only
            ],
            "response_derived_primitives": [
                {
                    "name": primitive,
                    "description": descriptions[primitive],
                    "reason": unsupported.get(
                        primitive,
                        "Detected from response metadata distributions, not generated query syntax.",
                    ),
                }
                for primitive in sorted(response_only)
            ],
            "unsupported_combinations": capability.get("unsupported_combinations") or [],
        }
    return {"platforms": platforms, "primitive_names": names, "response_metadata": response_metadata}
