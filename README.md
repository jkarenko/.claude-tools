# Claude Code Tools

Personal Claude Code skills and agents, synced across machines.

## Structure

```
.
├── CLAUDE.md               # Global instructions for all projects
├── settings.template.json  # ~/.claude/settings.json seed (copied on first install, never overwritten)
├── setup.sh                # Installer / updater (see below)
├── agents/                 # Custom agents (subagents)
│   └── <name>.md
├── skills/                 # Custom skills (slash commands)
│   └── <name>/
│       └── SKILL.md
└── scripts/                # Helper scripts skills call via ~/.claude/scripts/<file>
```

Private skills, scripts and CLAUDE.md rules live in a **private companion repo**,
`jkarenko/.claude-tools-gofore` (same `skills/` + `scripts/` layout plus a `CLAUDE.md`). `setup.sh`
clones it too when you have access, merges both repos into `~/.claude/skills/` and `~/.claude/scripts/`
as per-entry symlinks, and links its `CLAUDE.md` as `~/.claude/CLAUDE.private.md`, which the public
`CLAUDE.md` imports. Nothing from it is needed for the public tools to work.

## Setup on a new machine

```bash
# Option 1: curl
curl -fsSL https://raw.githubusercontent.com/jkarenko/.claude-tools/main/setup.sh | bash

# Option 2: git clone
git clone git@github.com:jkarenko/.claude-tools.git ~/.claude-tools && ~/.claude-tools/setup.sh
```

The setup script will:
- Clone (or pull) this repo to `~/.claude-tools`, and the private companion repo to
  `~/.claude-tools-gofore` if you have access (skip it with `CLAUDE_TOOLS_PRIVATE=0`)
- Adopt any pre-existing local skills/agents/CLAUDE.md into the repo (skips duplicates, backs up originals)
- Make `~/.claude/skills/` and `~/.claude/scripts/` union directories of per-entry symlinks into both repos
- Symlink `~/.claude/agents` and `~/.claude/CLAUDE.md` to this repo
- Link `~/.claude/CLAUDE.private.md` to the private repo's `CLAUDE.md`, or create it as an empty
  placeholder so the import in `CLAUDE.md` always resolves
- Seed `~/.claude/settings.json` from `settings.template.json` on first install (Claude Code rewrites
  that file itself, so it is copied, not linked; later runs only warn when it drifts from the template)
- Warn you if either repo has uncommitted changes

To update later: rerun `~/.claude-tools/setup.sh` (pulls both repos and refreshes links), or just
`git pull` in each repo if no skills were added/removed.

## Skills

| Skill | Purpose |
|-------|---------|
| `/auto-transcribe` | Transcribe a meeting recording into a speaker-labelled transcript with diarization and voice recognition |
| `/commit` | Create a conventional commit from staged changes |
| `/project-kb` | Build or refresh a repo's project knowledge base in `.claude/memory/` |
| `/reverse-engineer` | Reverse engineer binary formats or code |
| `/translate-file` | Translate a file while preserving its structure |

## Agents

- `codebase-takeover-analyst` — Analyze codebases for team handovers
- `sensitive-data-scanner` — Scan for leaked secrets/PII
- `website-reverse-engineer` — Create specs from existing websites
