# Memory file template and worked example

Every KB file: frontmatter + dense body + Related line. `type` is always `project` for KB files.

```markdown
---
name: <slug>-<dimension>
description: <one line: what this file tells you; used to decide relevance during recall>
metadata:
  type: project
---

Snapshot as of YYYY-MM-DD (HEAD abc1234). Update as items are fixed.   ← only for smells/gaps files

**Section heading**
- Concrete bullet: `path/to/file.ts` — symptom, why it matters, what to do about it.
- Another bullet — see [[<slug>-other-file]].

Related: [[<slug>-overview]], [[<slug>-architecture]].
```

## Worked example — overview file (ToolShare / neighborhoodapp, 2026-08-15)

```markdown
---
name: toolshare-overview
description: What the ToolShare (neighborhoodapp) project is, its stack, deployment, repo layout, and where things live — entry point of the project knowledge base
metadata:
  type: project
---

**ToolShare** (repo dir `neighborhoodapp`, package name `toolshare`) — a neighborhood tool-sharing marketplace: residents list tools to lend ("offer") or things they want ("request"), browse/filter, and message each other. Portfolio/demo-scale app, ~22 commits (2026-07-10 → 2026-07-22). Live demo: https://neighborhoodapp-xi.vercel.app/ . GitHub remote: `emilmanninen/neighborhoodapp`.

**Stack:** Next.js 16.2.10 (App Router, TS, all pages `'use client'`), React 19.2, Tailwind v4 (CSS-first `@theme inline` in `src/app/globals.css`), shadcn "base-vega" style on **@base-ui/react** (not Radix), Phosphor icons, Supabase JS v2 (auth + Postgres + Storage, **no `@supabase/ssr`**), Vitest 4, ESLint 9 flat config, Vercel hosting, GitHub Actions CI (lint → `vitest run src` → build with placeholder env).

**Layout (47 tracked files):**
- `src/app/*/page.tsx` — routes: `/` browse, `/login`, `/signup`, … `layout.tsx` = Inter font + globals.css only.
- `src/components/` — `AppHeader`, `ItemCard` (+ exported `Item` type), `CategoryIcon`, `ConversationSidebar`; `ui/` = shadcn button/badge/input/label/textarea.
- `src/lib/` — `supabaseClient.ts` (singleton browser client), `categories.ts`, `filterItems.ts` (+ only unit test), `formatRelativeTime.ts`, `utils.ts` (`cn`).
- Root: `schema.sql` (tables, trigger, RLS), `storage_policies.sql`, `seed.mjs`, `tests/rls.test.ts` (integration), `.env.local.example`, `.github/workflows/ci.yml`.

Related: [[toolshare-architecture]], [[toolshare-data-model-rls]], [[toolshare-code-smells]], [[toolshare-dev-workflow]], [[toolshare-design-system]].
```

## MEMORY.md example

```markdown
# ToolShare (neighborhoodapp) knowledge base
Project-scoped technical/operational knowledge. Ways-of-working feedback lives in ~/.claude/CLAUDE.md, not here.
- [Overview & where things are](toolshare-overview.md) — stack, repo layout, entry point
- [Architecture](toolshare-architecture.md) — BaaS/client-only pattern, auth guards, data flows
- [Data model & RLS](toolshare-data-model-rls.md) — schema, policies, and their gaps
- [Code smells & tech debt](toolshare-code-smells.md) — duplication, races, tooling gaps
- [Dev workflow](toolshare-dev-workflow.md) — env, scripts, Supabase setup, CI, deploy
- [Design system](toolshare-design-system.md) — tokens, shadcn/base-ui, layout conventions
```

Full reference implementation: `~/code/emilmanninen/neighborhoodapp/.claude/memory/`.
