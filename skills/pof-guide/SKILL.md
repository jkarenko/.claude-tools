---
name: pof-guide
description: Quick reference for POF commands and when to use them.
---

# POF Quick Reference Guide

## What to Use When

| Situation | Command | Description |
|-----------|---------|-------------|
| **Starting fresh** | `/pof:kickoff` | New project or major new system |
| **Adding a feature** | `/pof:story <story>` | User story → design → implement |
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
→ Answer requirements questions
→ Approve phase outline
/pof:orchestrate
→ Approve architecture
→ Approve design
→ Implementation runs
→ Approve deployment
→ Done
```

### Adding Features (After Initial Setup)
```
/pof:story As a user, I want to export data as CSV
→ Review UX recommendations
→ Approve implementation plan
→ Implementation runs
→ Done
```

### Quick Bug Fix
```
/pof:story --quick Fix timezone display in dashboard
→ Approve plan
→ Done
```

### Continuing Next Day
```
/pof:resume
→ See where you left off
→ Approve to continue
→ Workflow resumes
```

## When NOT to Use POF

- Single-line fixes → Just do it
- Typos and formatting → Just do it
- Exploratory research → Just ask
- Questions about code → Just ask

POF is for structured development with documentation, not every interaction.

## Key Concepts

**Checkpoints**: Points where POF pauses for your approval
- Architecture decisions
- Design decisions
- Implementation plans
- Deployment actions

**ADRs**: Architecture Decision Records in `docs/adr/`
- Created automatically for significant decisions
- Permanent documentation of why choices were made

**State**: Workflow state in `.claude/context/`
- `state.json` - Current phase
- `decisions.json` - Decisions made
- `current-story.md` - Active story (if using /pof:story)

## Tips

1. **Be specific in stories** - Include acceptance criteria
2. **Review plans before approving** - Catch issues early
3. **Use --quick for small stuff** - Skip UX review when not needed
4. **Check /pof:progress if lost** - See where you are
5. **Stories are archived** - Build project history over time
