---
name: pof-progress
description: Show current POF workflow progress. Displays current phase, completed work, and what's next.
---

# POF Progress

Display the current state of the POF workflow.

## Usage

When user asks "where are we?" or wants a status update.

## Process

1. Read `.claude/context/state.json`
2. Read `.claude/context/decisions.json`
3. Present current status

## Output Format

```markdown
## POF Progress

**Current Phase**: {phase number} - {phase name}
**Status**: {in_progress/blocked/waiting_for_input}

### Phase Map

PHASE 0: INITIALIZATION ✓
PHASE 1: ARCHITECTURE ✓
PHASE 2: DESIGN ◀ Current (2.3)
├── 2.1 UX/accessibility patterns ✓
├── 2.2 Component structure ✓
├── 2.3 Data flow design ← In progress
└── 2.4 Design approval
PHASE 3: SCAFFOLDING
PHASE 4: IMPLEMENTATION
PHASE 5: DEPLOYMENT
PHASE 6: HANDOFF

### Recent Decisions
| ID | Decision | Phase |
|----|----------|-------|
| d003 | Use Zustand for state | 2.2 |
| d002 | Component-first architecture | 2.1 |

### Blockers
{Any current blockers, or "None"}

### Next Step
{What happens next}
```

## State File

Read from `.claude/context/state.json`:
```json
{
  "currentPhase": "2.3",
  "status": "in_progress",
  "blockers": [],
  "lastCheckpoint": "1.5",
  "progressStyle": "inline-persistent",
  "verbose": false
}
```

## If No State File

If `.claude/context/state.json` doesn't exist:

```markdown
## POF Progress

**Status**: Not started

No POF workflow is currently active. Use `/pof:kickoff` to start a new workflow or `/pof:resume` if there's existing context.
```

## Quick Status

For inline progress during work, use the format:
```
// pof-{agent} is {action}
```

This skill is for detailed status reports when user asks.
