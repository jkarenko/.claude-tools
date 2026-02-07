# Claude Code Tools

Personal Claude Code skills and agents, synced across machines.

## Structure

```
.
├── CLAUDE.md          # Global instructions for all projects
├── agents/            # Custom agents (subagents)
│   └── <name>.md
├── skills/            # Custom skills (slash commands)
│   └── <name>/
│       └── SKILL.md
├── dashboard/         # POF real-time monitoring dashboard
│   ├── server.ts      # Bun HTTP server + SSE
│   └── index.html     # Single-page UI (zero deps)
└── templates/         # POF context templates
    ├── context/       # Workflow state templates
    └── adr/           # ADR templates
```

## Setup on a new machine

```bash
# Option 1: curl
curl -fsSL https://raw.githubusercontent.com/jkarenko/.claude-tools/main/setup.sh | bash

# Option 2: git clone
git clone git@github.com:jkarenko/.claude-tools.git ~/.claude-tools && ~/.claude-tools/setup.sh
```

The setup script will:
- Copy any existing local skills/agents into the repo (skips duplicates)
- Create symlinks from `~/.claude/` to the repo
- Warn you if there are new files to commit

To update later: `cd ~/.claude-tools && git pull`

---

## POF: Project Orchestration Flow

A workflow system for orchestrated project development. POF manages multi-phase projects with specialist agents, user checkpoints, real-time monitoring, and continuous documentation.

### Workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│  /pof-kickoff                                                        │
│                                                                      │
│  Detect project state ─► Git init ─► Gather requirements             │
│  ─► Create .claude/context/ ─► Start dashboard ─► Initial commit     │
│  ─► Present phase outline ─► CHECKPOINT 0.4                          │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ user approves
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 1: ARCHITECTURE (inline orchestration)                        │
│                                                                      │
│  ┌─────────────────┐   ┌────────────────────────┐                   │
│  │ stack-validator  │──►│ architecture-advisor    │                   │
│  │ (validate stack) │   │ (analyze, recommend)    │                   │
│  └─────────────────┘   └───────────┬────────────┘                   │
│                                     ▼                                │
│                         Write architecture.md                        │
│                         ─► CHECKPOINT 1.5 ─► ADR + COMMIT            │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ user approves
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 2: DESIGN                                                     │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ ux-designer      │──► UX patterns, accessibility, components      │
│  └─────────────────┘    ─► CHECKPOINT 2.4 ─► ADR + COMMIT           │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ user approves
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 3: SCAFFOLDING (green-field only)                             │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │ scaffolder       │──► Initialize project ─► Install deps          │
│  └─────────────────┘    ─► Verify ─► COMMIT                         │
└──────────────────┬───────────────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 4: IMPLEMENTATION                                             │
│                                                                      │
│  ┌──────────────────────┐                                           │
│  │ implementation-       │──► Create task plan                       │
│  │ planner              │    ─► CHECKPOINT 4.1                       │
│  └──────────────────────┘                                           │
│                                                                      │
│  For each task in plan (TDD):                                        │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │ test-writer  │─►│ Write    │─►│ test-runner  │─►│ git-committer │ │
│  │ (tests first)│  │ code     │  │ (verify)     │  │ (commit)      │ │
│  └─────────────┘  └──────────┘  └─────────────┘  └──────────────┘ │
│                                                                      │
│  ┌───────────────────┐                                              │
│  │ security-reviewer  │──► Review all changes                        │
│  └───────────────────┘    ─► CHECKPOINT 4.4                          │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ user approves
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 5: DEPLOYMENT                                                 │
│                                                                      │
│  CHECKPOINT 5.2 ─► deployer ─► Verify ─► ADR + COMMIT               │
└──────────────────┬───────────────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PHASE 6: HANDOFF                                                    │
│                                                                      │
│  Finalize docs ─► ADR index ─► Summary ─► Final COMMIT              │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Inline orchestration**: All phases run in the main conversation where the user can interact. Specialist agents are dispatched for focused work and return results.
- **TDD development cycle**: Phase 4.2 follows test-driven development: write unit tests first, implement to make them pass, verify, commit. Integration tests are a separate step. E2E is used sparingly.
- **Feature-level commits**: Every feature gets its own conventional commit (`type(scope): description`), not one big commit at the end.
- **Git from the start**: `git init` happens at kickoff. Context files are committed immediately.
- **Dashboard is optional**: Real-time monitoring at `localhost:3456`. Agents report progress via `curl` that silently no-ops if the dashboard isn't running.
- **Checkpoints**: User must approve architecture, design, implementation plans, and deployment before proceeding.

### Quick Start

```bash
# New project — full workflow
/pof-kickoff

# Add a feature to existing project
/pof-story As a user, I want to filter products by category

# Quick bug fix
/pof-story --quick Fix timezone display in dashboard

# Resume interrupted workflow
/pof-resume
```

### Story Flow (feature development)

