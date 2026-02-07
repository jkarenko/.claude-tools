---
name: pof-story
description: Add a new feature using a user story. Skips project setup and goes directly to design and implementation planning.
---

# POF Story

Accept a user story and orchestrate feature development without the full kickoff ceremony.

## Usage

```
/pof-story As a user, I want to filter products by category so I can find items faster
```

Or with acceptance criteria:

```
/pof-story As a user, I want to reset my password
- Email with reset link sent within 1 minute
- Link expires after 24 hours
- User sees confirmation message
```

Or plan a story for later without starting it:

```
/pof-story --plan As a user, I want to export data as CSV so I can analyze it externally
```

## Process

### Step 1: Parse the User Story

Extract from the input:
- **Who**: The user role/persona
- **What**: The desired functionality
- **Why**: The benefit/goal (if provided)
- **Acceptance criteria**: Specific requirements (if provided)

If the story is incomplete or unclear, ask for clarification.

### Step 2: Load Project Context

Read existing context:
- `.claude/context/project.json` — get `projectId` and project name
- `.claude/context/architecture.md`
- `.claude/context/.active-session` (if exists — another session may be running)

If `.claude/context/project.json` exists, use its `id` as `projectId` and `name` as the project name. If it doesn't exist, fall back to the directory name for the project name and leave `projectId` unset.

If no architecture context exists:
```markdown
No project context found. This feature needs architectural context first.

Options:
1. Run `/pof-kickoff` to set up the project
2. Provide architecture context now (stack, patterns, etc.)
```

### Step 2.5: Start Dashboard and Session

Generate a **new** session ID for this conversation (e.g., `pof-c4d1`).

Start the dashboard if not already running:

```bash
curl -sf http://localhost:3456/health > /dev/null 2>&1 || bun run ~/.claude-tools/dashboard/server.ts > /dev/null 2>&1 &
```

If it starts, inform the user: "Dashboard running at http://localhost:3456"

Register the session:

```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<sessionId>","status":"started","message":"Story started","detail":"project:<project name from context>","projectId":"<projectId>","storyTitle":"<story title>","storyStatus":"in_progress","sessionType":"story"}' \
  > /dev/null 2>&1 || true
```

### Step 3: Create Session File

Create the sessions directory if needed and write the session file at `.claude/context/sessions/{id}.json`:

```bash
mkdir -p .claude/context/sessions
```

```json
{
  "id": "pof-c4d1",
  "projectId": "<projectId from project.json>",
  "type": "story",
  "currentPhase": "design",
  "status": "in_progress",
  "lastCheckpoint": null,
  "blockers": [],
  "verbose": false,
  "createdAt": "<current ISO timestamp>",
  "lastActivity": "<current ISO timestamp>",
  "project": "<project name from project.json or directory name>",
  "story": {
    "title": "<short title derived from story>",
    "who": "<user role>",
    "what": "<desired functionality>",
    "why": "<benefit/goal>",
    "criteria": ["criterion 1", "criterion 2"],
    "slug": "<kebab-case-slug>",
    "quick": false
  }
}
```

Write the session ID to `.claude/context/.active-session`.

### Step 3.5: Plan Mode Check

If the `--plan` flag is present in the original input:

1. Set `status` to `"planned"` in the session file (instead of `"in_progress"`)
2. Set `currentPhase` to `"planned"` in the session file
3. Report to dashboard with `storyStatus: "planned"`:
   ```bash
   curl -s -X POST http://localhost:3456/api/status \
     -H 'Content-Type: application/json' \
     -d '{"agent":"orchestrator","session":"<sessionId>","status":"complete","message":"Story planned: <story title>","projectId":"<projectId>","storyTitle":"<story title>","storyStatus":"planned","sessionType":"story"}' \
     > /dev/null 2>&1 || true
   ```
4. **Stop** — do not proceed to Step 4 or beyond
5. Print:
   ```markdown
   ## Story Planned

   **Story**: <story title>
   **Session**: <session ID>
   **Status**: Planned (not started)

   This story has been saved for later. Start it with `/pof-resume` and select this session.
   ```

If `--plan` is not present, continue to Step 4.

### Step 4: Dispatch to UX Designer

Report phase transition to dashboard:
```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<session id>","phase":"design","status":"working","message":"Dispatching UX designer","projectId":"<projectId>","storyTitle":"<story title>","storyStatus":"in_progress","sessionType":"story"}' \
  > /dev/null 2>&1 || true
```

Use the Task tool to invoke `pof-ux-designer`:
- Provide story content (from `session.story`) and architecture context
- Ask for interaction patterns, accessibility requirements, component structure, loading/error states
- Include: `"Dashboard session ID: <session id>"`

Present UX recommendations to user (requires approval).

