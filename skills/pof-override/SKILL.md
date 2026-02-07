---
name: pof-override
description: Override a POF agent recommendation. Use when you want to proceed differently than suggested.
---

# POF Override

Override a recommendation from a POF agent and proceed with an alternative.

## When to Use

- Agent recommended option A, but you prefer B
- You have context the agent doesn't
- You want to try something despite warnings
- Requirements changed after recommendation

## Process

### 1. Acknowledge the Override

```markdown
## Override Recorded

**Original recommendation**: {what agent suggested}
**Your choice**: {what you want instead}

I'll proceed with your choice. Please note any caveats that were mentioned.
```

### 2. Record the Override

Read `.claude/context/.active-session` to get the session ID. Update `.claude/context/decisions.json`:
```json
{
  "id": "d00X",
  "sessionId": "<from .active-session>",
  "timestamp": "...",
  "phase": "...",
  "summary": "{chosen option}",
  "override": true,
  "originalRecommendation": "{what was recommended}",
  "reason": "{user's reason if provided}"
}
```

### 3. Handle ADR

If this is an architectural decision:
- Write ADR with the chosen option
- Note in the ADR that this was an override
- Include the reasoning if provided

## Override Format

When user wants to override:

```markdown
## Confirming Override

You're choosing **{option}** instead of the recommended **{recommendation}**.

**Noted caveats:**
- {any warnings that were given}

**To proceed**, I'll:
1. Record this decision
2. {Write ADR if architectural}
3. Continue with your choice

**If you have additional context** that addresses the caveats, please share it now.

Confirm override? (yes/no/provide context)
```

## Providing Context

If user has documentation or context:

```markdown
Thanks for the context. I'll note this in the decision record:

**User context**: {what they provided}

This addresses the concern about {caveat} because {explanation}.

Proceeding with {chosen option}.
```

## Example

```markdown
## Confirming Override

You're choosing **Prisma ORM** instead of the recommended **Drizzle ORM**.

**Noted caveats:**
- Prisma has larger bundle size
- Drizzle is newer but lighter

**If you have additional context** that addresses the caveats, please share it now.

Confirm override? (yes/no/provide context)
```

User: "yes, our team already knows Prisma well"

```markdown
## Override Recorded

**Original recommendation**: Drizzle ORM
**Your choice**: Prisma ORM
**Reason**: Team familiarity

Proceeding with Prisma. ADR will be written.
```
