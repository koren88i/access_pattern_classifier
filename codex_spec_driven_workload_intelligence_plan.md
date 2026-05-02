# Codex Plan: Spec-Driven Workload Intelligence Engine

## Implementation Status

Last updated: 2026-05-02

- Done: Sprint 0 spec artifacts in `specs/`.
- Done: Sprint 1 end-to-end skeleton for synthetic Elasticsearch events.
- Done: Early Redis support for cache and possible durable-state examples.
- Done: Sprint 3 daily aggregation views by system/platform/customer/template and weighted primitive profiles.
- Done: Initial Sprint 4 PostgreSQL grouped-analytics and text-search recommendation slices.
- Done: Deterministic YAML-driven workload simulator with artifact output and local scenario editor UI.
- Done: Optional local Elasticsearch/Kibana sink for simulator pipeline outputs.
- Done: Kibana lineage export views for recommendation backtrace, template evidence, event trace, and simulator validation.
- Done: Simulator query flags are backed by capability SSOT, primitive descriptions come from ontology SSOT, and response-derived signals are separated from query-shape controls.
- Verified: `python -m pytest` passes.
- Next: Build saved Kibana dashboards/searches, broaden simulator scenario coverage, and expand Sprint 4 recommendation/parser support.

## 1. Mission

Build a spec-driven system that turns gateway telemetry from data platforms into workload intelligence.

The system receives raw usage events from gateways in front of platforms such as Elasticsearch, Redis, MongoDB, PostgreSQL, Cassandra, and S3-compatible object storage.

It then produces:

1. Primitive multi-label classifications per operation.
2. Aggregated workload profiles over time.
3. Access-pattern classification per system/platform/customer.
4. Architecture mismatch detection.
5. Platform market analysis for investment prioritization.

The goal is not only to monitor queries, but to infer:

```text
observed behavior -> inferred intent -> architecture fit
```

Examples:

```text
Elasticsearch used mostly for stable high-volume aggregations
-> analytical serving workload
-> evaluate ClickHouse or another serving layer

Redis used as durable state without TTL
-> durable key-value/state workload
-> review Redis fit, consider Cassandra/PostgreSQL depending on scale and access pattern
```

---

## 2. Core Principle

Use spec-driven development.

Before implementing a classifier, define:

1. Input schema.
2. Output schema.
3. Ontology.
4. Rules.
5. Evidence requirements.
6. Test examples.

The specs are the source of truth. The implementation exists to satisfy the specs.

Recommended repository structure:

```text
workload-intelligence/
  specs/
    raw-event.schema.yaml
    primitive-ontology.yaml
    primitive-rules.yaml
    access-pattern-ontology.yaml
    pattern-rules.yaml
    workload-profile.schema.yaml
    recommendation-rules.yaml
    test-cases.yaml

  src/
    ingest/
      raw_event.py
    normalize/
      elastic_normalizer.py
      redis_normalizer.py
      template_fingerprint.py
    primitives/
      extractor.py
      rule_engine.py
    aggregate/
      window_aggregator.py
    patterns/
      scorer.py
    profiles/
      profile_builder.py
    recommendations/
      recommendation_engine.py
    api/
      app.py
    ui/
      dashboard.py

  tests/
    test_elastic_primitives.py
    test_redis_primitives.py
    test_template_fingerprinting.py
    test_aggregation.py
    test_pattern_scoring.py
    test_recommendations.py

  examples/
    elastic_dashboard_query.json
    elastic_text_search.json
    redis_cache.json
    redis_state.json
```

---

## 3. End-to-End Pipeline

The system must be useful from the first vertical slice.

Implement all layers, but start with a very small implementation inside each one.

```text
gateway event
-> raw normalized event
-> query normalization and template fingerprinting
-> primitive signal extraction
-> aggregation layer
-> access pattern scoring
-> workload profile
-> recommendation
-> dashboard/debug view
```

Important rule:

```text
The gateway emits raw usage events.
Classification and recommendations run asynchronously outside the request path.
```

---

## 4. Layer 0: Raw Gateway Events

### Goal

Capture enough information from every operation to classify it later, without slowing down the customer request path.

### Initial Platform Scope

Start with:

