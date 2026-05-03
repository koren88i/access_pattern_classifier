from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from workload_intelligence.exporters.elastic import (
    DEFAULT_KIBANA_URL,
    INDEX_AGGREGATE_WINDOWS,
    INDEX_LINEAGE_EVENTS,
    INDEX_LINEAGE_RECOMMENDATIONS,
    INDEX_LINEAGE_TEMPLATES,
    INDEX_LINEAGE_VALIDATION,
    INDEX_PRIMITIVE_EVENTS,
    INDEX_PRIMITIVE_SIGNALS,
    INDEX_PROFILES,
    INDEX_RECOMMENDATIONS,
    INDEX_SIM_RUNS,
    ElasticExportError,
)


DATA_VIEWS = {
    INDEX_SIM_RUNS: None,
    INDEX_PRIMITIVE_EVENTS: "timestamp",
    INDEX_PRIMITIVE_SIGNALS: "timestamp",
    INDEX_AGGREGATE_WINDOWS: "window_start",
    INDEX_PROFILES: "window_start",
    INDEX_RECOMMENDATIONS: "window_start",
    INDEX_LINEAGE_RECOMMENDATIONS: "window_start",
    INDEX_LINEAGE_TEMPLATES: None,
    INDEX_LINEAGE_EVENTS: "timestamp",
    INDEX_LINEAGE_VALIDATION: None,
}

DASHBOARD_ID = "workload-intelligence-lineage-dashboard"
DASHBOARD_TITLE = "Workload Intelligence Lineage"
RUN_CONTROL_ID = "lineage-run-selector"
EVENT_CONTROL_ID = "lineage-event-id-lookup"
TEMPLATE_CONTROL_ID = "lineage-template-id-selector"

SAVED_SEARCHES = {
    "workload-lineage-event-lookup": {
        "title": "WI Lineage - Event Lookup",
        "data_view": INDEX_LINEAGE_EVENTS,
        "columns": [
            "event_id",
            "run_id",
            "timestamp",
            "normalized_query_text",
            "raw_query_text",
            "matched_primitives",
            "template_id",
            "profile_id",
            "recommendation_ids",
            "aggregate_window_ids",
            "latency_ms",
            "response_bytes",
            "result_count",
        ],
        "sort": [["timestamp", "asc"]],
    },
    "workload-lineage-recommendation-backtrace": {
        "title": "WI Lineage - Recommendation Backtrace",
        "data_view": INDEX_LINEAGE_RECOMMENDATIONS,
        "columns": [
            "scenario_name",
            "system_id",
            "platform",
            "matched_rule_id",
            "recommendation",
            "severity",
            "confidence",
            "rule_condition_summary",
            "source_numbers",
            "top_template_ids",
            "sample_event_ids",
        ],
        "sort": [["window_start", "desc"]],
    },
    "workload-lineage-template-evidence": {
        "title": "WI Lineage - Template Evidence",
        "data_view": INDEX_LINEAGE_TEMPLATES,
        "columns": [
            "scenario_name",
            "template_id",
            "request_count",
            "contribution",
            "matched_primitives",
            "matched_rule_ids",
            "normalized_query_text",
            "sample_event_ids",
            "raw_query_samples",
        ],
        "sort": [],
    },
    "workload-lineage-event-forward-trace": {
        "title": "WI Lineage - Event Forward Trace",
        "data_view": INDEX_LINEAGE_EVENTS,
        "columns": [
            "scenario_name",
            "event_id",
            "template_id",
            "matched_primitives",
            "aggregate_window_ids",
            "profile_id",
            "recommendation_ids",
            "normalized_query_text",
            "raw_query_text",
        ],
        "sort": [["timestamp", "asc"]],
    },
    "workload-lineage-validation-check": {
        "title": "WI Lineage - Expected vs Observed",
        "data_view": INDEX_LINEAGE_VALIDATION,
        "columns": [
            "scenario_name",
            "validation_status",
            "expected_primitive_share",
            "observed_primitive_share",
            "observed_primitive_profile",
            "observed_access_pattern_scores",
            "recommendation_ids",
        ],
        "sort": [],
    },
}


