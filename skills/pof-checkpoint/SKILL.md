---
name: pof-checkpoint
description: Present a POF checkpoint for user approval. Summarizes progress and requests confirmation before proceeding.
---

# POF Checkpoint

Use this skill to present checkpoint summaries and request user approval before proceeding to the next phase.

## Checkpoint Locations

Checkpoints occur at:
- **0.4**: After initialization
- **1.5**: Architecture approval
- **2.4**: Design approval
- **4.4**: Implementation approval
- **5.2**: Deployment plan approval

## Checkpoint Format

```markdown
## ✓ Checkpoint: {Phase Name}

### Completed
- {What was done in this phase}
- {Key decisions made}

### Decisions Recorded
| Decision | Summary | ADR |
|----------|---------|-----|
| {ID} | {Brief} | {Link if applicable} |

### Next Phase: {Name}
{Brief description of what comes next}

**Items requiring your attention:**
- {Any pending questions}
- {Any concerns raised}

---

**Ready to proceed to {Next Phase}?** (yes/no/questions)
```

## Guidelines

- **Summarize, don't repeat**: Brief recap of accomplishments
- **Highlight decisions**: List what was decided
- **Preview next phase**: Set expectations
- **Surface concerns**: Don't hide issues
- **Clear call to action**: Ask for explicit approval

## User Responses

Handle different responses:

### "yes" or approval
- Update state.json to next phase
- Continue with `/pof:orchestrate`

### "no" or rejection
- Ask what needs to change
- Don't proceed until resolved

### Questions
- Answer questions
- Re-present checkpoint when ready

### Modifications
- Record changes to decisions
- Update relevant context files
- May need to re-run certain agents

## State Update

After approval, update `.claude/context/state.json`:
```json
{
  "lastCheckpoint": "1.5",
  "currentPhase": "2.1",
  "status": "in_progress"
}
```

## Example

```markdown
## ✓ Checkpoint: Architecture

### Completed
- Validated Next.js 14 + Bun + shadcn/ui compatibility
- Analyzed Azure SWA deployment requirements
- Designed component architecture

### Decisions Recorded
| Decision | Summary | ADR |
|----------|---------|-----|
| d001 | Use Next.js App Router | [ADR-0001](docs/adr/0001-use-nextjs-app-router.md) |
| d002 | Deploy to Azure SWA | [ADR-0002](docs/adr/0002-deploy-azure-swa.md) |

### Next Phase: Design
UX patterns, component structure, and data flow design.

**Items requiring your attention:**
- None. All questions resolved.

---

**Ready to proceed to Design phase?** (yes/no/questions)
```
