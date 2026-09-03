---
name: commit
description: Create a conventional commit for staged changes. Analyzes the diff, generates a message with mandatory scope, and commits. Use when the user says "commit", "done", "ready to commit", or similar.
---

# Commit

Analyze staged changes and create a conventional commit.

## Workflow

### 1. Check for Staged Changes

```bash
git diff --cached --stat
```

If nothing is staged, check for unstaged changes:
```bash
git status --short
```

If there are unstaged changes, ask the user what to stage. If there are no changes at all, inform the user and stop.

### 2. Analyze the Diff

```bash
git diff --cached
```

Review the staged changes to understand:
- What type of change this is (feat, fix, refactor, etc.)
- Which part of the codebase is affected (the scope)
- The core purpose of the changes

### 3. Check Recent History

```bash
git log --oneline -10
```

Review recent commits to maintain consistent style and understand context.

### 4. Generate Commit Message

Create a conventional commit message following these rules:

**Format** (mandatory scope per project convention):
```
type(scope): description

[optional body]
```

**Types**:
| Type | Use For |
|------|---------|
| `feat` | New features or functionality |
| `fix` | Bug fixes |
| `docs` | Documentation changes |
| `style` | Code style (formatting, no logic change) |
| `refactor` | Refactoring without behavior change |
| `perf` | Performance improvements |
| `test` | Adding or modifying tests |
| `chore` | Maintenance, dependencies, build |
| `build` | Build system changes |
| `ci` | CI/CD changes |

**Scope**: Describes what part of the codebase is affected (e.g., `auth`, `dashboard`, `api`, `ui`, `config`, `deps`). Always include a scope.

**Description rules**:
- Imperative mood: "add" not "added" or "adds"
- Lowercase after colon
- No period at end
- Under 50 characters when possible
- Specific and meaningful (never "update files" or "fix stuff")

**Body** (include when helpful):
- Explain the "why", not the "what"
- Use bullet points for multiple related changes
- Wrap at 72 characters

### 5. Present and Commit

Show the proposed commit message to the user. If they approve (or didn't ask for review), execute:

```bash
git commit -m "$(cat <<'EOF'
type(scope): description

Optional body here.
EOF
)"
```

### 6. Verify

```bash
git log --oneline -1
```

Confirm the commit was created.

## Rules

- **No AI attribution**: Never include "by Claude", "Co-Authored-By", or similar
- **One logical change per commit**: If changes span unrelated areas, suggest splitting
- **Never commit secrets**: Warn if staged files look like `.env`, credentials, or keys
- **Don't push**: Only commit locally. Never push unless the user explicitly asks
- **Don't amend**: Always create new commits unless the user specifically asks to amend

## Examples

Simple feature:
```
feat(auth): add Google OAuth login flow
```

Bug fix:
```
fix(calendar): correct timezone offset in booking display
```

Multiple related changes:
```
feat(admin): implement student lesson management

- Add lesson creation form with validation
- Create POST /api/admin/lessons endpoint
- Display student lessons in admin panel
```

Refactor:
```
refactor(components): extract shared form logic into useFormState hook
```
