---
name: pof-progress
description: Show current POF workflow progress. Displays current phase, completed work, and what's next.
---

# POF Progress

Display the current state of the POF workflow.

## Usage

When user asks "where are we?" or wants a status update.

## Process

1. Read `.claude/context/project.json` for project name and ID (if exists)
2. Read `.claude/context/.active-session` to get the current session ID
3. Read `.claude/context/sessions/{id}.json` for session state
4. Read `.claude/context/decisions.json`
5. Present current status with project context
6. List all stories with their statuses (active, planned, completed)

## Output Format

```markdown
## POF Progress

**Project**: {project name} ({projectId})
**Current Phase**: {phase number} - {phase name}
**Status**: {in_progress/blocked/waiting_for_input}

### Stories
| Status | Story | Session | Phase |
|--------|-------|---------|-------|
| ▶ active | filter products | pof-b7e2 | 4.2 |
| ⏸ paused | reset password | pof-c4d1 | 2.4 |
| 📋 planned | export CSV | pof-d9e3 | — |
| ✓ done | user login | pof-e1f4 | — |

### Phase Map (active session)

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

## Session File

Read from `.claude/context/sessions/{id}.json`:
```json
{
  "id": "pof-a3f8",
  "type": "kickoff",
  "currentPhase": "2.3",
  "status": "in_progress",
  "lastCheckpoint": "1.5",
  "blockers": [],
  "verbose": false,
  "createdAt": "...",
  "lastActivity": "...",
  "project": "...",
  "story": null
}
```

## If No Active Session

If `.claude/context/.active-session` doesn't exist or `.claude/context/sessions/` is empty:

```markdown
## POF Progress

**Status**: Not started

No POF workflow is currently active. Use `/pof-kickoff` to start a new workflow or `/pof-resume` if there's existing context.
```

## Quick Status

For inline progress during work, use the format:
```
// pof-{agent} is {action}
```

This skill is for detailed status reports when user asks.
