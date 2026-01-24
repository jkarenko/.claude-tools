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

A comprehensive workflow system for orchestrated project development. POF manages complex multi-step objectives with parallel execution, checkpoints, and continuous documentation.

### Quick Start

```bash
# In your project directory
/pof:kickoff
```

### POF Skills (14)

| Skill | Purpose |
|-------|---------|
| `/pof:kickoff` | Start a new workflow |
| `/pof:orchestrate` | Launch the orchestrator agent |
| `/pof:progress` | Show current phase and status |
| `/pof:checkpoint` | Present approval checkpoint |
| `/pof:clarify` | Ask structured clarifying questions |
| `/pof:alternatives` | Present multiple options |
| `/pof:sources` | Manage documentation sources |
| `/pof:override` | Override a recommendation |
| `/pof:verbose` | Toggle detailed explanations |
| `/pof:env-config` | Manage environment variables |
| `/pof:phase-outline` | Show all phases |
| `/pof:resume` | Resume paused workflow |
| `/pof:abort` | Gracefully stop workflow |
| `/pof:rollback` | Show rollback options |

### POF Agents (13)

| Agent | Purpose | Auto-accept |
|-------|---------|-------------|
| `pof-orchestrator` | Workflow coordination | N/A |
| `pof-doc-researcher` | Documentation lookup | Yes |
| `pof-architecture-advisor` | Tech analysis | No |
| `pof-stack-validator` | Compatibility checks | Yes |
| `pof-ux-designer` | Accessibility/UX | No |
| `pof-implementation-planner` | Task breakdown | No |
| `pof-adr-writer` | ADR documentation | Yes |
| `pof-git-committer` | Conventional commits | Yes (commit) |
| `pof-test-runner` | Test execution | Yes |
| `pof-security-reviewer` | Security analysis | No |
| `pof-deployer` | Deployment | No |
| `pof-error-handler` | Failure recovery | No |
| `pof-scaffolder` | Project setup | No |

### POF Phases

```
PHASE 0: INITIALIZATION → CHECKPOINT
PHASE 1: ARCHITECTURE → CHECKPOINT + ADR
PHASE 2: DESIGN → CHECKPOINT + ADR
PHASE 3: SCAFFOLDING → COMMIT
PHASE 4: IMPLEMENTATION → CHECKPOINT
PHASE 5: DEPLOYMENT → CHECKPOINT + ADR
PHASE 6: HANDOFF
```

### Context Files

POF maintains state in `.claude/context/`:
- `state.json` - Current phase and status
- `decisions.json` - Recorded decisions
- `requirements.md` - Project requirements
- `architecture.md` - Approved architecture
- `sources.json` - Documentation sources

### ADR Convention

POF uses Nygard-style ADRs in `docs/adr/`:
- One decision per ADR
- Format: `NNNN-short-kebab-title.md`
- Sections: Context, Decision, Consequences

---

## Other Agents

- `codebase-takeover-analyst` - Analyze codebases for team handovers
- `git-commit-writer` - Generate conventional commit messages
- `sensitive-data-scanner` - Scan for leaked secrets/PII
- `website-reverse-engineer` - Create specs from existing websites

## Other Skills

- `reverse-engineer` - Reverse engineer binary formats or code
