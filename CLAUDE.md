- Do not add any "generated using" type of info in commit message
- ALWAYS use conventional commit format with mandatory scope: `type(scope): description`
  - Valid types: feat, fix, docs, style, refactor, perf, test, chore, build, ci
  - Scope MUST describe what part of the codebase is affected (e.g., frontend, backend, graph, api)
  - Example: `feat(graph): add jitter series on right Y-axis`
- Always use ISO date format (yyyy-mm-dd) unless the user specifies a different format
- Always format money the Finnish way: number first, space (non-breaking) as the thousands separator, € symbol after with a space, comma as decimal separator — e.g. `100 000 €`, `1 200 000 €`, `1 150 €/htp`. Never use a leading symbol or the `k`/`M` abbreviation (no `€100k`, no `€1.2M`). This applies everywhere, including English chat replies.
- Chat replies to me are always in English, even when the produced artifacts (docs, diagrams, slack drafts, summaries, commit messages) are in Finnish or another language. Don't switch the conversation to Finnish just because the latest artifact was Finnish.
- Never cause an unrequested destructive or irreversible side-effect on shared/remote state — especially open PRs, branches others track, force-push, and history rewrites. Renaming an open PR's head branch closes the PR, and PRs cannot be deleted: scope actions to exactly what was asked, prefer the minimal non-destructive path, and confirm before touching shared remote state. Never state platform/tool behavior as fact when it's a guess — say so and verify before irreversible steps.

## Understanding the request before building

- If a request can be read at more than one level — granularity, shape, scope, format, audience — ask ONE short clarifying question with your best guess as the default, BEFORE building anything. Ten seconds of my time beats a correction loop. Example: "One sequence at the level of the status steps with the triggers as messages — or every system call?"
- Never argue against a request you have rewritten in your head. Restate the request in one line first; only then raise concerns, and only about that restatement.
- Don't substitute your judgement of what the audience needs for the instruction given. I have usually already decided the level and the audience. If you think something is missing, say so in one line AFTER delivering exactly what was asked — never by adding it.
- A correction replaces the plan; it is not a patch applied inside the old plan. If a correction contradicts the container you built, the container goes.
- Literal instructions ("no prose", "only the diagram", "markdown only") apply to the whole deliverable, not just the part last touched.
- Deliverables are files in the formats I asked for. No second format (PDF, HTML, image, artifact link) unless asked.

## Useful commands

- **List open Dependabot alerts for the current repo** (same data surfaced in the push-time warning from GitHub):
  ```bash
  gh api repos/{owner}/{repo}/dependabot/alerts --jq '.[] | select(.state == "open") | "\(.security_vulnerability.severity)\t\(.security_vulnerability.package.name)\t\(.security_advisory.summary)"'
  ```
  `gh` auto-substitutes `{owner}` and `{repo}` from the current git remote. Add `select(.security_vulnerability.severity == "critical")` to filter by severity.

<!-- Private rules from the private companion repo; setup.sh links this file
     (or leaves an empty placeholder when the private repo is not installed). -->
@~/.claude/CLAUDE.private.md
