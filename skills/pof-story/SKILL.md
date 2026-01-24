---
name: pof-story
description: Add a new feature using a user story. Skips project setup and goes directly to design and implementation planning.
---

# POF Story

Accept a user story and orchestrate feature development without the full kickoff ceremony.

## Usage

```
/pof:story As a user, I want to filter products by category so I can find items faster
```

Or with acceptance criteria:

```
/pof:story As a user, I want to reset my password
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
```bash
cat .claude/context/architecture.md 2>/dev/null
cat .claude/context/state.json 2>/dev/null
```

If no context exists:
```markdown
No project context found. This feature needs architectural context first.

Options:
1. Run `/pof:kickoff` to set up the project
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

```
Task tool:
- subagent_type: pof-ux-designer
- prompt: |
    Review this user story and provide UX/accessibility guidance:

    {story content}

    Consider:
    - Interaction patterns needed
    - Accessibility requirements
    - Component structure
    - Loading/error states

    Read .claude/context/architecture.md for tech stack context.
```

Present UX recommendations to user (requires approval).

### Step 5: Dispatch to Implementation Planner

After UX approval, use the Task tool to invoke `pof-implementation-planner`:

```
Task tool:
- subagent_type: pof-implementation-planner
- prompt: |
    Create an implementation plan for this user story:

    {story content}

    UX requirements:
    {ux recommendations}

    Read existing context from .claude/context/
    Write plan to .claude/context/implementation-plan.md
```

Present implementation plan to user (requires approval).

### Step 6: Hand Off to Orchestrator

After plan approval, update state and launch orchestrator:

Update `.claude/context/state.json`:
```json
{
  "currentPhase": "4.2",
  "status": "implementing",
  "mode": "story",
  "currentStory": "current-story.md"
}
```

Launch orchestrator:
```
Task tool:
- subagent_type: pof-orchestrator
- prompt: |
    Continue POF workflow in story mode.
    Implement the approved plan in .claude/context/implementation-plan.md
    Story context in .claude/context/current-story.md

    After implementation:
    - Run security review
    - Create commits
    - Write ADR if architectural decisions were made
    - Mark story complete
```

## Story Completion

When implementation finishes, update `current-story.md`:

```markdown
## Status
- Created: {timestamp}
- Completed: {timestamp}
- Phase: done
- Commits: {list of commit hashes}
- ADRs: {list if any}
```

Archive to `.claude/context/stories/{date}-{slug}.md` for history.

## Quick Mode

For small stories that don't need UX review:

```
/pof:story --quick Fix the login button alignment on mobile
```

This skips UX designer and goes straight to implementation planning.

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
