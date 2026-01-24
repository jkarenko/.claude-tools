---
name: pof-clarify
description: Structure clarifying questions for the user during POF workflow. Used when requirements are unclear or decisions need input.
---

# POF Clarify

Use this skill to ask well-structured clarifying questions during the POF workflow.

## When to Use

- Requirements are ambiguous
- Multiple valid approaches exist
- User intent is unclear
- Technical decision needs user input

## Question Format

Present questions clearly:

```markdown
## Clarification Needed

**Context**: {Brief context for why this matters}

**Question**: {The specific question}

**Options** (if applicable):
1. **{Option A}**: {Brief description}
   - Pros: {advantages}
   - Cons: {disadvantages}

2. **{Option B}**: {Brief description}
   - Pros: {advantages}
   - Cons: {disadvantages}

**Default recommendation**: {Which option and why, if you have a preference}
```

## Guidelines

- **One topic per clarification**: Don't bundle unrelated questions
- **Provide context**: Explain why the answer matters
- **Offer options when possible**: Easier to choose than to create
- **State your recommendation**: Guide but don't decide for user
- **Be concise**: Don't over-explain

## Examples

### Good Clarification

```markdown
## Clarification Needed

**Context**: The app needs user authentication. This affects security, UX, and infrastructure choices.

**Question**: What authentication method should we use?

**Options**:
1. **Email/Password**: Traditional approach
   - Pros: Full control, no external dependencies
   - Cons: Must handle password security, reset flows

2. **OAuth only** (Google, GitHub, etc.): Social login
   - Pros: No passwords to manage, users trust providers
   - Cons: Depends on external services, limited to supported providers

3. **Passwordless** (magic links, passkeys): Modern approach
   - Pros: No passwords, good security
   - Cons: Email dependency, newer pattern

**Default recommendation**: OAuth with optional email/password for flexibility.
```

### Bad Clarification (avoid)

```
What do you want to do for auth? There are many options like OAuth, passwords, magic links, passkeys, SAML, LDAP, etc. Each has trade-offs. What are your security requirements? Do you need SSO? What about MFA?
```

## Recording Clarifications

After user responds, record the decision in `.claude/context/decisions.json` if it's architectural, or just proceed if it's minor.

## Escalation

If user can't decide:
1. Offer to proceed with a sensible default
2. Note it can be changed later
3. Document the assumption
