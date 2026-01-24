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
ls .claude/context/ 2>/dev/null
```

Determine state:
- **Green-field**: Empty or minimal files
- **Existing project**: Has package.json, source code
- **Resuming**: Has `.claude/context/state.json`
- **Integration**: User mentions adding to existing system

### Step 2: Gather Requirements

Ask the user (if not already provided):
1. What are you building? (brief description)
2. Target tech stack (or let POF recommend)
3. Deployment target (or discuss later)
4. Any constraints or preferences?

### Step 3: Set Up Context Directory

If not resuming, create the POF context structure:
```bash
mkdir -p .claude/context docs/adr
```

Initialize `.claude/context/state.json`:
```json
{
  "currentPhase": "0.1",
  "status": "initializing",
  "blockers": [],
  "lastCheckpoint": null,
  "progressStyle": "inline-persistent",
  "verbose": false
}
```

### Step 4: Present Phase Outline

Show the user what's coming:

```
## POF Phase Outline

PHASE 0: INITIALIZATION ◀ You are here
├── 0.1 Project state detection
├── 0.2 Requirements gathering
├── 0.3 Source priority setup
└── 0.4 Phase outline presentation → CHECKPOINT

PHASE 1: ARCHITECTURE
├── 1.1 Stack validation
├── 1.2 Infrastructure discussion
├── 1.3 Architecture proposal
├── 1.4 Alternatives presentation
└── 1.5 Architecture approval → CHECKPOINT + ADR

PHASE 2: DESIGN
├── 2.1 UX/accessibility patterns
├── 2.2 Component structure
├── 2.3 Data flow design
└── 2.4 Design approval → CHECKPOINT + ADR

PHASE 3: SCAFFOLDING
├── 3.1 Project initialization
├── 3.2 Dependency installation
├── 3.3 Configuration setup
└── 3.4 Scaffold verification → ADR + COMMIT

PHASE 4: IMPLEMENTATION
├── 4.1 Implementation planning
├── 4.2 Development cycles
├── 4.3 Security review
└── 4.4 Implementation approval → CHECKPOINT

PHASE 5: DEPLOYMENT
├── 5.1 Environment configuration
├── 5.2 Deployment plan review → CHECKPOINT
├── 5.3 Deployment execution
├── 5.4 Verification
└── 5.5 Rollback documentation → ADR

PHASE 6: HANDOFF
├── 6.1 Documentation finalization
├── 6.2 ADR index generation
└── 6.3 Summary presentation
```

### Step 5: Request Checkpoint Approval

Before proceeding to Phase 1, ask:

> Phase 0 complete. I've gathered your requirements and set up the POF context.
>
> **Summary:**
> - Project type: {green-field/existing/integration}
> - Goal: {brief description}
> - Stack: {proposed or TBD}
> - Deployment: {proposed or TBD}
>
> Ready to proceed to **Phase 1: Architecture**?

## Next Steps

After approval, use `/pof:orchestrate` to start the orchestrator agent which will manage the remaining phases.

## After Kickoff Completes

Include this guidance when the full workflow finishes:

```markdown
## What's Next?

Your project is set up. For future development:

| To do this... | Use this command |
|---------------|------------------|
| Add a new feature | `/pof:story As a user, I want...` |
| Quick bug fix | `/pof:story --quick Fix the...` |
| See all commands | `/pof:guide` |

Stories skip the setup phases and go straight to design → plan → implement.
```

## Tips

- If user provides extensive context upfront, acknowledge and proceed faster
- If user is vague, ask clarifying questions
- Always show the phase outline so user knows what to expect
- Terse communication unless user asks for details
