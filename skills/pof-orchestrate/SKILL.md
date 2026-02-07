---
name: pof-orchestrate
description: Drive POF workflow phases inline. Reads state, dispatches agents, manages checkpoints, reports progress.
---

# POF Orchestrate

You are now driving the POF workflow directly in this conversation. You dispatch specialist agents for focused work, manage user checkpoints, maintain state, and report progress.

## Step 1: Read State

Read `.claude/context/state.json` to determine current phase. Note the `sessionId` — you'll need it for all dashboard reports and agent dispatches. Also read whichever context files are relevant:

- `.claude/context/requirements.md` — always
- `.claude/context/decisions.json` — always
- `.claude/context/architecture.md` — Phase 2+
- `.claude/context/implementation-plan.md` — Phase 4+
- `.claude/context/current-story.md` — if `state.mode === "story"`

If `state.mode === "story"`, skip to **Phase 4** (story mode only runs implementation + verification).

## Step 2: Dashboard Report

Report your progress throughout. Use the `sessionId` from `state.json` in every report. This silently no-ops if the dashboard isn't running:

```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<sessionId>","phase":"PHASE","status":"working","message":"MSG"}' \
  > /dev/null 2>&1 || true
```

Report at every phase transition and agent dispatch.

**When dispatching agents**, always include the session ID in the dispatch prompt so the agent can use it for its own dashboard reports: `"Dashboard session ID: <sessionId>"`

## Step 3: Execute Current Phase

Based on `state.currentPhase`, continue from that point. After each checkpoint approval, **continue to the next phase without waiting for user to invoke another command**.

---

### PHASE 1: ARCHITECTURE

**1.1 Stack Validation**

Dispatch `pof-stack-validator` via Task tool:
- Provide requirements summary from `requirements.md`
- Ask it to check version compatibility and known issues

Present validation results to user. If issues found, discuss before proceeding.

Update state to `1.2`.

**1.2 Infrastructure & Architecture Discussion**

Dispatch `pof-architecture-advisor` via Task tool:
- Provide requirements + stack validation results
- Ask for architecture analysis, infrastructure recommendations, conflict identification

Present findings and recommendations to user.

Update state to `1.3`.

**1.3 Architecture Proposal**

Synthesize stack validation + architecture advice into a coherent architecture proposal. Write to `.claude/context/architecture.md`:
- Tech stack with versions
- Component architecture
- Data flow
- Infrastructure approach
- Key trade-offs

Update state to `1.5`.

**1.5 Architecture Approval → CHECKPOINT**

Present architecture summary. Ask user to approve, request changes, or see alternatives.

If user wants alternatives: present options, discuss, revise architecture.md.

On approval:
1. Record decision in `decisions.json`
2. Dispatch `pof-adr-writer`: "Write ADR for architecture decision. Read `.claude/context/architecture.md`."
3. Dispatch `pof-git-committer`: commit architecture.md + ADR + decisions.json
4. Update state to `2.1`, set `lastCheckpoint: "1.5"`

**Continue to Phase 2.**

---

### PHASE 2: DESIGN

**2.1 UX & Accessibility Patterns**

Dispatch `pof-ux-designer` via Task tool:
- Provide architecture.md and requirements.md
- Ask for UX patterns, accessibility requirements, component structure, interaction design

Present UX recommendations to user.

Update state to `2.2`.

**2.2 Component & Data Flow Design**

Based on UX recommendations and architecture, design:
- Component hierarchy and structure
- Data flow between components
- API contracts (if applicable)
- State management approach

Write design decisions to `architecture.md` (append design section) or create separate design doc if complex.

Update state to `2.4`.

**2.4 Design Approval → CHECKPOINT**

Present design summary. Ask user to approve or request changes.

On approval:
1. Record decision in `decisions.json`
2. Dispatch `pof-adr-writer` for design ADR
3. Dispatch `pof-git-committer`: commit design artifacts
4. Update state to `3.1`, set `lastCheckpoint: "2.4"`

**Continue to Phase 3** (or skip to Phase 4 if not green-field).