```
/pof-story As a user, I want...
    │
    ▼
Parse story ─► Load project context
    │
    ▼
┌─────────────┐    ┌──────────────────────┐
│ ux-designer  │──►│ implementation-planner │
│ (patterns)   │   │ (task breakdown)       │
└─────────────┘    └──────────┬───────────┘
                              │ user approves plan
                              ▼
              For each task: write test ─► code ─► run test ─► commit
                              │
                              ▼
              Security review ─► Archive story ─► Done
```

### POF Skills (16)

| Skill | Purpose |
|-------|---------|
| `/pof-kickoff` | Start a new workflow (git init, setup, auto-continues) |
| `/pof-orchestrate` | Drive workflow phases inline |
| `/pof-story` | Add a feature via user story |
| `/pof-resume` | Resume paused workflow |
| `/pof-progress` | Show current phase and status |
| `/pof-phase-outline` | Show all phases and sub-steps |
| `/pof-checkpoint` | Present approval checkpoint |
| `/pof-clarify` | Ask structured clarifying questions |
| `/pof-alternatives` | Present multiple options |
| `/pof-override` | Override a recommendation |
| `/pof-sources` | Manage documentation sources |
| `/pof-verbose` | Toggle detailed explanations |
| `/pof-env-config` | Manage environment variables |
| `/pof-abort` | Gracefully stop workflow |
| `/pof-rollback` | Show rollback options |
| `/pof-guide` | Quick reference for all commands |

### POF Agents (14)

| Agent | Purpose | Auto-accept |
|-------|---------|-------------|
| `pof-orchestrator` | Workflow coordination (reference/fallback) | N/A |
| `pof-stack-validator` | Technology compatibility checks | Yes |
| `pof-architecture-advisor` | Tech analysis and recommendations | No |
| `pof-ux-designer` | Accessibility and UX patterns | No |
| `pof-implementation-planner` | Task breakdown and sequencing | No |
| `pof-scaffolder` | Project structure initialization | No |
| `pof-git-committer` | Conventional commits | Yes (commit) |
| `pof-test-writer` | Write unit tests before implementation (TDD) | Yes |
| `pof-test-runner` | Test execution and reporting | Yes |
| `pof-security-reviewer` | Security vulnerability analysis | No |
| `pof-deployer` | Deployment to infrastructure | No |
| `pof-adr-writer` | Architecture Decision Records | Yes |
| `pof-doc-researcher` | Documentation lookup | Yes |
| `pof-error-handler` | Failure diagnosis and recovery | No |

All agents report progress to the dashboard via `curl` (silently no-ops if dashboard not running).

### Dashboard

Real-time monitoring UI for the POF workflow. Supports multiple simultaneous sessions — each Claude Code conversation gets its own session ID, and the dashboard shows all active sessions in a sidebar.

```bash
# Start manually (kickoff starts it automatically)
bun run ~/.claude-tools/dashboard/server.ts

# View at
open http://localhost:3456
```

Features:
- **Multi-session sidebar** — switch between active sessions, see project name, phase, and agent count at a glance
- Phase progress stepper per session
- Agent cards with live status and colors
- Activity log with timestamps
- Question/answer panel for async two-way communication
- Auto-reconnecting SSE stream
- Stale sessions auto-expire after 4 hours of inactivity

API endpoints (all accept `session` field for routing):
- `POST /api/status` — agent progress reports
- `POST /api/question` — post a question for the user
- `POST /api/answer` — user answers from the UI
- `GET /api/events` — SSE stream for real-time updates
- `GET /api/state?session=ID` — full state snapshot
- `GET /api/sessions` — summary of all active sessions
- `GET /health` — uptime check

### After Completion

When the workflow finishes (Phase 6 or story completion), POF presents a summary with next-steps options. The conversation stays open — you can add features, fix bugs, or ask questions without restarting. In a new session, use `/pof-resume` to pick up where you left off.

Deployment (Phase 5) is optional — if your project doesn't need it, POF offers to skip straight to handoff.

### Context Files

POF maintains state in `.claude/context/`:

| File | Purpose |
|------|---------|
| `state.json` | Current phase, status, mode, session ID |
| `decisions.json` | Recorded architectural decisions |
| `requirements.md` | Project requirements |
| `architecture.md` | Approved architecture |
| `implementation-plan.md` | Current implementation plan |
| `current-story.md` | Active user story |
| `stories/` | Archived completed stories |

### ADR Convention

POF uses Nygard-style ADRs in `docs/adr/`:
- One decision per ADR
- Format: `NNNN-short-kebab-title.md`
- Sections: Context, Decision, Consequences
- Bidirectional superseded linking

---

## Other Skills

| Skill | Purpose |
|-------|---------|
| `/commit` | Create a conventional commit from staged changes |
| `/reverse-engineer` | Reverse engineer binary formats or code |

## Other Agents

- `codebase-takeover-analyst` — Analyze codebases for team handovers
- `sensitive-data-scanner` — Scan for leaked secrets/PII
- `website-reverse-engineer` — Create specs from existing websites
