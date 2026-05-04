from __future__ import annotations

from typing import Any


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    rendered = ["  ".join(value.ljust(widths[index]) for index, value in enumerate(headers))]
    rendered.append("  ".join("-" * width for width in widths))
    rendered.extend("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in rows)
    return "\n".join(rendered)


def _top_primitives(profile: dict[str, float], limit: int = 3) -> str:
    ranked = sorted(profile.items(), key=lambda item: item[1], reverse=True)
    return ", ".join(
        f"{primitive}:{score:.2f}"
        for primitive, score in ranked[:limit]
        if score > 0
    ) or "none"


def render_dashboard_rows(profiles: list[dict[str, Any]]) -> str:
    headers = ["System", "Customer", "Platform", "Database/Index", "Dominant Pattern", "Score", "Recommendation"]
    rows = []
    for profile in profiles:
        dominant = profile["dominant_patterns"][0] if profile["dominant_patterns"] else {}
        recommendation = profile["recommendations"][0]
        scope = profile["scope"]
        rows.append(
            [
                scope["system_id"],
                scope.get("customer_id", ""),
                scope["platform"],
                scope.get("database_or_index", ""),
                dominant.get("pattern", "unknown_mixed"),
                f"{dominant.get('score', 0.0):.2f}",
                recommendation["recommendation"],
            ]
        )
    return _render_table(headers, rows)


def render_platform_market_analysis(platform_windows: list[dict[str, Any]]) -> str:
    headers = ["Platform", "Requests", "Systems", "Customers", "By Count", "By Systems"]
    rows = []
    for window in platform_windows:
        volume = window["volume_metrics"]
        rows.append(
            [
                window["key"]["platform"],
                str(volume["request_count"]),
                str(volume["unique_system_count"]),
                str(volume["unique_customer_count"]),
                _top_primitives(window["primitive_profiles"]["request_count"]),
                _top_primitives(window["primitive_profiles"]["unique_systems"]),
            ]
        )
    return _render_table(headers, rows)


def render_top_templates_by_system(system_windows: list[dict[str, Any]]) -> str:
    headers = ["System", "Platform", "Template", "Requests", "Share", "Top Primitives"]
    rows = []
    for window in system_windows:
        for template in window["top_templates"]:
            rows.append(
                [
                    window["key"]["system_id"],
                    window["key"]["platform"],
                    template["template_id"],
                    str(template["request_count"]),
                    f"{template['contribution']:.2f}",
                    _top_primitives(template["primitive_summary"]),
                ]
            )
    return _render_table(headers, rows)


def render_primitive_weight_comparison(
    windows: list[dict[str, Any]],
    modes: tuple[str, ...] = ("request_count", "latency_cost"),
) -> str:
    headers = ["View", "Scope", "Platform", "Mode", "Top Primitives"]
    rows = []
    for window in windows:
        key = window["key"]
        scope = key.get("system_id") or key.get("customer_id") or key.get("template_id") or key["platform"]
        for mode in modes:
            rows.append(
                [
                    key["aggregation_view"],
                    scope,
                    key["platform"],
                    mode,
                    _top_primitives(window["primitive_profiles"][mode]),
                ]
            )
    return _render_table(headers, rows)
