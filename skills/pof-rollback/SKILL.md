---
name: pof-rollback
description: Display rollback instructions for the current POF state. Shows how to undo recent changes.
---

# POF Rollback

Display instructions for rolling back recent changes.

## When to Use

- Deployment went wrong
- Need to undo recent changes
- User wants to know recovery options

## Process

1. Check `.claude/context/rollback.md` for documented rollback steps
2. Check git history for recent commits
3. Check deployment status if applicable
4. Present rollback options

## Output Format

```markdown
## Rollback Options

### Git Rollback

**Last commits:**
```
{git log --oneline -5}
```

**To undo last commit (keep changes):**
```bash
git reset --soft HEAD~1
```

**To undo last commit (discard changes):**
```bash
git reset --hard HEAD~1
```

### Deployment Rollback

**Current deployment:**
- Environment: {production/staging}
- Deployed at: {timestamp}
- Commit: {hash}

**To rollback:**
```bash
{deployment-specific rollback command}
```

### Database Rollback

{If applicable, migration rollback steps}

### Manual Recovery

If automated rollback fails:
1. {Step 1}
2. {Step 2}
```

## Check Rollback Documentation

Read from `.claude/context/rollback.md` if it exists:
```bash
cat .claude/context/rollback.md 2>/dev/null
```

## Git History

Show recent commits:
```bash
git log --oneline -10
```

## Deployment History

Check deployment platform for history:
- Vercel: `vercel ls`
- Azure SWA: Check Azure Portal
- Docker: Check container registry tags

## Safety Warnings

Always warn about:
- Data loss from hard resets
- Production impact
- Database migration irreversibility
- Downstream effects

```markdown
⚠️ **Warning**: Rolling back in production may cause:
- Brief downtime
- Loss of data created since deployment
- Need to re-run migrations

Proceed with caution.
```
