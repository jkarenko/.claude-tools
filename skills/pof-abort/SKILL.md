---
name: pof-abort
description: Gracefully stop the POF workflow. Preserves state for later resume.
---

# POF Abort

Gracefully stop the POF workflow while preserving state.

## When to Use

- User needs to stop working
- Workflow is going in wrong direction
- Need to pause and reconsider
- Switching to different task

## Process

### 1. Confirm Abort

```markdown
## Abort POF Workflow?

**Current phase**: {phase}
**Current step**: {step}

This will:
- ✓ Save current state for later resume
- ✓ Preserve all decisions and ADRs
- ✓ Keep all generated code
- ✗ Stop any running agents

**To resume later**: Use `/pof-resume`

Confirm abort? (yes/no)
```

### 2. Save State

Read `.claude/context/.active-session` to get the session ID, then update `.claude/context/sessions/{id}.json`:
- Set `status` to `"paused"`
- Add `pausedAt` with current ISO timestamp
- Set `lastActivity` to current timestamp

### 3. Cleanup

- Stop any background agents
- Ensure files are saved
- Commit any pending changes (ask first)

### 4. Confirm

```markdown
## POF Workflow Paused

State saved. To resume:
```bash
# In this project directory
/pof-resume
```

### Preserved
- Phase: {phase}
- Decisions: {N} recorded
- ADRs: {N} written
- Code: All changes saved

### Not Committed
{List any uncommitted changes, if any}
```

## Hard Abort

If user wants to discard everything:

```markdown
## Hard Abort

⚠️ This will discard all POF context (but not code changes).

**Will delete:**
- `.claude/context/` directory
- Workflow state

**Will keep:**
- All code files
- ADRs in `docs/adr/`
- Git history

Are you sure? (yes, discard/no, soft abort)
```

If confirmed:
```bash
rm -rf .claude/context/sessions/ .claude/context/.active-session
```

## Abort Reasons

Optionally record why:
```markdown
**Why are you aborting?** (optional, helps improve workflow)
1. Need to stop for now
2. Going in wrong direction
3. Requirements changed
4. Other: {free text}
```

This can be logged for workflow improvement.