```text
Elasticsearch + Redis
```

Design schemas so additional platforms can be added later.

### Raw Event Schema

```yaml
RawUsageEvent:
  event_id: string
  timestamp: datetime

  identity:
    system_id: string
    customer_id: optional string
    user_id: optional string
    client_id: optional string
    service_name: optional string
    trace_id: optional string
    session_id: optional string

  platform:
    type: enum[elasticsearch, redis, mongo, postgres, cassandra, s3]
    database: optional string
    index_or_table: optional string

  operation:
    method: optional string
    command: string
    endpoint: optional string
    raw_query: object | string
    normalized_query: optional object | string

  request:
    request_bytes: optional number

  response:
    status_code: optional number
    latency_ms: number
    response_bytes: optional number
    result_count: optional number
```

### MVP Requirements

For Elasticsearch capture:

```text
platform
system_id
timestamp
index
endpoint
method
body
latency_ms
status_code
result_count if available
```

For Redis capture:

```text
platform
system_id
timestamp
command
key or key pattern
ttl/expire signal if available
latency_ms
status_code/error signal
```

---

## 5. Layer 1: Primitive Multi-Label Signal Extraction

### Goal

Classify each operation into primitive intent signals.

Do not force one category per operation.

Each primitive has:

```text
matched: true/false
signal_weight: strength contributed by a matched rule
rule_confidence: confidence in the rule as evidence
evidence: human-readable reasons
```

Signal weights are not probabilities and do not need to sum to 1.

### Primitive Ontology v0

```yaml
PrimitiveIntent:
  access_shape:
    - key_lookup
    - range_lookup
    - multi_filter
    - scan
    - aggregation
    - sort_paginate

  data_interaction:
    - point_write
    - append_write
    - update_write
    - batch_write
    - bulk_read

  semantics:
    - time_series
    - text_search
    - vector_search
    - geo_search

  operational_shape:
    - large_result
    - low_latency_sensitive
    - ttl_or_expire_usage

PrimitiveDescriptions:
  key_lookup: "Reads one or a small set of records by stable identifier or key."
  aggregation: "Computes grouped, counted, summed, averaged, or otherwise reduced results."
  large_result: "Returns a large number of rows, documents, keys, or result items."
```

Start with these implemented:

```text
key_lookup
range_lookup
multi_filter
scan
aggregation
sort_paginate
point_write
batch_write
update_write
bulk_read
time_series
text_search
vector_search
geo_search
large_result
```

### Primitive Output Example

```json
{
  "event_id": "evt-123",
  "platform": "elasticsearch",
  "template_id": "tpl-a91",
  "primitive_signals": {
    "key_lookup": {
      "matched": true,
      "signal_weight": 0.4,
      "rule_confidence": 0.8,
      "evidence": ["term filter on customer_id"]
    },
    "aggregation": {
      "matched": true,
      "signal_weight": 0.9,
      "rule_confidence": 0.95,
      "evidence": ["aggs clause exists: terms aggregation on status"]
    },
    "time_series": {
      "matched": true,
      "signal_weight": 0.7,
      "rule_confidence": 0.9,
      "evidence": ["range filter on @timestamp"]
    },
    "text_search": {
      "matched": false,
      "signal_weight": 0.0,
      "rule_confidence": 0.9,
      "evidence": []
    }
  }
}
```

### Rule Spec Example

```yaml
rules:
  - id: elastic_aggregation_aggs
    platform: elasticsearch
    primitive: aggregation
    when:
      path_exists: "$.body.aggs"
    signal_weight: 0.9
    rule_confidence: 0.95
    evidence: "Elasticsearch query contains aggs clause"

  - id: elastic_text_match
    platform: elasticsearch
    primitive: text_search
    when:
      any_path_exists:
        - "$.body.query.match"
        - "$.body.query.multi_match"
        - "$.body.query.query_string"
    signal_weight: 0.85
    rule_confidence: 0.9
    evidence: "Elasticsearch query contains text-search query type"

  - id: elastic_time_range
    platform: elasticsearch
    primitive: time_series
    when:
      range_filter_field_matches:
        - "@timestamp"
        - "timestamp"
        - "time"
        - "created_at"
    signal_weight: 0.7
    rule_confidence: 0.85
    evidence: "Range filter over timestamp-like field"
```

