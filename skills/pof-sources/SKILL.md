---
name: pof-sources
description: Manage documentation source priorities for POF. View, add, or modify sources that agents use for research.
---

# POF Sources

Manage documentation sources that POF agents consult during research.

## Source Priority (Higher number = Higher priority)

1. User-provided URLs in conversation
2. Project sources (`.claude/sources.md`)
3. Global sources (`~/.claude/sources.md`)
4. Official documentation (agent defaults)

## View Current Sources

Check both project and global sources:

```bash
echo "=== Project Sources ==="
cat .claude/sources.md 2>/dev/null || echo "No project sources file"

echo ""
echo "=== Global Sources ==="
cat ~/.claude/sources.md 2>/dev/null || echo "No global sources file"
```

## Sources File Format

```markdown
# Documentation Sources

## Project-Specific
- [Internal API Docs](https://internal.example.com/api)
- [Team Wiki](https://wiki.example.com)

## Technology

### Next.js
- [Team Next.js Guide](https://wiki.example.com/nextjs) (priority: 1)
- [Official Docs](https://nextjs.org/docs) (default)

### Bun
- [Official Docs](https://bun.sh/docs) (default)

### shadcn/ui
- [Official Docs](https://ui.shadcn.com) (default)

### Azure SWA
- [Internal Azure Guide](https://wiki.example.com/azure) (priority: 1)
- [Official Docs](https://learn.microsoft.com/azure/static-web-apps) (default)
```

## Commands

### Add a Source

To add a project source:
```bash
mkdir -p .claude
cat >> .claude/sources.md << 'EOF'

### {Technology}
- [{Name}]({URL}) (priority: 1)
EOF
```

### Create Sources File

If starting fresh:
```bash
cat > .claude/sources.md << 'EOF'
# Documentation Sources

## Project-Specific
<!-- Add project-specific documentation links here -->

## Technology
<!-- Add technology-specific sources, higher priority overrides lower -->
EOF
```

## Usage by Agents

When `pof-doc-researcher` or other agents need documentation:
1. They check for explicit URLs in their prompt first
2. Then read `.claude/sources.md` in the project
3. Then read `~/.claude/sources.md` for global preferences
4. Finally, fall back to their built-in knowledge and web search

## Tips

- Use `(priority: N)` to override defaults within a technology
- Use `(default)` to mark fallback sources
- Project sources take precedence over global sources
- User-provided URLs in conversation always win
