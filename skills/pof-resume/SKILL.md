---
name: pof-resume
description: Resume a paused POF workflow from saved state. Reads context and continues from last checkpoint.
---

# POF Resume

Resume a POF workflow from saved state. Supports multiple sessions and migration from legacy state files.

## When to Use

- Continuing work in a new session
- After a break in the workflow
- Recovering from an interrupted session
- Switching between parallel stories/workflows

## Process

### 1. Check for Sessions

Check for the `sessions/` directory first. If it exists, list all `.json` files in `.claude/context/sessions/`.

If no `sessions/` directory exists but `.claude/context/state.json` does exist, perform **migration** (see Migration section below).

If neither exists:
```markdown
No POF workflow state found. Use `/pof-kickoff` to start a new workflow.
```

### 2. Present Session List

Read `.claude/context/project.json` if it exists to get the project name. Read each session `.json` file and group sessions by project.

Present sessions grouped by project name:

```markdown
## Available Sessions

### podcast-processor (proj-a3f8)

| # | ID | Type | Phase | Status | Last Activity | Story |
|---|-----|------|-------|--------|---------------|-------|
| 1 | pof-a3f8 | kickoff | 4.2 | in_progress | 2h ago | — |
| 2 | pof-b7e2 | story | 2.4 | paused | 1d ago | filter products |
| 3 | pof-c4d1 | story | planned | planned | 5h ago | export CSV |
| 4 | pof-d9e3 | story | idle | completed | 3d ago | reset password |

Which session to resume? (number, or "new" for /pof-kickoff)
```

For story sessions, show `session.story.title` in the Story column. For kickoff sessions, show `—`.

**Planned stories**: Show them in the list with status "planned". If the user selects a planned story:
1. Update the session file: set `status` to `"in_progress"`, `currentPhase` to `"design"`
2. Write the session ID to `.claude/context/.active-session`
3. Continue with the story flow from Step 4 of `/pof-story` (dispatch UX designer)

If sessions don't have a `projectId` field, group them under "Unknown project".

### 3. Select Session

If only **one** non-completed session exists, auto-select it and inform the user.

Otherwise, wait for user to pick a session number.

Write the selected session ID to `.claude/context/.active-session`.

### 4. Load Context

Read the selected session file and all relevant context files:
- `.claude/context/sessions/{id}.json` - Session state
- `.claude/context/decisions.json` - Decisions made
- `.claude/context/requirements.md` - Original requirements
- `.claude/context/architecture.md` - Approved architecture (if exists)
- `.claude/context/sessions/{id}-plan.md` - Implementation plan (if exists)

### 5. Start Dashboard

Start the dashboard if not already running:

```bash
curl -sf http://localhost:3456/health > /dev/null 2>&1 || \
  bun run ~/.claude-tools/dashboard/server.ts > /dev/null 2>&1 &
```

If dashboard is already running, skip. If it starts, inform the user.

Register the session with the dashboard:

```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<session id>","status":"started","message":"Resuming from phase <X.X>","detail":"project:<project name>","projectId":"<projectId>","sessionType":"<kickoff|story>","storyTitle":"<story title if story>","storyStatus":"<session status>"}' \
  > /dev/null 2>&1 || true
```

### 6. Present Resume Summary

```markdown
## Resuming POF Workflow

**Session**: {id}
**Type**: {kickoff/story}
**Last active**: {lastActivity timestamp}
**Current phase**: {phase number} - {phase name}
**Last checkpoint**: {checkpoint}
**Status**: {status}
{if story: **Story**: {story.title}}

### Context Loaded
- {check} Requirements
- {check} Decisions ({N} recorded)
- {check/cross} Architecture
- {check/cross} Implementation plan

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

### 7. Handle Response

**"yes"**: Update session `lastActivity` to current timestamp. Continue directly with the `/pof-orchestrate` instructions — read session, determine phase, and proceed inline. **Do not** spawn a subagent.

**"no"**: Ask what they want to do instead.

**"review"**: Show more detailed state, allow modifications.

## Migration (from legacy state.json)

When `/pof-resume` finds `.claude/context/state.json` but no `.claude/context/sessions/` directory:

1. Create `sessions/` directory:
   ```bash
   mkdir -p .claude/context/sessions
   ```

2. Read old `state.json` and create `sessions/pof-migr.json`:
   ```json
   {
     "id": "pof-migr",
     "type": "<'story' if state.mode === 'story', else 'kickoff'>",
     "currentPhase": "<from state.currentPhase>",
     "status": "<from state.status>",
     "lastCheckpoint": "<from state.lastCheckpoint>",
     "blockers": "<from state.blockers>",
     "verbose": "<from state.verbose>",
     "createdAt": "<from state.startedAt or file mtime>",
     "lastActivity": "<current ISO timestamp>",
     "project": "<from context or directory name>",
     "story": null
   }
   ```

3. If `current-story.md` exists, parse it and populate `session.story`:
   ```json
   {
     "title": "<from story heading>",
     "who": "<parsed>",
     "what": "<parsed>",
     "why": "<parsed>",
     "criteria": ["<parsed criteria>"],
     "slug": "<derived from title>",
     "quick": false
   }
   ```

4. If `implementation-plan.md` exists, copy to `sessions/pof-migr-plan.md`

5. Write `pof-migr` to `.claude/context/.active-session`

6. Delete old files:
   ```bash
   rm .claude/context/state.json
   rm -f .claude/context/current-story.md
   rm -f .claude/context/implementation-plan.md
   ```

7. Present migration notice:
   ```markdown
   ## Migration Complete

   Migrated legacy state to per-session format:
   - Session: `pof-migr`
   - Phase: {phase}
   - Status: {status}

   Old `state.json` and `current-story.md` have been removed (recoverable via git).

   Proceeding with resume...
   ```

Then continue with Step 6 (Present Resume Summary).

## State Recovery

If a session file is corrupted or incomplete:

```markdown
## State Recovery Needed

The session state appears incomplete. Options:

1. **Reconstruct from ADRs**: Read docs/adr/ to rebuild decisions
2. **Start fresh**: Run `/pof-kickoff` (preserves existing code)
3. **Manual fix**: Edit `.claude/context/sessions/{id}.json` directly

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