Primitive names and descriptions must be declared in `primitive-ontology.yaml` before they appear in extraction rules or simulator capabilities. Platform-specific detection details belong in `primitive-rules.yaml`; for example `redis_get_by_key` should normally be a rule id that emits the ontology primitive `key_lookup`, not a new primitive.

Simulator query-shape controls are narrower than the ontology. `simulator-capabilities.yaml` declares which ontology primitives can be synthesized as query flags for each platform. Response-derived operational signals such as `large_result` and `low_latency_sensitive` are driven by response metadata distributions and are shown separately from query flags.

---

## 6. Query Template and Fingerprint Layer

### Goal

Group repeated query shapes.

Raw queries differ because parameter values change. The system should normalize values and produce a stable template hash.

Example raw query:

```json
{
  "query": {
    "bool": {
      "filter": [
        { "term": { "customer_id": 123 } },
        { "range": { "@timestamp": { "gte": "2026-04-01", "lte": "2026-04-02" } } }
      ]
    }
  },
  "aggs": {
    "by_status": {
      "terms": {
        "field": "status"
      }
    }
  }
}
```

Normalized template:

```json
{
  "query": {
    "bool": {
      "filter": [
        { "term": { "customer_id": "?" } },
        { "range": { "@timestamp": { "gte": "?", "lte": "?" } } }
      ]
    }
  },
  "aggs": {
    "by_status": {
      "terms": {
        "field": "status"
      }
    }
  }
}
```

Then:

```text
template_id = sha256(canonical_json(normalized_template))
```

### Why Templates Matter

A single aggregation only says:

```text
this operation computes a summary
```

But template behavior over time tells us architectural intent.

Example:

```text
aggregation template appears 5 times/month
-> maybe reporting, occasional admin query, or manual investigation

same aggregation template appears 500,000 times/day
-> likely product/API/dashboard analytical serving workload
```

Stability matters:

```text
high volume + stable templates
-> serving-layer candidate

high volume + unstable templates
-> ad-hoc analytics/exploration candidate
```

---

## 7. Layer 2: Aggregation Layer

### Goal

Aggregate primitive signals into workload-level evidence.

A single operation gives weak evidence. Time windows and templates create meaning.

### Aggregation Dimensions

The system should support:

```text
time window
query template
system/application
platform
customer/team
```

MVP starts with:

```text
system_id + platform + 1 day window
```

But the schema should be ready for all dimensions.

### Aggregate Window Schema

```yaml
AggregateWindow:
  key:
    system_id: string
    platform: string
    window_start: datetime
    window_end: datetime

  volume_metrics:
    request_count: number
    unique_template_count: number

  latency_metrics:
    avg_latency_ms: number
    p95_latency_ms: number
    max_latency_ms: number

  data_metrics:
    avg_response_bytes: optional number
    avg_result_count: optional number

  primitive_profile:
    key_lookup: number
    range_lookup: number
    multi_filter: number
    aggregation: number
    scan: number
    sort_paginate: number
    point_write: number
    batch_write: number
    update_write: number
    bulk_read: number
    time_series: number
    text_search: number
    vector_search: number
    geo_search: number
    large_result: number

  template_metrics:
    top_templates_coverage: number
    template_stability: number
```

### Basic Aggregation Formula

For MVP:

```text
primitive_profile[p] =
  sum(operation.primitive_signals[p].signal_weight) / request_count
```

Later add cost-weighted views:

```text
primitive_profile_by_latency_cost[p] =
  sum(operation.primitive_signals[p].signal_weight * latency_ms) / sum(latency_ms)
```

This is important because:

```text
By count:
90% key lookups

By latency cost:
70% aggregations
```

That tells us most calls are cheap lookups but most platform cost comes from aggregation.

---

## 8. Layer 3: Access Pattern Scoring

### Goal

Convert aggregated primitive profiles into meaningful workload categories.

### Access Pattern Ontology v0

