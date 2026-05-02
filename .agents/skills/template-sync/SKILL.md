---
name: template-sync
description: Use when a real project's `AGENTS.md` or `.agents/skills/` has improved and you want to promote the generalizable parts back into a Codex template repo. Compare if needed, strip project-specific details, and apply the improvement in the separate template repository.
---

# Template Sync

## Goal
Promote reusable improvements discovered in a real project back into a Codex template repo.

## Use this when
- A real project's `AGENTS.md` section turned out better than the template version and should be generalized upstream
- A local skill in `.agents/skills/` was improved in a way that would help other projects too
- A skill listed under `Skills to add` in a real project has now been written and belongs in the template repo
- The user asks to contribute, upstream, promote, or carry an improvement back into a Codex template repo

---

## Real-world setup

Treat this as a two-repo workflow:

- **Repo 1: the real project** where the improvement was discovered
- **Repo 2: the template repo** where the generalized improvement should land

Typical local layout:

```text
work/
  my-real-project/
  codex-template/
```

Preferred workflow:
- Inspect and learn in the real project
- Apply the cleaned-up improvement in the separate local clone of the Codex template repo
- Commit and push from the template repo, not from the project repo

Optional comparison helper:
- Add the template repo as a read-only remote inside the project repo if you only need to inspect the current upstream file
- Do not treat that remote as the place to develop or push template changes

If the template repo is not available locally, ask the user for its path or remote before editing upstream files.

---

## File path mapping

The template repo and a project that uses it store files in different locations:

| Template repo | Real project |
|---|---|
| `AGENTS.template.md` or `AGENTS.md` | `AGENTS.md` (project root) |
| `.agents/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` |

Use this mapping when copying a generalized improvement from the real project back into the template repo.

---

## Workflow

### 1) Identify the candidate improvement in the real project
Ask:
- Does this change depend on project-specific knowledge (internal hostnames, domain rules, team conventions)?
- Would it make the template better for any project, or just this one?

If the answer is "any project" — it belongs in the template. If it's project-specific — it belongs only in `AGENTS.md` or the local skill copy.

### 2) Compare against the current template version when helpful
If the template repo is cloned locally, inspect the target file there directly.

If you only need a read-only comparison from inside the project repo, you may add and fetch a template remote after the user confirms the remote URL:
```bash
git remote add template <template-repo-url>
git fetch template
git show template/main:AGENTS.template.md
git show template/main:.agents/skills/<name>/SKILL.md
```

Use this for reference only. The actual template change should still be made in the separate template repo.

### 3) Strip project-specific content
Before contributing back, remove or replace:
- Internal service names, hostnames, URLs
- Business domain language specific to this project
- Examples that only make sense in this codebase

Replace with generic equivalents or placeholder examples.

### 4) Apply the change in the template repo
Open the separate local clone of the Codex template repo and edit the matching file there.

Examples:
- project `AGENTS.md` -> template `AGENTS.template.md` or `AGENTS.md`
- project `.agents/skills/<name>/SKILL.md` -> template `.agents/skills/<name>/SKILL.md`

Typical flow:
```bash
cd /path/to/codex-template
git checkout -b improve/<topic>
# apply the cleaned-up improvement
git add AGENTS.template.md .agents/skills/<name>/SKILL.md
git commit -m "feat(template): <description of improvement>"
git push origin improve/<topic>
```

If you do not have write access:
- Fork the template repo and open a pull request, or
- prepare a patch for the maintainer to apply in the template repo

In the PR or patch notes, describe:
- what improved,
- what prompted the change in the real project,
- what was stripped or generalized before upstreaming.

### 5) Update template indexes when needed
If the improvement affects the skills index or adds a new skill, also update:
- the `## Skills available` section in `AGENTS.template.md` or `AGENTS.md`
- remove the skill from `## Skills to add` if it was listed there
- the skills table in `README.md` when the change is user-visible

---

## Guardrails
- Never interpret this skill as "pull template changes into the project."
- Never push from the project repo directly into the template repo.
- Never contribute project-specific content to the template — sanitize first.
- Never overwrite the template with a raw project file without reviewing and cleaning it first.
- Use a template remote only for read-only comparison; use a separate clone for real template edits whenever possible.
- When in doubt about whether something is generalizable, leave it in the project and note it for later review.
