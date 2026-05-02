---
name: project-intake
description: Use when a repository is new, `AGENTS.md` has major TODO placeholders, or the decision-critical project sections are too incomplete to guide implementation. Inspect the repo first, then ask only the minimum high-value questions needed to make `Project mission`, `Deployment context & audience`, `Tech stack`, `Commands`, and `Design constraints` actionable.
---

# Project Intake

## Goal
Bootstrap a new project's `AGENTS.md` without turning onboarding into an interrogation.

Fill the minimum sections needed for good engineering judgment early, then let the rest of the file mature through real work.

## Trigger this skill when
- The repository is new or lightly scaffolded.
- `AGENTS.md` still contains major `_TODO_` placeholders in the critical sections.
- A task depends on project context that has not been written down yet.
- The user asks to bootstrap, onboard, or fill out the project guidance before substantial implementation.

## Critical sections
Make these sections actionable as early as possible:
- `Project mission`
- `Deployment context & audience`
- `Tech stack`
- `Commands`
- `Design constraints`

These may start rough and improve later:
- `Architecture`
- `Git conventions` scopes
- `Coding standards` details
- `Skills to add`

These should usually emerge only from real experience:
- `Project-specific anti-patterns and lessons learned`

## Workflow

### 1) Inspect the repo before asking questions
Start with evidence that already exists:
- `README` and docs
- package manifests and lockfiles
- Docker / Compose files
- CI config
- entrypoints, tests, and scripts
- existing `AGENTS.md`

Draft what you can from the repo before asking the user anything.

### 2) Separate known facts from missing decisions
For each critical section, decide whether the answer is:
- already evidenced by the repo,
- implied but still needs confirmation,
- truly missing and needs user input.

Only ask about the third category.

### 3) Ask the fewest high-value questions
Ask only what is needed to make the critical sections useful.

Prioritize questions in this order:
1. what problem the project solves and for whom,
2. where it runs and who operates it,
3. what commands and workflows are canonical,
4. what constraints are non-negotiable.

Prefer one short batch of tightly related questions over a long checklist. Do not ask the user to fill every section manually if the repo already answers part of it.

### 4) Write or update `AGENTS.md`
Turn the gathered information into concise, concrete guidance.

Prefer specifics over vague principles:
- Good: `Production uses PostgreSQL 16 on RDS in eu-west-1.`
- Weak: `Database is managed in the cloud.`

If something is still unknown, leave a focused placeholder that names the missing decision rather than a generic TODO.

### 5) Leave the rest for progressive onboarding
Do not block implementation just because every section is not complete.

If a section depends on experience rather than setup, leave it partial and update it later when the repo reveals durable knowledge.

## Output format
For an intake task, structure the response like this:

1. What was learned from the repo
2. Questions asked or assumptions made
3. Sections updated
4. What remains intentionally incomplete

## Guardrails
- Do not invent project facts to make the template look complete.
- Do not ask broad low-signal questionnaires when the repo can answer the question.
- Do not populate `Project-specific anti-patterns and lessons learned` from guesswork.
- Do not overwrite user-written project guidance without preserving its intent.
- Do not block execution on perfect completeness; make the file actionable first, then improve it over time.