```yaml
AccessPatterns:
  oltp:
    description: Transactional application database usage.
    positive_signals:
      - key_lookup
      - point_write
      - update_write
      - low result count
      - low latency
    negative_signals:
      - heavy aggregation
      - large scans
      - text/vector/geo dominance

  high_throughput_state:
    description: Predictable state access at high volume.
    positive_signals:
      - key_lookup
      - point_write
      - batch_write
      - high request rate
      - stable templates
    negative_signals:
      - joins
      - ad-hoc filters
      - aggregations

  cache:
    description: Repeated key-based ephemeral access.
    positive_signals:
      - key_lookup
      - high repetition
      - ttl_or_expire_usage
      - low latency
    negative_signals:
      - durable retention
      - complex queries

  analytical_serving:
    description: Repeated analytical queries with SLA expectations.
    positive_signals:
      - aggregation
      - time_series
      - multi_filter
      - stable templates
      - high concurrency
    negative_signals:
      - high text_search
      - low repetition
      - complex ad-hoc joins

  ad_hoc_analytics:
    description: Exploratory analytical access with changing query shapes.
    positive_signals:
      - scan
      - aggregation
      - low template stability
      - large result sets
    negative_signals:
      - high repetition
      - strict low-latency behavior

  search_text:
    description: Full-text search workload.
    positive_signals:
      - text_search

  search_vector:
    description: Vector similarity search workload.
    positive_signals:
      - vector_search

  search_geo:
    description: Geospatial search workload.
    positive_signals:
      - geo_search

  blob:
    description: Key-based access to large opaque objects.
    positive_signals:
      - key_lookup
      - large payload
      - no filtering
```

### MVP Access Patterns

Start with:

```text
analytical_serving
search_text
cache
oltp
ad_hoc_analytics
unknown_mixed
```

### Pattern Rule Example

```yaml
pattern_rules:
  analytical_serving:
    score:
      aggregation: 0.35
      time_series: 0.20
      multi_filter: 0.10
      template_stability: 0.20
      request_rate: 0.10
      p95_latency_pressure: 0.05
    penalties:
      text_search: -0.30
      vector_search: -0.30
      geo_search: -0.15

  search_text:
    score:
      text_search: 0.80
      sort_paginate: 0.10
      key_lookup: 0.05
      template_stability: 0.05

  cache:
    score:
      key_lookup: 0.45
      request_rate: 0.20
      ttl_or_expire_usage: 0.25
      low_latency: 0.10
    penalties:
      aggregation: -0.40
      scan: -0.30

  ad_hoc_analytics:
    score:
      scan: 0.30
      aggregation: 0.25
      low_template_stability: 0.30
      large_result: 0.15
```

---

## 9. Layer 4: Workload Profiles

### Goal

Create the main product object: an explainable workload profile.

### Workload Profile Schema

```yaml
WorkloadProfile:
  profile_id: string

  scope:
    system_id: string
    customer_id: optional string
    platform: string
    database_or_index: optional string
    window_start: datetime
    window_end: datetime

  volume:
    request_count: number
    unique_template_count: number
    top_templates_coverage: number

  latency:
    avg_latency_ms: number
    p95_latency_ms: number
    max_latency_ms: number

  primitive_profile:
    key_lookup: number
    range_lookup: number
    multi_filter: number
    aggregation: number
    scan: number
    sort_paginate: number
    point_write: number
    batch_write: number
    update_write: number
    bulk_read: number
    time_series: number
    text_search: number
    vector_search: number
    geo_search: number
    large_result: number

  access_pattern_scores:
    oltp: number
    cache: number
    analytical_serving: number
    ad_hoc_analytics: number
    search_text: number
    search_vector: number
    search_geo: number
    high_throughput_state: number
    unknown_mixed: number

  dominant_patterns:
    - pattern: string
      score: number
      confidence: number

  evidence:
    top_templates:
      - template_id: string
        request_count: number
        contribution: number
        primitive_summary: object

    explanation:
      - string
```

### Example Profile

