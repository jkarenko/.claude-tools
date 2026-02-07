---
name: pof-guide
description: Quick reference for POF commands and when to use them.
---

# POF Quick Reference Guide

## What to Use When

| Situation | Command | Description |
|-----------|---------|-------------|
| **Starting fresh** | `/pof:kickoff` | New project → setup → architecture → build |
| **Adding a feature** | `/pof:story <story>` | User story → design → implement → commit |
| **Resuming work** | `/pof:resume` | Continue interrupted workflow |
| **Check status** | `/pof:progress` | See current phase and next steps |
| **See all phases** | `/pof:phase-outline` | Full phase structure |
| **Disagree with suggestion** | `/pof:override` | Override agent recommendation |
| **See other options** | `/pof:alternatives` | Alternative approaches |
| **Pause work** | `/pof:abort` | Save state, stop workflow |
| **More detail** | `/pof:verbose` | Toggle detailed explanations |

## Typical Workflows

### New Project
```
/pof:kickoff
→ Git init + answer requirements questions
→ Approve phase outline
→ Architecture phase runs (agents dispatched inline)
→ Approve architecture
→ Design phase runs
→ Approve design
→ Scaffolding + commit
→ Implementation (code → test → commit per feature)
→ Security review
→ Deployment (if applicable)
→ Done
```

The entire flow is seamless after kickoff — no need to run separate commands between phases.

### Adding Features (After Initial Setup)
```
/pof:story As a user, I want to export data as CSV
→ Review UX recommendations
→ Approve implementation plan
→ Implementation runs (commit per feature)
→ Done
```

### Quick Bug Fix
```
/pof:story --quick Fix timezone display in dashboard
→ Approve plan
→ Implementation + commit
→ Done
```

### Continuing Next Day
```
/pof:resume
→ See where you left off
→ Approve to continue
→ Workflow resumes inline
```

## When NOT to Use POF

- Single-line fixes → Just do it
- Typos and formatting → Just do it
- Exploratory research → Just ask
- Questions about code → Just ask

POF is for structured development with documentation, not every interaction.

## Key Concepts

**Inline Orchestration**: All phases run directly in the conversation. Specialist agents are dispatched for focused tasks (validation, planning, commits) but the workflow logic stays in the main conversation where you can interact.

**Dashboard** (optional): Real-time monitoring at `http://localhost:3456`. Started automatically by kickoff. Shows agent activity, phase progress, and pending questions. Works without it — purely additive.

**Checkpoints**: Points where POF pauses for your approval:
- Architecture decisions
- Design decisions
- Implementation plans
- Deployment actions

**TDD in Development**: Phase 4.2 follows a test-driven cycle: write unit tests first (`pof-test-writer`), then implement to make them pass, then run tests (`pof-test-runner`), then commit. Integration tests are a separate step after all features. E2E is used sparingly and only when relevant.

**Feature-Level Commits**: Every implemented feature gets its own conventional commit (`type(scope): description`), not just one commit at the end. Both test and implementation files are committed together.

**ADRs**: Architecture Decision Records in `docs/adr/`. Created automatically for significant decisions. Permanent documentation of why choices were made.

**State**: Workflow state in `.claude/context/`:
- `state.json` - Current phase
- `decisions.json` - Decisions made
- `architecture.md` - Approved architecture
- `implementation-plan.md` - Current plan
- `current-story.md` - Active story (if using /pof:story)

## Tips

1. **Be specific in stories** - Include acceptance criteria
2. **Review plans before approving** - Catch issues early
3. **Use --quick for small stuff** - Skip UX review when not needed
4. **Check /pof:progress if lost** - See where you are
5. **Stories are archived** - Build project history over time
6. **Dashboard is optional** - Open it for visibility, close it when not needed