---

### PHASE 3: SCAFFOLDING

Skip this phase if the project already has structure (existing project or integration).

**3.1–3.3 Project Initialization**

Dispatch `pof-scaffolder` via Task tool:
- Provide architecture.md for stack/structure decisions
- Let it create project structure, install dependencies, configure tools

Present scaffolding report to user.

**3.4 Scaffold Verification**

Verify the scaffold works:
- Dispatch `pof-test-runner` if tests exist
- Check that the dev server starts

Then:
1. Dispatch `pof-git-committer`: commit initial scaffold — `feat(scaffold): initialize project structure`
2. Update state to `4.1`, set `lastCheckpoint: "3.4"`

**Continue to Phase 4.**

---

### PHASE 4: IMPLEMENTATION

**4.1 Implementation Planning**

Dispatch `pof-implementation-planner` via Task tool:
- Provide architecture.md, design docs, requirements.md
- If story mode: provide `current-story.md`
- Ask it to create a detailed, sequenced plan with tasks

It writes to `.claude/context/implementation-plan.md`.

Present implementation plan to user. **CHECKPOINT** — user must approve the plan.

On approval, update state to `4.2`.

**4.2 Iterative Development (TDD)**

Read `implementation-plan.md`. For each task in the plan, follow a test-driven cycle:

1. **Write tests first** — dispatch `pof-test-writer` with the task description and architecture context. It writes unit tests that define expected behavior (these will fail initially).
2. **Implement** the feature — write the code yourself in the main conversation to make the tests pass.
3. **Run tests** — dispatch `pof-test-runner` to verify implementation. If tests fail, fix the code and re-run.
4. **Commit** — dispatch `pof-git-committer` to create a feature-level conventional commit (include both test and implementation files).
5. **Report** — update dashboard with progress.

Repeat for each task. Keep the user informed with brief progress updates between tasks.

Not every task needs the full TDD cycle — skip `pof-test-writer` for configuration, styling, or trivial changes where unit tests add no value.

**4.2.5 Integration Tests (optional)**

After all tasks in the plan are implemented, consider whether integration tests are warranted. Integration tests are a **separate concern** from the per-feature TDD loop:

- Dispatch `pof-test-runner` with explicit instructions to run integration tests (e.g., `npm run test:integration`)
- Only if the project has integration test infrastructure set up
- Focus on cross-component or cross-service boundaries
- Do not block on this — if no integration test setup exists, note it and move on

**4.3 Security Review**

After implementation is complete, dispatch `pof-security-reviewer`:
- Point it at the new/changed code
- Present findings to user
- Fix any critical issues, commit fixes

**4.4 Implementation Approval → CHECKPOINT**

Present implementation summary:
- Features completed
- Tests passing (unit + integration if run)
- Commits created
- Security review results

Then ask:

> Implementation is complete. **Next up: Phase 5 (Deployment).**
>
> Options:
> 1. **Proceed to deployment** — configure environment, deploy, verify
> 2. **Skip deployment** — go straight to Phase 6 (Handoff / documentation wrap-up)
> 3. **Request changes** — revisit implementation

If story mode: skip to **Story Completion** below.

On approval for deployment: update state to `5.1`, set `lastCheckpoint: "4.4"`. **Continue to Phase 5.**

On skip deployment: update state to `6.1`, set `lastCheckpoint: "4.4"`. **Continue to Phase 6.**

---

### PHASE 5: DEPLOYMENT

**5.1 Environment Configuration**

Check if `.env.example` exists and is complete. If deployment needs env vars, ensure they're documented.

**5.2 Deployment Plan → CHECKPOINT**

Present deployment plan:
- Target environment
- Deployment method
- Rollback strategy

User must approve before deployment.

**5.3 Deployment Execution**

Dispatch `pof-deployer`:
- Provide deployment plan and architecture context
- Requires user approval for each deployment action

**5.4 Verification**

Verify deployment succeeded. Run smoke tests if applicable.

**5.5 Rollback Documentation**