```json
{
  "scope": {
    "system_id": "fraud-service",
    "platform": "elasticsearch",
    "window_start": "2026-04-01T00:00:00Z",
    "window_end": "2026-04-30T00:00:00Z"
  },
  "volume": {
    "request_count": 12000000,
    "unique_template_count": 80,
    "top_templates_coverage": 0.86
  },
  "primitive_profile": {
    "aggregation": 0.74,
    "time_series": 0.68,
    "text_search": 0.05,
    "key_lookup": 0.22,
    "scan": 0.31
  },
  "access_pattern_scores": {
    "analytical_serving": 0.81,
    "search_text": 0.06,
    "ad_hoc_analytics": 0.18,
    "oltp": 0.12
  },
  "dominant_patterns": [
    {
      "pattern": "analytical_serving",
      "score": 0.81,
      "confidence": 0.76
    }
  ],
  "evidence": {
    "explanation": [
      "74% aggregation signal across requests",
      "68% time-series signal",
      "Top 10 templates cover 86% of traffic",
      "Text-search signal is only 5%"
    ]
  }
}
```

---

## 10. Recommendation Layer

### Goal

Turn workload profiles into explainable architecture guidance.

### MVP Recommendation Types

```text
no_action
review_required
technology_mismatch_candidate
migration_candidate
platform_investment_signal
```

### Recommendation Rule Examples

```yaml
rules:
  - id: elastic_as_analytical_serving
    when:
      platform: elasticsearch
      access_pattern_scores.analytical_serving: "> 0.65"
      access_pattern_scores.search_text: "< 0.20"
      volume.request_count: "> threshold"
    then:
      recommendation: "Evaluate analytical serving layer"
      target_technology: "ClickHouse candidate"
      severity: "medium"
      evidence:
        - "Elasticsearch traffic is dominated by analytical serving pattern"
        - "True text-search signal is low"

  - id: redis_as_durable_state
    when:
      platform: redis
      primitive_profile.key_lookup: "> 0.75"
      ttl_or_expire_usage: "< 0.10"
      retention_observed: "long"
    then:
      recommendation: "Review Redis durable-state usage"
      target_technology: "Cassandra or PostgreSQL depending on scale and access pattern"
      severity: "medium"

  - id: postgres_heavy_analytics
    when:
      platform: postgres
      primitive_profile.aggregation: "> 0.50"
      primitive_profile.scan: "> 0.40"
      volume.request_count: "> threshold"
    then:
      recommendation: "Review analytical workload on PostgreSQL"
      target_technology: "ClickHouse or Iceberg/Trino depending on SLA"
      severity: "medium"
```

---

## 11. Dashboard v0

Expose the full product from day one.

### Page 1: System Workload Profile

For one system show:

```text
current platform
dominant access pattern
primitive signal breakdown
top query templates
recommendation
evidence
```

### Page 2: Platform Market Analysis

Example:

```text
Elasticsearch:
- 52% analytical serving
- 26% text search
- 12% ad-hoc exploration
- 10% unknown/mixed

Redis:
- 70% cache
- 18% durable state
- 12% unknown
```

### Page 3: Mismatch Candidates

```text
System          Platform        Detected Pattern        Recommendation
fraud-service   Elasticsearch   Analytical serving      Evaluate ClickHouse
job-state-api   Redis           Durable state           Review Cassandra/PG
reporting-api   PostgreSQL      Heavy aggregation       Evaluate serving layer
```

### Page 4: Ontology Debug View

For trust, show:

```text
why this was classified this way
which rules matched
which primitive signal weights contributed
which templates dominated
sample events
confidence
```

---

## 12. Agile Delivery Plan

### Sprint 0: Specs Only

Deliver:

```text
raw-event.schema.yaml
primitive-ontology.yaml
primitive-rules.yaml
access-pattern-ontology.yaml
pattern-rules.yaml
workload-profile.schema.yaml
recommendation-rules.yaml
test-cases.yaml
```

Acceptance criteria:

```text
At least 6 test cases exist:
- Elasticsearch dashboard aggregation
- Elasticsearch text search
- Redis cache GET/SETEX
- Redis durable state GET/SET without TTL
- PostgreSQL simple OLTP lookup
- PostgreSQL scan + GROUP BY
```

---

### Sprint 1: End-to-End Skeleton

Goal:

```text
one raw event -> one primitive profile -> one aggregate window -> one workload profile -> one dashboard row
```

Implement:

```text
synthetic event ingestion
Elasticsearch normalizer
template fingerprinting
primitive extraction via declarative rules
daily aggregation by system/platform
3 access pattern scores:
- analytical_serving
- search_text
- unknown_mixed
basic dashboard table
```

