---
name: pof-env-config
description: Manage environment variables for POF projects. Create .env.example, guide user through setting values.
---

# POF Environment Config

Manage environment variables for the project.

## Principles

- **Never create `.env.local` with real values**: User must set secrets
- **Always create `.env.example`**: Document required variables
- **Never commit secrets**: Ensure `.env.local` is in `.gitignore`

## Process

### 1. Audit Required Variables

Check the codebase for environment variable usage:
```bash
grep -r "process.env\." --include="*.ts" --include="*.tsx" --include="*.js" | grep -v node_modules | sort -u
```

### 2. Create .env.example

```bash
cat > .env.example << 'EOF'
# ===================
# Required Variables
# ===================

# Database
DATABASE_URL=

# Authentication
AUTH_SECRET=    # Generate with: openssl rand -base64 32

# ===================
# Optional Variables
# ===================

# Analytics (optional)
ANALYTICS_ID=

# ===================
# Development Only
# ===================

# Debug mode
DEBUG=false
EOF
```

### 3. Verify .gitignore

```bash
# Check if .env.local is ignored
grep -q "\.env\.local" .gitignore || echo ".env.local" >> .gitignore
grep -q "\.env" .gitignore || echo ".env" >> .gitignore
```

### 4. Guide User

Present variables that need values:

```markdown
## Environment Setup Required

The following environment variables need to be set in `.env.local`:

| Variable | Purpose | How to Get |
|----------|---------|------------|
| `DATABASE_URL` | Database connection | Your database provider |
| `AUTH_SECRET` | Session encryption | Run: `openssl rand -base64 32` |

### Steps

1. Copy the example file:
   ```bash
   cp .env.example .env.local
   ```

2. Edit `.env.local` and fill in your values

3. Never commit `.env.local` to git
```

## Variable Categories

### Required
Variables the app cannot start without.

### Optional
Variables with sensible defaults or optional features.

### Development Only
Variables only needed in development (DEBUG, etc.)

### Build Time vs Runtime

Note which variables are needed at:
- **Build time**: `NEXT_PUBLIC_*` variables
- **Runtime**: Server-side variables

## Security Notes

- `NEXT_PUBLIC_*` variables are exposed to the browser
- Server-only variables should never have `NEXT_PUBLIC_` prefix
- API keys for client-side services (maps, analytics) can be public
- Database URLs, auth secrets must never be public
