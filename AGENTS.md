# AGENTS.md

This file provides standing instructions to Codex when working in this repository. It is not user documentation; it is project guidance that should shape planning, coding, verification, and handoff.

---

## Project Mission

This project is a spec-driven workload intelligence engine for gateway telemetry.

It receives raw usage events from gateways in front of data platforms such as Elasticsearch, Redis, MongoDB, PostgreSQL, Cassandra, and S3-compatible object storage, then infers:

```text
observed behavior -> inferred intent -> architecture fit
```

The current product surface is a Python CLI/debug dashboard that turns synthetic gateway events into:

- primitive operation labels,
- query template fingerprints,
- daily workload aggregation,
- access-pattern scores,
- workload profiles,
- architecture-fit recommendations,
- dashboard rows.

Use [README.md](README.md) for the runnable current slice and [codex_spec_driven_workload_intelligence_plan.md](codex_spec_driven_workload_intelligence_plan.md) for the broader implementation plan.

---

## Current Scope

Implemented:

- Sprint 0 spec files in `specs/`.
- Sprint 1 Elasticsearch end-to-end skeleton.
- Early Sprint 2 Redis GET/SETEX cache and GET/SET durable-state signals.
- Sprint 3 daily aggregation views by system, platform, customer, and template.
- Primitive profiles weighted by request count, latency cost, response volume, unique systems, and unique customers.
- Initial Sprint 4 PostgreSQL lookup, grouped-analytics, and text-search recommendation slices.
- Deterministic YAML-driven workload simulator with mocked response metadata, saved artifacts, and a local editor UI.
- Simulator primitive descriptions are shown from `specs/primitive-ontology.yaml`; platform query-flag availability comes from `specs/simulator-capabilities.yaml`.
- Optional local Elasticsearch/Kibana sink for simulator pipeline outputs.
- Kibana lineage export views for recommendation backtrace, template evidence, event trace, and simulator validation.
- Declarative primitive, pattern, and recommendation rules loaded from YAML.
- Focused pytest coverage for fingerprinting, primitive extraction, profiles, recommendations, and dashboard rendering.

Next planned work:

- Saved Kibana dashboards/searches, broader simulator scenario coverage, and Sprint 4 recommendation/parser support beyond the initial lookup, grouped-analytics, and text-search slices.

Not implemented yet:

- Full PostgreSQL parser coverage beyond the initial lookup, grouped-analytics, and text-search slices.
- Persistent human review workflow.
- Web dashboard.

---

## Deployment Context & Audience

Treat this as an early local prototype for a future production-adjacent system.

- Current runtime: local Python CLI over JSON examples.
- Intended runtime: asynchronous classifier outside the gateway request path.
- Intended users: platform engineers, data infrastructure engineers, SREs, and architecture reviewers.
- Operators care about evidence, explainability, low request-path risk, and tenant-safe aggregation.
- Input telemetry may include sensitive internal identifiers. Do not add logging or examples that expose secrets, credentials, or real customer data.

Important rule from the plan:

```text
The gateway emits raw usage events.
Classification and recommendations run asynchronously outside the request path.
```

---

## Tech Stack

- Language: Python.
- Test runner: pytest.
- Specs/config: YAML files under `specs/`.
- Example inputs: JSON files under `examples/`.
- Source package: `src/workload_intelligence/`.
- CLI entrypoint: `run_workload_dashboard.py` and `workload_intelligence.cli`.
- No web framework or persistent datastore is currently implemented.

---

## Architecture

```text
raw JSON event examples
-> ingest/raw_event.py
-> normalize/dispatcher.py
-> normalize/{elastic_normalizer.py,redis_normalizer.py}
-> normalize/template_fingerprint.py
-> primitives/{extractor.py,rule_engine.py}
-> aggregate/window_aggregator.py
-> patterns/scorer.py
-> profiles/profile_builder.py
-> recommendations/recommendation_engine.py
-> ui/dashboard.py
-> cli.py / run_workload_dashboard.py
```

Specs in `specs/` are the source of truth for schemas, ontology, rules, recommendation logic, and acceptance examples. Implementation should satisfy the specs, not replace them.

---

## Commands

Run the current dashboard slice:

```powershell
python run_workload_dashboard.py examples\elastic_dashboard_events.json
python run_workload_dashboard.py examples\elastic_dashboard_events.json --json
python run_workload_dashboard.py examples\redis_cache_events.json
python run_workload_dashboard.py examples\redis_state_events.json
```

Run tests:

