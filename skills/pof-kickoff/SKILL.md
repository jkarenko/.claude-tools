---
name: pof-kickoff
description: Start a new POF (Project Orchestration Flow) workflow. Gathers requirements, detects project state, sets up context, and presents phase outline.
---

# POF Kickoff

You are starting a POF (Project Orchestration Flow) workflow. This is the entry point for orchestrated project development.

## Kickoff Process

### Step 1: Detect Project State

Check the current directory:
```bash
ls -la
cat package.json 2>/dev/null
ls .claude/context/sessions/ 2>/dev/null
```

Determine state:
- **Green-field**: Empty or minimal files
- **Existing project**: Has package.json, source code
- **Resuming**: Has `.claude/context/sessions/` with session files → redirect to `/pof-resume`
- **Integration**: User mentions adding to existing system

### Step 2: Initialize Git

If the directory is not already a git repository:
```bash
git init
```

If it is already a repo, skip this step. Git must be initialized before any POF work begins.

### Step 3: Gather Requirements

Ask the user (if not already provided):
1. What are you building? (brief description)
2. Target tech stack (or let POF recommend)
3. Deployment target (or discuss later)
4. Any constraints or preferences?

### Step 4: Set Up Context Directory

Create the POF context structure:
```bash
mkdir -p .claude/context/sessions docs/adr
```

Generate a short project ID: `proj-` followed by 4 random hex chars (e.g., `proj-a3f8`).

Create **project file** at `.claude/context/project.json`:
```json
{
  "id": "proj-a3f8",
  "name": "<project name or description>",
  "createdAt": "<current ISO timestamp>"
}
```

If `.claude/context/project.json` already exists, read it and use the existing project ID and name instead of generating new ones.

Generate a short session ID: `pof-` followed by 4 random hex chars (e.g., `pof-b7e2`).

Initialize the **session file** at `.claude/context/sessions/{id}.json`:
```json
{
  "id": "pof-b7e2",
  "projectId": "proj-a3f8",
  "type": "kickoff",
  "currentPhase": "0.1",
  "status": "initializing",
  "blockers": [],
  "lastCheckpoint": null,
  "verbose": false,
  "createdAt": "<current ISO timestamp>",
  "lastActivity": "<current ISO timestamp>",
  "project": "<project name or description>",
  "story": null
}
```

Write the session ID to `.claude/context/.active-session` (just the ID string, e.g., `pof-b7e2`).

Initialize `.claude/context/decisions.json` (shared across sessions):
```json
{
  "decisions": []
}
```

Write the gathered requirements to `.claude/context/requirements.md`.

### Step 5: Start Dashboard (optional)

Start the POF dashboard for real-time monitoring. This is optional — all workflow features work without it.

```bash
bun run ~/.claude-tools/dashboard/server.ts > /dev/null 2>&1 &
```

If the dashboard starts, inform the user: "Dashboard running at http://localhost:3456"

If it fails (port busy, bun not installed), silently continue — the dashboard is purely additive.

Send an initial status report with the project name so the dashboard can label this session:

```bash
curl -s -X POST http://localhost:3456/api/status \
  -H 'Content-Type: application/json' \
  -d '{"agent":"orchestrator","session":"<sessionId>","status":"started","message":"Kickoff started","detail":"project:<project name>","projectId":"<projectId>","sessionType":"kickoff"}' \
  > /dev/null 2>&1 || true
```

### Step 6: Present Phase Outline

Show the user what's coming:

```
## POF Phase Outline

PHASE 0: INITIALIZATION ◀ You are here
├── 0.1 Project state detection
├── 0.2 Requirements gathering
├── 0.3 Context setup
└── 0.4 Phase outline presentation → CHECKPOINT

PHASE 1: ARCHITECTURE
├── 1.1 Stack validation
├── 1.2 Infrastructure discussion
├── 1.3 Architecture proposal
└── 1.5 Architecture approval → CHECKPOINT + ADR

PHASE 2: DESIGN
├── 2.1 UX/accessibility patterns
├── 2.2 Component & data flow design
└── 2.4 Design approval → CHECKPOINT + ADR

PHASE 3: SCAFFOLDING (if green-field)
├── 3.1 Project initialization
├── 3.2 Dependencies & configuration
└── 3.4 Scaffold verification → COMMIT

PHASE 4: IMPLEMENTATION
├── 4.1 Implementation planning → CHECKPOINT
├── 4.2 Development cycles (TDD: write test → implement → run test → commit)
├── 4.3 Security review
└── 4.4 Implementation approval → CHECKPOINT

PHASE 5: DEPLOYMENT
├── 5.1 Environment configuration
├── 5.2 Deployment plan → CHECKPOINT
├── 5.3 Execution & verification
└── 5.5 Rollback documentation → ADR

PHASE 6: HANDOFF
├── 6.1 Documentation finalization
├── 6.2 ADR index generation
└── 6.3 Summary presentation
```

### Step 7: Initial Commit

Commit the POF context files:
```bash
git add .claude/context/project.json .claude/context/sessions/ .claude/context/.active-session .claude/context/decisions.json .claude/context/requirements.md docs/adr/
git commit -m "chore(pof): initialize project orchestration context"
```

### Step 8: Checkpoint 0.4

Present the checkpoint:

> Phase 0 complete. Project context is set up and committed.
>
> **Summary:**
> - Project type: {green-field/existing/integration}
> - Goal: {brief description}
> - Stack: {proposed or TBD}
> - Deployment: {proposed or TBD}
>
> Ready to proceed to **Phase 1: Architecture**?

### Step 9: Auto-Continue

After user approves Checkpoint 0.4:

1. Update session file: set `currentPhase` to `"1.1"`, `status` to `"in_progress"`, `lastCheckpoint` to `"0.4"`, and `lastActivity` to current timestamp
2. Inform the user: "Starting Phase 1: Architecture..."
3. Continue directly with the `/pof-orchestrate` instructions — read and follow the orchestrate skill logic to begin Phase 1.

**Do not** tell the user to manually run `/pof-orchestrate`. The workflow continues seamlessly from kickoff into orchestration.

## Tips

- If user provides extensive context upfront, acknowledge and proceed faster
- If user is vague, ask clarifying questions
- Always show the phase outline so user knows what to expect
- Terse communication unless user asks for details
- If git init fails or user doesn't want git, note it but continue — git is strongly recommended but not blocking