Acceptance criteria:

```text
Given synthetic Elasticsearch dashboard events,
the system produces an analytical_serving workload profile with evidence.
```

---

### Sprint 2: Redis Support

Add:

```text
Redis command parser
TTL/EXPIRE signal
cache access pattern
early durable_state/high_throughput_state signal
```

Acceptance criteria:

```text
Redis GET + SETEX traffic classifies mostly as cache.
Redis GET + SET without TTL classifies as possible durable state / review required.
```

---

### Sprint 3: Better Aggregation

Add aggregation views by:

```text
template
system
platform
customer/team
```

Add multiple weighting modes:

```text
by request count
by latency cost
by response volume
by unique systems/customers
```

Acceptance criteria:

```text
Dashboard can show:
- platform-level market analysis
- top templates per system
- primitive profile by count and by latency cost
```

---

### Sprint 4: Recommendations

Add first recommendation rules:

```text
Elasticsearch analytical-serving candidate
Redis durable-state candidate
PostgreSQL analytics candidate
```

Acceptance criteria:

```text
Recommendation includes:
- target review area
- confidence
- evidence
- matched rule id
```

---

### Sprint 5: Feedback and LLM Assist

Add human review workflow:

```text
accept classification
reject classification
mark ambiguous
suggest better pattern
add domain-specific matcher hints
```

Admins and domain reviewers should be able to promote observed query knowledge into controlled rule configuration.
For example, while reviewing a PostgreSQL `key_lookup` miss, an admin should be able to add domain identifier fields such as `account_uuid`, `tenant_key`, `external_ref`, or a platform-specific equivalent without editing Python code.
This should remain spec-driven and auditable:

```text
review query evidence
consult domain owner if needed
add or approve field/rule hint
write/update YAML rule configuration
re-run affected examples/tests
preserve who/why metadata for the rule change
```

Do not turn this into per-event manual override. The goal is to make future classifications better through reviewable rule updates.

Use LLM only offline for:

```text
ambiguous template labeling
explanation drafting
ontology improvement suggestions
```

Do not call an LLM per query in production.

Acceptance criteria:

```text
Reviewed labels are stored and can be used later for calibration or training.
```

---

## 13. Testing Philosophy

Tests should be spec-driven.

For each primitive and access pattern, create examples with expected outputs.

Example:

```yaml
case: elastic_dashboard_query
input:
  platform: elasticsearch
  body:
    query:
      bool:
        filter:
          - term:
              customer_id: 123
          - range:
              "@timestamp":
                gte: "now-1h"
    aggs:
      by_status:
        terms:
          field: status
expected:
  primitive_signals:
    aggregation:
      matched: true
      min_signal_weight: 0.8
    time_series:
      matched: true
      min_signal_weight: 0.6
    key_lookup:
      matched: true
      min_signal_weight: 0.2
    text_search:
      matched: false
```

---

## 14. Implementation Rules for Codex

1. Keep classification logic declarative where possible.
2. Do not hardcode ontology knowledge deeply inside Python functions.
3. Preserve evidence for every primitive signal.
4. Separate matched-condition evidence from signal weight and rule confidence.
5. Do not require primitive signal weights to sum to 1.
6. Build all layers from the beginning, even if each layer is small.
7. Keep gateway path clean; classification runs async.
8. Optimize for explainability over model cleverness.
9. Use rules first. Use LLMs only for offline labeling/review.
10. Favor simple working vertical slices over large incomplete modules.

---

## 15. Definition of Done for MVP

The MVP is done when the system can process synthetic gateway events and produce an explainable result like:

```text
In the last 24 hours, system fraud-service used Elasticsearch mostly as analytical serving.

Evidence:
- 71% of requests contained aggregations
- 65% had timestamp range filters
- top 5 templates covered 82% of traffic
- only 4% contained text-search queries

Recommendation:
Review whether this workload belongs on the analytical serving layer rather than Elasticsearch.
```

The first MVP does not need perfect classification. It must prove the full flow:

```text
raw signal -> primitive evidence -> aggregation -> access pattern -> workload profile -> recommendation
```
