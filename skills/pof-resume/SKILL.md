---
name: pof-resume
description: Resume a paused POF workflow from saved state. Reads context and continues from last checkpoint.
---

# POF Resume

Resume a POF workflow from saved state.

## When to Use

- Continuing work in a new session
- After a break in the workflow
- Recovering from an interrupted session

## Process

### 1. Check for Existing State

```bash
cat .claude/context/state.json 2>/dev/null
```

If no state file exists:
```markdown
No POF workflow state found. Use `/pof:kickoff` to start a new workflow.
```

### 2. Load Context

Read all context files:
- `.claude/context/state.json` - Current phase and status
- `.claude/context/decisions.json` - Decisions made
- `.claude/context/requirements.md` - Original requirements
- `.claude/context/architecture.md` - Approved architecture (if exists)
- `.claude/context/implementation-plan.md` - Implementation plan (if exists)

### 3. Present Resume Summary

```markdown
## Resuming POF Workflow

**Last active**: {timestamp from state.json or file mtime}
**Current phase**: {phase number} - {phase name}
**Last checkpoint**: {checkpoint}
**Status**: {status}

### Context Loaded
- ✓ Requirements
- ✓ Decisions ({N} recorded)
- {✓/✗} Architecture
- {✓/✗} Implementation plan

### Recent Decisions
| ID | Decision | Phase |
|----|----------|-------|
| {id} | {summary} | {phase} |

### Blockers (if any)
{blockers or "None"}

### Ready to Continue?
The workflow will resume from **{current step}**.

Proceed? (yes/no/review)
```

### 4. Handle Response

**"yes"**: Launch orchestrator with `/pof:orchestrate`

**"no"**: Ask what they want to do instead

**"review"**: Show more detailed state, allow modifications

## State Recovery

If state is corrupted or incomplete:

```markdown
## State Recovery Needed

The workflow state appears incomplete. Options:

1. **Reconstruct from ADRs**: Read docs/adr/ to rebuild decisions
2. **Start fresh**: Run `/pof:kickoff` (preserves existing code)
3. **Manual fix**: Edit `.claude/context/state.json` directly

What would you like to do?
```

## Partial Resume

If resuming mid-step:

```markdown
## Partial Step Resume

You were in the middle of **{step}** when the session ended.

Options:
1. **Restart step**: Begin {step} from scratch
2. **Continue**: Attempt to continue from where we left off
3. **Skip**: Mark as complete and move to next step

What would you like to do?
```
