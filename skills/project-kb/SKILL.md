---
name: project-kb
description: Analyze an existing repository and build (or refresh) its project knowledge base as one-topic-per-file memories in <repo>/.claude/memory/ — where things are, how they are implemented, architecture, data model, dev workflow/deploy, caveats and code smells — then wire it into CLAUDE.md and report the findings. Use when the user says "build the knowledge base", "document this project for Claude", "/project-kb", "refresh the KB", or asks to analyze a repo's architecture and record it in project memory.
---

# Project KB

Turn a codebase into a maintained, in-repo knowledge base that Claude loads every session and that humans can read as onboarding docs. Output lives in the repo, not in `~/.claude`.

Modes: `/project-kb` (init — no KB yet), `/project-kb refresh` (KB exists; update it against HEAD), `/project-kb <dimension>` (add/refresh one topic, e.g. `data-model`).

## Ground rules (learned the hard way)

1. **The answer to the user is prose, not a file write.** After writing the KB, give a standalone summary of the findings in the chat reply (stack, architecture in two sentences, top caveats/smells, how deploy works). Never end the turn with only "memory updated".
2. **Scope discipline.** Nothing project-specific goes into `~/.claude/CLAUDE.md`, `~/.claude/settings.json` or `~/.claude/projects/*/memory`. Everything this skill writes goes under `<repo>/.claude/` (or `CLAUDE.md`/`AGENTS.md`/`.gitignore` at repo root).
3. **Repo-level voice.** Write facts about the repo, not about the user's relationship to it. No "the user's fork", "treat as inherited", "we"; no ways-of-working feedback (that lives in `~/.claude/CLAUDE.md`).
4. **Snapshot honesty.** Any file listing smells/gaps opens with `Snapshot as of <YYYY-MM-DD> (HEAD <sha>). Update as items are fixed.` Dates ISO. Say "not verified" when you inferred rather than read.
5. **Never overwrite an existing `CLAUDE.md`/`AGENTS.md`/`.gitignore`** — append. Never commit `.claude/settings.local.json`.
6. Don't create the KB from a fresh clone's guesswork: read the code. Prefer `Explore` agents over dumping files into context for anything above ~40 tracked files.

## Workflow

### 1. Survey (cheap, always)

```bash
git rev-parse --show-toplevel && git remote -v && git log --oneline | wc -l && git log -1 --format='%h %ad' --date=short
git ls-files | wc -l; git ls-files | sed 's#/[^/]*$##' | sort | uniq -c | sort -rn | head -30
ls -a; cat CLAUDE.md AGENTS.md README.md 2>/dev/null | head -150
ls .claude .claude/memory 2>/dev/null; cat .claude/settings.local.json 2>/dev/null
ls -d ../*/ 2>/dev/null   # siblings under the same parent dir
```

Decide: init vs refresh (does `.claude/memory/MEMORY.md` exist?). Detect the shape: single app / multi-service (`backend/` + `frontend/`) / library / data pipeline. Note **siblings** in the parent dir whose README/CLAUDE.md name this repo (shared DB, API consumer) — they get a cross-reference bullet in the overview.

Pick the **project slug** used as file prefix: the product name from `package.json`/`pyproject`/README title if it differs from the dir name (`toolshare-*` for repo `neighborhoodapp`), else the dir name.

### 2. Analyze by dimension

Core dimensions (always):

| file | covers |
|---|---|
| `<slug>-overview.md` | what it is, scale (files/commits/date range), stack + versions, live URL, remote, **repo layout with what lives where**, entry points, siblings. Entry point of the KB — links to all others. |
| `<slug>-architecture.md` | runtime pattern (SSR/CSR/BaaS/API+worker…), auth model, main data flows, cross-cutting conventions, what is deliberately absent |
| `<slug>-dev-workflow.md` | env vars & example files, scripts, local setup, tests (what exists, what needs live infra), CI, deploy path (who deploys what on which trigger; env var location), migration/schema application path |
| `<slug>-code-smells.md` | duplication, correctness/robustness risks, type-safety gaps, tooling/repo hygiene, security notes — each bullet concrete (file, symptom, why it matters) |

