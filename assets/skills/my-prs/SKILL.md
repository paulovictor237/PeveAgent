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

```
📋 N open PRs across M repos — X ready to merge, Y need review

px-center/<repo>
• [#<number>] <title>
  🔗 <url>
  🚧 Draft          (only if draft)
  👀 Needs review (N approvals) | ✅ Ready to merge | 🔄 Changes requested
  ✅ No conflicts | ⚠️ Has conflicts | ❓ Conflict state unknown
  ✅ CI passing | ❌ CI failing | ⏳ CI pending | ➖ No CI
```
