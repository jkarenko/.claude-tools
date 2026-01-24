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
# Clone the repo
git clone git@github.com:USERNAME/claude-tools.git ~/.claude-tools

# Create symlinks
ln -sf ~/.claude-tools/skills ~/.claude/skills
ln -sf ~/.claude-tools/agents ~/.claude/agents
ln -sf ~/.claude-tools/CLAUDE.md ~/.claude/CLAUDE.md
```

## Current contents

### Agents
- `codebase-takeover-analyst` - Analyze codebases for team handovers
- `git-commit-writer` - Generate conventional commit messages
- `sensitive-data-scanner` - Scan for leaked secrets/PII
- `website-reverse-engineer` - Create specs from existing websites

### Skills
- `reverse-engineer` - Reverse engineer binary formats or code
