---
name: my-prs
description: Use when the user wants to see all their open pull requests, check PR status, review pipeline results, detect merge conflicts, or get a dashboard of in-progress work across repos. Triggers on "list my PRs", "show my pull requests", "what PRs do I have open", "PR dashboard", or any variation.
---

# My PRs

Lists all open PRs for the authenticated GitHub user across the px-center org, grouped by repo. Output is Slack-optimized.

## Usage

```bash
python3 ~/.claude/skills/my-prs/my-prs.py
```

Print the output directly to the user — it's already Slack-ready.

## Output Format

Two sections. Each PR shows three lines: project (`▸ <repo>`), PR title, and an explicit raw link (`→ <url>`).

**Ready to merge** = not draft + approved + mergeable + no pending reviewers + CI passing/none + not dirty. Three-line block per PR — no status lines (it's ready, just go).

**Needs my attention** = everything else. Same three-line block, plus problem lines branched under the PR with `┣━`/`┗━` connectors. Only problems are shown — green/OK states are hidden.

```
📋 MY OPEN PRs — N total
✓ X ready · ⚠ Y needs attention
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━ ✓ READY TO MERGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ▸ <repo>
    <title>
    → <url>

━━━ ⚠ NEEDS MY ATTENTION ━━━━━━━━━━━━━━━━━━━━━━━━

  ▸ <repo>
    <title>
    → <url>
    ┗━ <symbol> <reason>
```

Problem-line symbols (each only if it applies):
`🚧 draft` · `🔄 changes requested` · `👀 needs review (N approvals)` · `⛔ pending required review: <team/user>` · `⬇️ behind base branch` · `⚠ has conflicts` · `❓ merge state unknown` · `❌ CI failing` · `⏳ CI pending`
