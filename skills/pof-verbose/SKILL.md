---
name: pof-verbose
description: Toggle verbose mode for POF agents. When enabled, agents explain their reasoning in detail.
---

# POF Verbose

Toggle verbose mode for POF workflow.

## Modes

### Terse (default)
- Short, factual updates
- Decisions stated without lengthy justification
- Progress messages are minimal
- Good for experienced users

### Verbose
- Detailed explanations of reasoning
- Step-by-step justifications
- More context on decisions
- Good for learning or reviewing

## Usage

### Enable Verbose
```markdown
## Verbose Mode: ON

Agents will now provide detailed explanations for:
- Why recommendations are made
- How decisions were reached
- What alternatives were considered
- Step-by-step reasoning

Use `/pof:verbose` again to toggle off.
```

Update `.claude/context/state.json`:
```json
{
  "verbose": true
}
```

### Disable Verbose
```markdown
## Verbose Mode: OFF

Agents will now be terse:
- Brief, factual updates
- Decisions without lengthy justification
- Minimal progress messages

Use `/pof:verbose` again to toggle on.
```

Update `.claude/context/state.json`:
```json
{
  "verbose": false
}
```

## Check Current State

```bash
cat .claude/context/state.json | grep verbose
```

## Effect on Agents

When `verbose: true`:

**Architecture Advisor** will explain:
- Why certain technologies were considered
- How trade-offs were weighed
- What research was done

**Stack Validator** will show:
- Detailed compatibility checks
- Version requirement reasoning
- Integration point analysis

**Implementation Planner** will include:
- Reasoning for task ordering
- Why certain dependencies exist
- Alternative approaches considered

## Example: Terse vs Verbose

### Terse
```
Stack validated. Next.js 14 + Bun compatible. Proceeding.
```

### Verbose
```
Stack validation complete.

I checked Next.js 14 compatibility with Bun 1.x:
- Bun has supported Next.js since version 1.0
- The App Router is fully compatible
- Server Components work correctly
- Some edge cases exist with certain Next.js plugins

shadcn/ui compatibility:
- Requires Tailwind CSS (will be installed with Next.js)
- Works with App Router structure
- No known issues with Bun

Conclusion: Stack is compatible. Proceeding to architecture phase.
```

## Temporary Verbose

For a single query without changing mode:
```
"Explain why you recommended X" or "Give me more detail on Y"
```

Agents should respond with detail regardless of mode setting when explicitly asked.
