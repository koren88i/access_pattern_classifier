from __future__ import annotations

from pathlib import Path
from typing import Any

from workload_intelligence.exporters.elastic_constants import (
    DEFAULT_ELASTICSEARCH_URL,
    ElasticExportError,
)
from workload_intelligence.exporters.elastic_documents import export_actions
from workload_intelligence.exporters.elastic_mappings import index_templates


def _load_elasticsearch_client() -> tuple[Any, Any]:
    try:
        from elasticsearch import Elasticsearch, helpers
    except ImportError as exc:
        raise ElasticExportError(
            "The official Elasticsearch Python client is required for --index-elastic. "
            "Install it with: python -m pip install elasticsearch"
        ) from exc
    return Elasticsearch, helpers


def create_elasticsearch_client(url: str = DEFAULT_ELASTICSEARCH_URL) -> Any:
    Elasticsearch, _helpers = _load_elasticsearch_client()
    client = Elasticsearch(url)
    try:
        if not client.ping():
            raise ElasticExportError(f"Elasticsearch did not respond at {url}")
    except Exception as exc:
        if isinstance(exc, ElasticExportError):
            raise
        raise ElasticExportError(f"Could not connect to Elasticsearch at {url}: {exc}") from exc
    return client


def ensure_index_templates(client: Any) -> None:
    for index_name, properties in index_templates().items():
        client.indices.put_index_template(
            name=f"{index_name}-template",
            index_patterns=[index_name],
            template={"mappings": {"dynamic": True, "properties": properties}},
        )


def index_run(
    run_id: str,
    scenario: Any,
    events: list[dict[str, Any]],
    report: dict[str, Any],
    validation: dict[str, Any],
    run_dir: Path,
    elasticsearch_url: str = DEFAULT_ELASTICSEARCH_URL,
    include_raw_query: bool = False,
) -> dict[str, Any]:
    client = create_elasticsearch_client(elasticsearch_url)
    _Elasticsearch, helpers = _load_elasticsearch_client()
    ensure_index_templates(client)
    actions = export_actions(
        run_id=run_id,
        scenario=scenario,
        events=events,
        report=report,
        validation=validation,
        run_dir=run_dir,
        include_raw_query=include_raw_query,
    )
    try:
        indexed, errors = helpers.bulk(client, actions, refresh=True, raise_on_error=False)
    except Exception as exc:
        raise ElasticExportError(f"Bulk indexing failed: {exc}") from exc
    if errors:
        raise ElasticExportError(f"Bulk indexing completed with errors: {errors[:3]}")
    return {"indexed": indexed, "indices": sorted({action["_index"] for action in actions})}