def _request_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "kbn-xsrf": "workload-intelligence",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ElasticExportError(f"Kibana data-view setup failed at {url}: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        raise ElasticExportError(f"Could not connect to Kibana at {url}: {exc}") from exc


def _get_json(url: str) -> dict[str, Any]:
    request = Request(url, method="GET", headers={"kbn-xsrf": "workload-intelligence"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ElasticExportError(f"Kibana request failed at {url}: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        raise ElasticExportError(f"Could not connect to Kibana at {url}: {exc}") from exc


def _post_saved_object(
    kibana_url: str,
    object_type: str,
    object_id: str,
    attributes: dict[str, Any],
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    base = kibana_url.rstrip("/")
    return _request_json(
        f"{base}/api/saved_objects/{object_type}/{object_id}?overwrite=true",
        {"attributes": attributes, "references": references},
    )


def _data_view_ids(kibana_url: str) -> dict[str, str]:
    base = kibana_url.rstrip("/")
    response = _get_json(f"{base}/api/data_views")
    return {item["title"]: item["id"] for item in response.get("data_view", [])}


def _search_source(data_view_ref_name: str, query: str = "") -> str:
    return json.dumps(
        {
            "query": {"query": query, "language": "kuery"},
            "filter": [],
            "indexRefName": data_view_ref_name,
        },
        separators=(",", ":"),
    )


def _dashboard_search_source() -> str:
    return json.dumps(
        {"query": {"query": "", "language": "kuery"}, "filter": []},
        separators=(",", ":"),
    )


def _dashboard_controls(data_view_id: str) -> dict[str, Any]:
    controls = {
        RUN_CONTROL_ID: {
            "grow": True,
            "order": 0,
            "type": "optionsListControl",
            "width": "large",
            "explicitInput": {
                "id": RUN_CONTROL_ID,
                "dataViewId": data_view_id,
                "fieldName": "run_id",
                "title": "Run",
                "searchTechnique": "prefix",
                "selectedOptions": [],
                "sort": {"by": "_key", "direction": "desc"},
                "exclude": False,
            },
        },
        EVENT_CONTROL_ID: {
            "grow": True,
            "order": 1,
            "type": "optionsListControl",
            "width": "large",
            "explicitInput": {
                "id": EVENT_CONTROL_ID,
                "dataViewId": data_view_id,
                "fieldName": "event_id",
                "title": "Event ID",
                "searchTechnique": "prefix",
                "selectedOptions": [],
                "sort": {"by": "_key", "direction": "asc"},
                "exclude": False,
            },
        },
        TEMPLATE_CONTROL_ID: {
            "grow": True,
            "order": 2,
            "type": "optionsListControl",
            "width": "large",
            "explicitInput": {
                "id": TEMPLATE_CONTROL_ID,
                "dataViewId": data_view_id,
                "fieldName": "template_id",
                "title": "Template ID",
                "searchTechnique": "prefix",
                "selectedOptions": [],
                "sort": {"by": "_count", "direction": "desc"},
                "exclude": False,
            },
        },
    }
    return {
        "chainingSystem": "HIERARCHICAL",
        "controlStyle": "oneLine",
        "ignoreParentSettingsJSON": json.dumps(
            {
                "ignoreFilters": False,
                "ignoreQuery": False,
                "ignoreTimerange": False,
                "ignoreValidations": False,
            },
            separators=(",", ":"),
        ),
        "panelsJSON": json.dumps(controls, separators=(",", ":")),
        "showApplySelections": False,
    }


def setup_saved_searches(kibana_url: str = DEFAULT_KIBANA_URL) -> list[str]:
    setup_data_views(kibana_url)
    data_view_ids = _data_view_ids(kibana_url)
    created = []
    for search_id, spec in SAVED_SEARCHES.items():
        data_view_title = spec["data_view"]
        if data_view_title not in data_view_ids:
            raise ElasticExportError(f"Kibana data view {data_view_title!r} was not found")
        ref_name = "kibanaSavedObjectMeta.searchSourceJSON.index"
        attributes = {
            "title": spec["title"],
            "description": "Generated by workload-intelligence lineage setup.",
            "columns": spec["columns"],
            "sort": spec["sort"],
            "kibanaSavedObjectMeta": {"searchSourceJSON": _search_source(ref_name)},
        }
        references = [{"name": ref_name, "type": "index-pattern", "id": data_view_ids[data_view_title]}]
        _post_saved_object(kibana_url, "search", search_id, attributes, references)
        created.append(search_id)
    return created


def setup_lineage_dashboard(kibana_url: str = DEFAULT_KIBANA_URL) -> dict[str, Any]:
    search_ids = setup_saved_searches(kibana_url)
    data_view_ids = _data_view_ids(kibana_url)
    lineage_events_data_view_id = data_view_ids.get(INDEX_LINEAGE_EVENTS)
    if not lineage_events_data_view_id:
        raise ElasticExportError(f"Kibana data view {INDEX_LINEAGE_EVENTS!r} was not found")
    panels = []
    references = []
    layouts = [
        ("workload-lineage-event-lookup", 0, 0, 48, 10),
        ("workload-lineage-recommendation-backtrace", 0, 10, 48, 12),
        ("workload-lineage-template-evidence", 0, 22, 48, 12),
        ("workload-lineage-event-forward-trace", 0, 34, 48, 12),
        ("workload-lineage-validation-check", 0, 46, 48, 10),
    ]
    for index, (search_id, x, y, width, height) in enumerate(layouts, start=1):
        panel_index = str(index)
        ref_name = f"panel_{panel_index}"
        panels.append(
            {
                "panelIndex": panel_index,
                "type": "search",
                "panelRefName": ref_name,
                "gridData": {"x": x, "y": y, "w": width, "h": height, "i": panel_index},
                "embeddableConfig": {},
            }
        )
        references.append({"name": ref_name, "type": "search", "id": search_id})

    references.extend(
        [
            {
                "name": f"controlGroup_{RUN_CONTROL_ID}:optionsListDataView",
                "type": "index-pattern",
                "id": lineage_events_data_view_id,
            },
            {
                "name": f"controlGroup_{EVENT_CONTROL_ID}:optionsListDataView",
                "type": "index-pattern",
                "id": lineage_events_data_view_id,
            },
            {
                "name": f"controlGroup_{TEMPLATE_CONTROL_ID}:optionsListDataView",
                "type": "index-pattern",
                "id": lineage_events_data_view_id,
            },
        ]
    )

    attributes = {
        "title": DASHBOARD_TITLE,
        "description": (
            "Lineage workflow: recommendation backtrace, template evidence, event forward trace, "
            "and simulator expected-vs-observed validation."
        ),
        "hits": 0,
        "panelsJSON": json.dumps(panels, separators=(",", ":")),
        "optionsJSON": json.dumps(
            {
                "useMargins": True,
                "syncColors": False,
                "syncCursor": True,
                "syncTooltips": True,
                "hidePanelTitles": False,
            },
            separators=(",", ":"),
        ),
        "timeRestore": True,
        "timeFrom": "now-7d",
        "timeTo": "now",
        "refreshInterval": {"pause": True, "value": 0},
        "controlGroupInput": _dashboard_controls(lineage_events_data_view_id),
        "kibanaSavedObjectMeta": {"searchSourceJSON": _dashboard_search_source()},
    }
    _post_saved_object(kibana_url, "dashboard", DASHBOARD_ID, attributes, references)
    return {
        "dashboard_id": DASHBOARD_ID,
        "title": DASHBOARD_TITLE,
        "saved_searches": search_ids,
        "url": f"{kibana_url.rstrip('/')}/app/dashboards#/view/{DASHBOARD_ID}",
    }


def setup_data_views(kibana_url: str = DEFAULT_KIBANA_URL) -> list[str]:
    created = []
    base = kibana_url.rstrip("/")
    for title, time_field in DATA_VIEWS.items():
        data_view: dict[str, Any] = {"title": title, "name": title}
        if time_field:
            data_view["timeFieldName"] = time_field
        _request_json(f"{base}/api/data_views/data_view", {"data_view": data_view, "override": True})
        created.append(title)
    return created
