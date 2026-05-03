from __future__ import annotations

import os


DEFAULT_ELASTICSEARCH_URL = os.environ.get("WORKLOAD_ELASTICSEARCH_URL", "http://localhost:9200")
DEFAULT_KIBANA_URL = os.environ.get("WORKLOAD_KIBANA_URL", "http://localhost:5601")

INDEX_SIM_RUNS = "workload-sim-runs"
INDEX_PRIMITIVE_EVENTS = "workload-primitive-events"
INDEX_PRIMITIVE_SIGNALS = "workload-primitive-signals"
INDEX_AGGREGATE_WINDOWS = "workload-aggregate-windows"
INDEX_PROFILES = "workload-profiles"
INDEX_RECOMMENDATIONS = "workload-recommendations"
INDEX_LINEAGE_RECOMMENDATIONS = "workload-lineage-recommendations"
INDEX_LINEAGE_TEMPLATES = "workload-lineage-templates"
INDEX_LINEAGE_EVENTS = "workload-lineage-events"
INDEX_LINEAGE_VALIDATION = "workload-lineage-validation"

EXPORT_INDICES = (
    INDEX_SIM_RUNS,
    INDEX_PRIMITIVE_EVENTS,
    INDEX_PRIMITIVE_SIGNALS,
    INDEX_AGGREGATE_WINDOWS,
    INDEX_PROFILES,
    INDEX_RECOMMENDATIONS,
    INDEX_LINEAGE_RECOMMENDATIONS,
    INDEX_LINEAGE_TEMPLATES,
    INDEX_LINEAGE_EVENTS,
    INDEX_LINEAGE_VALIDATION,
)


class ElasticExportError(RuntimeError):
    pass
