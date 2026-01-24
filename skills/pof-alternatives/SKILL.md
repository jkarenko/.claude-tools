---
name: pof-alternatives
description: Present alternative approaches or technologies for a POF decision. Used when multiple valid options exist.
---

# POF Alternatives

Present alternative approaches when there are multiple valid options for a decision.

## When to Use

- Multiple technologies could work
- Different architectural patterns are viable
- Trade-offs need user input
- Current choice has significant caveats

## Presentation Format

```markdown
## Alternatives: {Decision Topic}

### Context
{Why this decision matters, 1-2 sentences}

### Options

#### Option 1: {Name} ⭐ Recommended
{Brief description}

| Aspect | Assessment |
|--------|------------|
| Fit for project | {rating and note} |
| Complexity | {Low/Medium/High} |
| Community/Support | {note} |
| Long-term viability | {note} |

**Pros:**
- {Pro 1}
- {Pro 2}

**Cons:**
- {Con 1}
- {Con 2}

---

#### Option 2: {Name}
{Brief description}

| Aspect | Assessment |
|--------|------------|
| Fit for project | {rating and note} |
| Complexity | {Low/Medium/High} |
| Community/Support | {note} |
| Long-term viability | {note} |

**Pros:**
- {Pro 1}

**Cons:**
- {Con 1}

---

### Recommendation
{Clear recommendation with reasoning}

### Your Input Needed
- Do you have constraints I should consider?
- Is there a preference based on team experience?
- Any documentation that addresses concerns?
```

## Guidelines

- **Max 3-4 options**: More is overwhelming
- **Clear recommendation**: Don't be wishy-washy
- **Honest trade-offs**: Every option has cons
- **Respect user context**: They may know things you don't
- **Actionable**: User should be able to decide

## After User Chooses

1. Record decision in `.claude/context/decisions.json`
2. Trigger `pof-adr-writer` if architectural
3. Update any affected context files
4. Proceed with chosen option

## Example

```markdown
## Alternatives: State Management

### Context
The app needs client-side state management for user preferences and cart data.

### Options

#### Option 1: Zustand ⭐ Recommended
Lightweight, minimal boilerplate state management.

| Aspect | Assessment |
|--------|------------|
| Fit for project | Excellent - right size for this scope |
| Complexity | Low |
| Community/Support | Strong, active maintenance |
| Long-term viability | Good - simple API unlikely to break |

**Pros:**
- Minimal boilerplate
- No providers needed
- TypeScript native
- Small bundle size

**Cons:**
- Less ecosystem than Redux
- No dev tools (though zustand/devtools exists)

---

#### Option 2: Redux Toolkit
Industry standard, full-featured state management.

| Aspect | Assessment |
|--------|------------|
| Fit for project | Overkill for current scope |
| Complexity | Medium |
| Community/Support | Excellent |
| Long-term viability | Excellent |

**Pros:**
- Extensive ecosystem
- Excellent dev tools
- Well-documented patterns

**Cons:**
- More boilerplate
- Larger bundle
- Steeper learning curve

---

### Recommendation
**Zustand** - This project's state needs are straightforward. Zustand provides what we need without overhead.

### Your Input Needed
- Team familiarity with either library?
- Plans for complex state in the future?
```