Dispatch `pof-adr-writer`: document deployment approach and rollback procedures.
Dispatch `pof-git-committer`: commit deployment configs and docs.

Update state to `6.1`.

**Continue to Phase 6.**

---

### PHASE 6: HANDOFF

**6.1 Documentation Finalization**

Ensure all documentation is current:
- Architecture.md reflects final state
- ADRs are complete
- README is updated (if applicable)

**6.2 ADR Index**

Dispatch `pof-adr-writer`: regenerate `docs/adr/README.md` index.

**6.3 Summary & Completion**

Present workflow summary:
- What was built
- Key decisions (with ADR references)
- Commits created
- Deployment status

Update state: `{ "currentPhase": "complete", "status": "done" }`

Dispatch `pof-git-committer`: final documentation commit.

Show the user their next-steps options:

```
## Workflow Complete

**Project**: {name/description}
**Phases completed**: 0–6
**Total commits**: {N}
**ADRs written**: {N}
**Deployment**: {deployed to X / skipped}

| To do this...              | Do this                                  |
|----------------------------|------------------------------------------|
| Add a new feature          | `/pof-story As a user, I want...`        |
| Quick bug fix              | `/pof-story --quick Fix the...`          |
| Push all commits to remote | `git push`                               |
| Review decisions made      | See `docs/adr/`                          |
| See project history        | `git log --oneline`                      |
| See all commands           | `/pof-guide`                             |

This conversation can continue — ask questions, add features, or start
a new conversation any time with `/pof-resume` to pick up where you
left off.
```

---

### STORY COMPLETION (story mode only)

After Phase 4 completes in story mode:

1. Verify all acceptance criteria in `current-story.md` are met
2. Dispatch `pof-adr-writer` if architectural decisions were made during implementation
3. Archive story to `.claude/context/stories/{date}-{slug}.md`
4. Update `current-story.md` status to `done`
5. Reset state: `{ "currentPhase": "idle", "status": "ready", "mode": null, "lastStory": "{slug}" }`

Present story completion summary, then show next-steps options:

```
## Story Complete

**Story**: {story title}
**Commits**: {N} feature commits
**Tests**: {pass/fail summary}

| To do this...              | Do this                                  |
|----------------------------|------------------------------------------|
| Add another feature        | `/pof-story As a user, I want...`        |
| Quick bug fix              | `/pof-story --quick Fix the...`          |
| Push commits to remote     | `git push`                               |
| See project history        | `git log --oneline`                      |
| See all commands           | `/pof-guide`                             |
```

---

## Commit Discipline

Dispatch `pof-git-committer` after these events:
- Architecture approval (Phase 1.5)
- Design approval (Phase 2.4)
- Scaffold creation (Phase 3.4)
- **Each feature/task** in implementation (Phase 4.2) — this is the key difference from before
- Security fixes (Phase 4.3)
- Deployment configs (Phase 5.5)
- Final documentation (Phase 6.3)
- Story completion

All commits use conventional format with mandatory scope: `type(scope): description`

## State Management

After each step, update `.claude/context/state.json`:

```json
{
  "currentPhase": "X.X",
  "status": "in_progress",
  "sessionId": "<current session ID>",
  "lastCheckpoint": "X.X",
  "blockers": [],
  "progressStyle": "inline-persistent",
  "verbose": false,
  "mode": null
}
```

Also update `.claude/context/decisions.json` when decisions are made at checkpoints.

## Communication Style

- **Terse between checkpoints**: brief progress updates, no unnecessary explanation
- **Detailed at checkpoints**: summarize work, present decisions clearly, outline next phase
- **Always state what's next**: after each step, tell the user what comes next
- **Respect verbose mode**: if `state.verbose === true`, explain agent reasoning in detail

## Error Handling

If an agent fails:
1. Dispatch `pof-error-handler` with the error context
2. Present diagnosis and recovery options to user
3. Do not proceed past the failure until resolved

If blocked on user input:
1. Report the blocker clearly
2. Update state with blocker info
3. Wait for user response before continuing