### Step 5: Dispatch to Implementation Planner

Report phase transition:
```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<session id>","phase":"4.1","status":"working","message":"Creating implementation plan","projectId":"<projectId>","storyTitle":"<story title>","storyStatus":"in_progress","sessionType":"story"}' \
  > /dev/null 2>&1 || true
```

After UX approval, use the Task tool to invoke `pof-implementation-planner`:
- Provide story content (from `session.story`), UX recommendations, architecture context
- Tell it to write the plan to `.claude/context/sessions/{id}-plan.md`
- Include: `"Dashboard session ID: <session id>"`
- Include: `"Session file: .claude/context/sessions/{id}.json"`

Present implementation plan to user (requires approval).

### Step 6: Begin Inline Implementation

After plan approval, update the session file and begin implementation directly:

Update `.claude/context/sessions/{id}.json`:
- Set `currentPhase` to `"4.2"`
- Set `status` to `"implementing"`
- Set `lastCheckpoint` to `"4.1"`
- Set `lastActivity` to current timestamp

Report phase transition:
```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<session id>","phase":"4.2","status":"working","message":"Starting implementation","projectId":"<projectId>","storyTitle":"<story title>","storyStatus":"in_progress","sessionType":"story"}' \
  > /dev/null 2>&1 || true
```

**Continue with implementation inline** — follow the `/pof-orchestrate` Phase 4.2 TDD instructions:

1. Read `sessions/{id}-plan.md`
2. For each task in the plan (TDD cycle):
   - Dispatch `pof-test-writer` to write unit tests first (skip for config/styling/trivial tasks)
     - Include `"Dashboard session ID: <session id>"` in dispatch
   - Implement the feature (write code in this conversation to make tests pass)
   - Dispatch `pof-test-runner` to verify — fix if tests fail
     - Include `"Dashboard session ID: <session id>"` in dispatch
   - Dispatch `pof-git-committer` for a feature-level conventional commit
     - Include `"Dashboard session ID: <session id>"` in dispatch
   - Report task progress to dashboard:
     ```bash
     curl -s -X POST http://localhost:3456/api/status \
       -H 'Content-Type: application/json' \
       -d '{"agent":"orchestrator","session":"<session id>","phase":"4.2","status":"working","message":"Completed: <task name>"}' \
       > /dev/null 2>&1 || true
     ```
3. After all tasks: run integration tests if applicable (separate concern)
4. Dispatch `pof-security-reviewer`
   - Include `"Dashboard session ID: <session id>"` in dispatch
5. Present completion summary

**Do not** spawn a `pof-orchestrator` subagent. Run everything inline in this conversation.

### Step 7: Story Completion

When implementation finishes:

1. Verify all acceptance criteria from `session.story.criteria` are met
2. Dispatch `pof-adr-writer` if architectural decisions were made
3. Archive story to `.claude/context/stories/{date}-{slug}.md` (write story details from session file)
4. Update session file: set `status` to `"completed"`, `currentPhase` to `"idle"`, `lastActivity` to current timestamp
5. Report completion to dashboard:
   ```bash
   curl -s -X POST http://localhost:3456/api/status \
     -H 'Content-Type: application/json' \
     -d '{"agent":"orchestrator","session":"<session id>","phase":"complete","status":"complete","message":"Story complete: <story title>","projectId":"<projectId>","storyTitle":"<story title>","storyStatus":"completed","sessionType":"story"}' \
     > /dev/null 2>&1 || true
   ```

Present story completion summary.

## Quick Mode

For small stories that don't need UX review:

```
/pof-story --quick Fix the login button alignment on mobile
```

This skips UX designer (Step 4) and goes straight to implementation planning.

## Dashboard Reporting

Report story progress throughout. Use the session `id` from the session file in every report. Include `projectId`, `storyTitle`, `storyStatus`, and `sessionType` in all reports:

```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<session id>","phase":"4.2","status":"working","message":"Implementing: <task>","projectId":"<projectId>","storyTitle":"<story title>","storyStatus":"in_progress","sessionType":"story"}' \
  > /dev/null 2>&1 || true
```

**When dispatching agents**, always include both the session ID and session file path in the dispatch prompt:
- `"Dashboard session ID: <session id>"`
- `"Session file: .claude/context/sessions/<id>.json"`

## Output Format

```markdown
## Story Received

**Who**: {role}
**What**: {functionality}
**Why**: {benefit}

### Acceptance Criteria
- [ ] {criterion}

---

Analyzing project context...
Dispatching to UX designer for interaction guidance...
```

## Tips

- Keep stories focused on one feature
- Include acceptance criteria for clarity
- Use `--quick` for bug fixes or trivial changes
- Stories are archived for project history
