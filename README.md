# Claude Code Tools

Personal Claude Code skills and agents, synced across machines.

## Structure

```
.
├── CLAUDE.md          # Global instructions for all projects
├── agents/            # Custom agents (subagents)
│   └── <name>.md
└── skills/            # Custom skills (slash commands)
    └── <name>/
        └── SKILL.md
```

## Setup on a new machine

```bash
# One-liner: clone and run setup
git clone git@github.com:jkarenko/claude-tools.git ~/.claude-tools && ~/.claude-tools/setup.sh
```

The setup script will:
- Copy any existing local skills/agents into the repo (skips duplicates)
- Create symlinks from `~/.claude/` to the repo
- Warn you if there are new files to commit

To update later: `cd ~/.claude-tools && git pull`

## Current contents

### Agents
- `codebase-takeover-analyst` - Analyze codebases for team handovers
- `git-commit-writer` - Generate conventional commit messages
- `sensitive-data-scanner` - Scan for leaked secrets/PII
- `website-reverse-engineer` - Create specs from existing websites

### Skills
- `reverse-engineer` - Reverse engineer binary formats or code
