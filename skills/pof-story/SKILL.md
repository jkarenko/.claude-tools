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
- `.claude/context/architecture.md`
- `.claude/context/state.json`

If no context exists:
```markdown
No project context found. This feature needs architectural context first.

Options:
1. Run `/pof-kickoff` to set up the project
2. Provide architecture context now (stack, patterns, etc.)
```

### Step 3: Create Story Context

Write the story to `.claude/context/current-story.md`:

```markdown
# Current Story

## User Story
As a {who}, I want {what} so that {why}.

## Acceptance Criteria
- [ ] {criterion 1}
- [ ] {criterion 2}

## Status
- Created: {timestamp}
- Phase: design
```

### Step 4: Dispatch to UX Designer

Use the Task tool to invoke `pof-ux-designer`:
- Provide story content and architecture context
- Ask for interaction patterns, accessibility requirements, component structure, loading/error states

Present UX recommendations to user (requires approval).

### Step 5: Dispatch to Implementation Planner

After UX approval, use the Task tool to invoke `pof-implementation-planner`:
- Provide story content, UX recommendations, architecture context
- Ask it to create a detailed plan with commit points
- It writes to `.claude/context/implementation-plan.md`

Present implementation plan to user (requires approval).

### Step 6: Begin Inline Implementation

After plan approval, update state and begin implementation directly:

Update `.claude/context/state.json`:
```json
{
  "currentPhase": "4.2",
  "status": "implementing",
  "mode": "story",
  "currentStory": "current-story.md",
  "lastCheckpoint": "4.1"
}
```

**Continue with implementation inline** — follow the `/pof-orchestrate` Phase 4.2 TDD instructions:

1. Read `implementation-plan.md`
2. For each task in the plan (TDD cycle):
   - Dispatch `pof-test-writer` to write unit tests first (skip for config/styling/trivial tasks)
   - Implement the feature (write code in this conversation to make tests pass)
   - Dispatch `pof-test-runner` to verify — fix if tests fail
   - Dispatch `pof-git-committer` for a feature-level conventional commit
   - Report progress to dashboard
3. After all tasks: run integration tests if applicable (separate concern)
4. Dispatch `pof-security-reviewer`
5. Present completion summary

**Do not** spawn a `pof-orchestrator` subagent. Run everything inline in this conversation.

### Step 7: Story Completion

When implementation finishes:

1. Verify all acceptance criteria in `current-story.md` are met
2. Dispatch `pof-adr-writer` if architectural decisions were made
3. Update `current-story.md` status to `done` with commit list
4. Archive to `.claude/context/stories/{date}-{slug}.md`
5. Reset state: `{ "currentPhase": "idle", "status": "ready", "mode": null, "lastStory": "{slug}" }`

Present story completion summary.

## Quick Mode

For small stories that don't need UX review:

```
/pof-story --quick Fix the login button alignment on mobile
```

This skips UX designer (Step 4) and goes straight to implementation planning.

## Dashboard Reporting

Report story progress throughout:

```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","phase":"4.2","status":"working","message":"Implementing: <task>"}' \
  > /dev/null 2>&1 || true
```

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