Conditional dimensions (add when the repo has the concern):

- `<slug>-data-model.md` (+ `-rls`/`-auth` when relevant) — tables/entities, relations, indexes, policies and their gaps
- `<slug>-design-system.md` — tokens, component library, layout conventions (frontends)
- `<slug>-pipeline.md` / `-ingestion.md` — stages, schedules, idempotency, state tables (data pipelines)
- `<slug>-api.md` — endpoints/contracts (services)
- `<slug>-eval.md` / `-rag.md` — evaluation setup, retrieval config (ML/LLM apps)

For repos > ~40 files, fan out **one `Explore` agent per dimension in a single message** with a prompt of the form: "Report facts for the `<dimension>` topic of a project KB: <bullets from the table above>. Cite `path:line`. Flag anything inferred rather than read. Return prose bullets, no file dumps." Then write the files yourself from their reports — you own consistency and cross-links.

For small repos read the key files directly (`Read`/`sed -n`), don't spawn agents for a 15-file pipeline.

### 3. Write the memory files

Format for every file (see `reference/memory-file-template.md`):

```markdown
---
name: <slug>-<dimension>
description: <one line — used to decide relevance during recall>
metadata:
  type: project
---

<dense bullets; backtick paths; `[[<slug>-other]]` links to related files>

Related: [[<slug>-overview]], [[…]].
```

- Prefer 15–40 lines per file; a topic that needs more should be split into two files, not padded.
- Concrete over generic: `list-item/page.tsx` and `item/[id]/edit/page.tsx` are near-identical forms → candidate for shared `ItemForm`, not "there is some duplication".
- Then `MEMORY.md` — the index, one line per file, no content:

```markdown
# <Product> (<repo dir>) knowledge base
Project-scoped technical/operational knowledge. Ways-of-working feedback lives in ~/.claude/CLAUDE.md, not here.
- [Overview & where things are](<slug>-overview.md) — stack, repo layout, entry point
- …
```

**Refresh mode:** read every existing file, verify each claim against HEAD (`git diff <old-sha>..HEAD --stat` narrows it), update/remove stale bullets, bump the snapshot line, add new files only for new concerns. Report what changed since the last snapshot in the chat reply.

### 4. Wire it in

- `CLAUDE.md`: ensure a line `@.claude/memory/MEMORY.md` exists (append; create the file if missing). If the repo has an existing `CLAUDE.md` with content, keep it — the KB complements it; move nothing.
- `.claude/settings.local.json` (machine-local, gitignored): ensure `"autoMemoryDirectory": "./.claude/memory"` — merge into existing JSON, don't clobber other keys.
- `.gitignore`: ensure `.claude/settings.local.json` is ignored (add under a `# claude code local (machine-specific) settings` comment).
- Optional, only if the user asked for shared conventions (as with the git-workflow section in AGENTS.md): append to `AGENTS.md`, never to the KB files.

Verify: `git status --short` shows only KB files + wiring; `git check-ignore .claude/settings.local.json` succeeds.

### 5. Report

Reply in prose, standalone: what the project is, stack, architecture in 2–3 sentences, how deploy works, the 3–5 most important caveats/smells, and which KB files were written. Then one trailing line on wiring/git state.

### 6. Git (follow repo conventions; never push or open a PR unasked)

- Branch `docs/claude-kb` (or `docs/claude-kb-refresh`) from up-to-date `main`.
- Stage KB files + `CLAUDE.md` + `.gitignore` (+ `AGENTS.md` if touched). **Not** `.claude/settings.local.json`.
- Commit `docs(claude): add <Product> knowledge base and wire it into CLAUDE.md` (refresh: `docs(claude): refresh <Product> knowledge base to <sha>`).
- Tell the user the branch is ready; pushing/PR happen only when asked. If `origin` is not the user's own account, mention that a fork remote may be needed for the PR and confirm before any remote action.
