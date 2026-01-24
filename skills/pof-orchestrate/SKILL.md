---
name: pof-orchestrate
description: Launch the POF orchestrator agent to manage the workflow. Use after /pof:kickoff or /pof:resume.
---

# POF Orchestrate

This skill spawns the pof-orchestrator agent to manage the project workflow.

## When to Use

- After `/pof:kickoff` has completed Phase 0
- After `/pof:resume` when continuing a paused workflow
- When user wants to proceed with the next phase

## Process

1. **Read current state**: Check `.claude/context/state.json`
2. **Spawn orchestrator**: Use the Task tool to launch `pof-orchestrator`
3. **Relay status**: Report orchestrator output to user

## Invocation

Launch the orchestrator agent with the Task tool:

```
Task tool:
- subagent_type: pof-orchestrator
- prompt: "Continue POF workflow from current state. Read .claude/context/state.json for current phase and status."
```

## State File Location

The orchestrator reads from and writes to:
- `.claude/context/state.json` - Current phase and status
- `.claude/context/decisions.json` - Decisions made
- `.claude/context/requirements.md` - Gathered requirements
- `.claude/context/architecture.md` - Approved architecture

## Progress Messages

The orchestrator will output progress in this format:
```
// pof-{agent} is {action}
```

These should be displayed to the user to show workflow progress.

## Checkpoints

The orchestrator will pause at checkpoints and relay questions to the main conversation for user approval. These checkpoints are:
- Phase 0.4: After initialization
- Phase 1.5: Architecture approval
- Phase 2.4: Design approval
- Phase 4.4: Implementation approval
- Phase 5.2: Deployment plan approval

## Handling Orchestrator Output

When the orchestrator returns:
1. Present the summary to the user
2. If there's a checkpoint question, ask it
3. If there's an error, present recovery options
4. Update the user on next steps

## Example Flow

User: `/pof:orchestrate`

→ Read state: Phase 1.1
→ Launch orchestrator with prompt to continue from Phase 1.1
→ Orchestrator dispatches pof-stack-validator
→ Progress: `// pof-stack-validator is checking compatibility`
→ Orchestrator dispatches pof-architecture-advisor
→ Progress: `// pof-architecture-advisor is analyzing tech choices`
→ Orchestrator reaches checkpoint at 1.5
→ Returns architecture proposal for user approval
→ Present to user: "Architecture proposal ready. [details] Approve?"