```powershell
python -m pytest
```

---

## Design Constraints

These are hard constraints for this project:

- Specs are the contract. When classifier behavior changes, update the relevant schema, ontology, rules, examples, and tests together.
- Primitive names must be declared in `specs/primitive-ontology.yaml` before they appear in extraction rules or simulator capabilities.
- Query-shape primitives and response-derived signals are separate simulator concepts. Do not expose operational response signals such as `large_result` as selectable query flags.
- Keep classification and recommendations out of the gateway request path.
- Design for multi-tenancy from day one. System, customer, platform, and template identity must come from input data, not hardcoded names.
- Normalize query templates by removing literal values while preserving structural meaning such as fields, operators, aggregation shapes, and command types.
- Keep platform-specific parsing in normalizers and declarative rules in YAML where practical.
- Do not add recommendations that lack evidence in the workload profile or rule match.
- Add platforms in complete vertical slices: schema support, normalizer/parser, primitive rules, examples, tests, aggregation/profile behavior, and recommendation behavior where applicable.
- Prefer deterministic classification logic. LLM-assisted interpretation belongs in a future human-review workflow, not in the core classifier without an explicit design.

---

## Project-Specific Lessons

Check these before implementing:

- **Rule**: Do not infer architecture intent from a single operation.
  **Why**: The project depends on time windows, template stability, and repeated behavior to distinguish occasional queries from workload patterns.

- **Rule**: Do not normalize away structural query meaning.
  **Why**: Literal values should become placeholders, but fields, operators, aggregation structure, and command type are evidence.

- **Rule**: Do not hide new classifier behavior only in Python code.
  **Why**: Specs and acceptance examples are how future contributors understand and verify the classifier contract.

---

## Working Style

- Inspect the relevant specs before changing implementation.
- Prefer small vertical slices over broad partial layers.
- Reuse existing module boundaries before adding new abstractions.
- Keep changes easy to verify with pytest or a CLI example.
- State assumptions when requirements are ambiguous.
- Push back when a requested shortcut conflicts with the spec-driven contract or request-path safety.

---

## Execution And Verification

For meaningful changes:

1. Define the observable behavior before editing.
2. Update or add the spec/rule/example that describes the behavior.
3. Add or update focused tests.
4. Implement the smallest code change that satisfies the spec.
5. Run `python -m pytest` unless the change is docs-only.
6. For user-visible pipeline behavior, run at least one relevant `run_workload_dashboard.py` example.

For bugs, follow `.agents/skills/bug-investigation/SKILL.md`.

For refactors, follow `.agents/skills/refactor-safely/SKILL.md`.

For deliverables or handoff, follow `.agents/skills/deliverable-verification/SKILL.md`.

---

## Planning

Use [codex_spec_driven_workload_intelligence_plan.md](codex_spec_driven_workload_intelligence_plan.md) as the active roadmap unless the user gives a newer plan.

When following a plan:

- Complete and verify one step before starting the next.
- Mark completed work in the plan when the user asks for persistent plan tracking.
- Record deviations in the plan if implementation changes the agreed path.
- Split steps before starting them if they turn out too large to verify cleanly.

---

## Git Conventions

This workspace may not always be a Git repository. When Git is available:

- Use Conventional Commits.
- Keep one logical change per commit.
- Stage files explicitly by name.
- Never commit secrets, `.env` files, credentials, caches, or generated `__pycache__` artifacts.
- Do not force-push to `main`.

---

## Skills Available

Repo skills live in `.agents/skills/`. Codex can discover them automatically, and they can also be invoked explicitly when useful.

- `.agents/skills/project-intake/SKILL.md`
- `.agents/skills/bug-investigation/SKILL.md`
- `.agents/skills/refactor-safely/SKILL.md`
- `.agents/skills/deliverable-verification/SKILL.md`
- `.agents/skills/docker/SKILL.md`
- `.agents/skills/session-close/SKILL.md`
- `.agents/skills/template-sync/SKILL.md`

When a task matches a skill, read and follow it before making substantial changes.

---

## Skills To Add

Potential future skills:

| Skill | Why it matters |
|---|---|
| `testing` | Defines what to test, when to mock, fixture strategy, and platform-specific acceptance coverage. |
| `ci-cd` | Defines what a passing pipeline means and how to debug CI failures. |
| `security-review` | Helps catch sensitive telemetry handling, secret leakage, and unsafe external integrations. |
| `performance-investigation` | Distinguishes functional correctness from throughput or latency regressions. |
