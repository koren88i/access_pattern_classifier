# Access Pattern Classifier

Spec-driven workload intelligence for gateway telemetry.

The current sprint implements a small vertical slice:

```text
raw synthetic event
-> platform normalization
-> query template fingerprint
-> primitive signal extraction
-> daily target-scope aggregation
-> access-pattern scoring
-> workload profile
-> recommendation
-> dashboard row
```

The specs in `specs/` are the source of truth for schemas, ontology, rules, recommendation logic, and acceptance examples.

## Run

```powershell
python run_workload_dashboard.py examples\elastic_dashboard_events.json
python run_workload_dashboard.py examples\elastic_dashboard_events.json --json
python run_workload_dashboard.py examples\elastic_dashboard_events.json --report-json
python run_workload_dashboard.py examples\elastic_dashboard_events.json --view platform
python run_workload_dashboard.py examples\elastic_dashboard_events.json --view templates
python run_workload_dashboard.py examples\elastic_dashboard_events.json --view primitive-weights
python run_workload_dashboard.py examples\postgres_analytics_events.json
python run_workload_dashboard.py examples\postgres_text_search_events.json
```

## Simulate

Generate synthetic gateway events from a YAML scenario, run the existing pipeline, and save replayable artifacts:

```powershell
python run_workload_simulator.py scenarios\postgres_text_search.yaml
python run_workload_simulator.py scenarios\postgres_analytics.yaml
python run_workload_simulator.py scenarios\redis_cache.yaml
python run_workload_simulator.py scenarios\redis_durable_state.yaml
python run_workload_simulator.py scenarios\elastic_analytics.yaml
```

Start the local scenario editor:

```powershell
python run_workload_simulator.py --ui
```

Simulator runs are saved under `simulator_runs\` with the scenario, generated events, JSON reports, dashboard text, and validation output.

### Simulator Primitive Contract

The simulator UI separates query-shape inputs from response-derived signals:

- `specs\primitive-ontology.yaml` is the source of truth for primitive names and descriptions.
- `specs\simulator-capabilities.yaml` is the source of truth for which primitives each platform can synthesize as query flags.
- Response-derived signals such as `large_result` and `low_latency_sensitive` are shown separately in the UI and are driven by response distributions such as `responses.result_count` or `responses.latency_ms`, not by generated query syntax.
- The simulator UI includes a Matcher Source inspector. Checked primitive flags define the generated sample shape; the selected checked row defines which primitive rule is inspected. The normalized matcher input highlights the exact fields read by that primitive's rule conditions.
- The simulator UI currently edits the global scenario `responses:` block. YAML scenarios may still define per-shape overrides under `query_shapes[].responses`; adding dedicated UI controls for those shape-level response overrides is future work.
- Extraction rules emit `primitive_signals` with `signal_weight` and `rule_confidence`. Recommendation confidence remains a separate profile/recommendation concept.

### Response Metadata And Dashboards

Simulator `responses:` metadata flows through the pipeline as event evidence:

```text
scenario responses
-> generated event response.latency_ms / response.response_bytes / response.result_count
-> primitive rules and primitive profiles
-> aggregate latency/data metrics
-> access-pattern scores
-> recommendations and dashboard rows
```

The basic CLI dashboard does not render `latency_ms`, `response_bytes`, or `result_count` as top-level columns. It renders the resulting dominant pattern and recommendation. Response metadata still affects that row when it changes matched primitives such as `large_result`, latency/data-weighted primitive profiles, pattern scores, or recommendation evidence.

Kibana lineage views expose the response metadata directly on event-level documents. Use `workload-lineage-events` or `workload-primitive-events` to inspect the raw response fields behind a dashboard result.

In the expected-vs-observed validation view, `expected_primitive_share` and `observed_primitive_share` are both event shares. A value of `1.0` means every query in the run was expected to include, or actually matched, that primitive. `observed_primitive_profile` is separate: it keeps the weighted classifier signal, so a primitive can have `observed_primitive_share: 1.0` while its weighted signal is lower, such as `0.55`.

## Explore In Kibana

Start the local development Elastic/Kibana stack:

```powershell
docker compose up -d
```

Install the optional Elasticsearch exporter dependency:

```powershell
python -m pip install -r requirements-elastic.txt
```

Run a simulator scenario and index the extracted pipeline data:

```powershell
python run_workload_simulator.py scenarios\postgres_analytics.yaml --index-elastic --setup-kibana-data-views
```

Open Kibana at:

```text
http://localhost:5601
```

The simulator UI can also write a run to Elasticsearch. Start it with:

```powershell
python run_workload_simulator.py --ui
```

Then select `Write to Elasticsearch` before running the scenario. `Include raw query samples` stays separate and off by default.

Useful data views:

- `workload-primitive-signals`: primitive signal weight over time by platform, system, scenario, and template.
- `workload-primitive-events`: event-level primitive signals, normalized queries, and response metadata.
- `workload-aggregate-windows`: request-count, latency-cost, response-volume, and template-stability aggregations.
- `workload-profiles`: dominant patterns and profile-level evidence scoped by system, customer, platform, and database/index.
- `workload-recommendations`: recommendation severity, matched rule id, and target technology.
- `workload-lineage-recommendations`: recommendation backtrace with rule thresholds and observed values.
- `workload-lineage-templates`: top template evidence with normalized query, matched rules, and sample events.
- `workload-lineage-events`: event-forward trace from query and response metadata to template/profile/recommendation IDs.
- `workload-lineage-validation`: simulator expected-vs-observed trust check.

Raw query text/body is not exported by default. Add `--include-raw-query` only for local debugging with synthetic data.

### Lineage Verification In Kibana

Run the PostgreSQL analytics scenario with raw-query samples for synthetic debugging:

```powershell
python run_workload_simulator.py scenarios\postgres_analytics.yaml --index-elastic --setup-kibana-data-views --setup-kibana-dashboard --include-raw-query
```

Open the ready dashboard:

```text
http://localhost:5601/app/dashboards#/view/workload-intelligence-lineage-dashboard
```

The dashboard embeds four saved Discover sessions: recommendation backtrace, template evidence, event forward trace, and expected-vs-observed validation. Add a KQL filter such as:

```text
scenario_name: postgres_analytics
```

For manual Discover inspection, use these workflows:

1. Recommendation -> template -> event

   - Data view: `workload-lineage-recommendations`
   - Filter: `scenario_name: postgres_analytics`
   - Pin fields: `matched_rule_id`, `rule_condition_summary`, `source_numbers`, `top_template_ids`, `sample_event_ids`
   - Expected: `postgres_heavy_analytics` shows `aggregation > 0.50`, `scan > 0.40`, and `analytical_serving > 0.60` with observed values.

2. Event lookup

   - Dashboard panel: `WI Lineage - Event Lookup`
   - Controls: choose a `Run`, then search or paste `sim-postgres_analytics-000001` in `Event ID`
   - KQL fallback: `run_id: "2026-05-02T153200Z_postgres_analytics" and event_id: "sim-postgres_analytics-000001"`
   - Pin fields: `event_id`, `latency_ms`, `response_bytes`, `result_count`, `normalized_query_text`, `raw_query_text`, `matched_primitives`, `template_id`, `profile_id`, `recommendation_ids`
   - Expected: the pasted event ID shows one raw query, its response metadata, normalized query text, extracted primitives, and forward links.

3. Template evidence

   - Data view: `workload-lineage-templates`
   - Filter: `scenario_name: postgres_analytics`
   - Pin fields: `template_id`, `normalized_query_text`, `primitive_summary`, `matched_rule_ids`, `sample_event_ids`, `raw_query_samples`
   - Expected: the top template shows the GROUP BY SQL shape and primitive rule ids such as `postgres_aggregation_group_by`.

4. Template -> all events

   - Dashboard controls: choose a `Run`, then choose or paste a `Template ID`
   - Example template: `tpl-e87ba9c3db5c2546`
   - Expected: event panels show all raw event rows that collapsed into the selected normalized template.

5. Event -> recommendation

   - Data view: `workload-lineage-events`
   - Filter: one `event_id` from `sample_event_ids`
   - Pin fields: `raw_query_text`, `normalized_query_text`, `latency_ms`, `response_bytes`, `result_count`, `matched_primitives`, `template_id`, `aggregate_window_ids`, `profile_id`, `recommendation_ids`
   - Expected: one raw query and its response metadata link forward to matched primitives, its template, aggregate windows, profile, and recommendation.

6. Scenario expected -> observed

   - Data view: `workload-lineage-validation`
   - Filter: `scenario_name: postgres_analytics`
   - Pin fields: `expected_primitive_share`, `observed_primitive_share`, `observed_primitive_profile`, `observed_access_pattern_scores`, `recommendation_ids`
   - Expected: simulator expectations and observed query-match shares line up, with weighted primitive scores and recommendation IDs linked back to lineage recommendations.

## Test

```powershell
python -m pytest
```

## Codex

Project guidance for Codex lives in `AGENTS.md`. Repo-scoped skills live in `.agents/skills/` and are discoverable by Codex from the repository root.

## Current Scope

Implemented:

- Sprint 0 spec files, including at least six acceptance cases.
- Sprint 1 Elasticsearch end-to-end skeleton.
- Early Sprint 2 Redis GET/SETEX cache and GET/SET durable-state signals.
- Sprint 3 daily aggregation views by profile target, system, platform, customer, and template.
- Narrow Sprint 4 PostgreSQL analytics and text-search recommendation slices.
- Deterministic YAML-driven workload simulator with mocked response metadata and a local editor UI.
- Optional local Elasticsearch/Kibana sink for simulator pipeline outputs.
- Kibana lineage export views for recommendation backtrace, template evidence, event trace, and simulator validation.
- Primitive profiles weighted by request count, latency cost, response volume, unique systems, and unique customers.
- Declarative primitive, pattern, and recommendation rules loaded from YAML.
- Focused pytest coverage for fingerprinting, primitive extraction, profiles, recommendations, and dashboard rendering.

Not implemented yet:

- Full PostgreSQL parser coverage beyond the initial lookup, grouped-analytics, and text-search slices.
- Persistent human review workflow.
- Admin/domain-review workflow for adding controlled matcher hints, such as domain-specific identifier fields for `key_lookup`, back into YAML rule configuration.
- A web dashboard.
