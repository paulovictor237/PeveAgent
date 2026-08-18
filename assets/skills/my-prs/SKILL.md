---
name: my-prs
description: Use when the user wants to see all their open pull requests, check PR status, review pipeline results, detect merge conflicts, or get a dashboard of in-progress work across repos. Triggers on "list my PRs", "show my pull requests", "what PRs do I have open", "PR dashboard", or any variation.
---

# My PRs

Lists all open PRs for the authenticated GitHub user across the px-center org, grouped by repo. Output is **plain text in a tree layout** (Portuguese labels) — compact, terminal-friendly, easy to copy into other chats.

## Usage

```bash
python3 ~/.claude/skills/my-prs/my-prs.py
```

Print the output directly to the user, verbatim, inside a code block so the tree alignment is preserved.

## Output Format

Header line with totals, then two sections. **Only what matters is shown** — positive/green stages are hidden; each `╰─` line is an item that needs action (or context on it).

- **`✅ PRONTOS PRA MERGE`** — clean PRs. Title + link + comment count only, no approve count/approvers, no other status noise.
- **`⚠️ PRECISAM DE ATENÇÃO`** — title + link, then actionable lines + approve count/approvers (always) + comment count.

Each repo is a `📦 repo · N PRs` group. Each PR is `[#num] title` followed by its `╰─` lines.

```
📋 Meus PRs abertos — N no total em X repo(s)
   ✅ M prontos pra merge · ⚠️ Y precisam de atenção

━━━ ⚠️ PRECISAM DE ATENÇÃO ━━━

📦 repo-name · 2 PRs

[#1583] [EER-397] - Ajusta layout e validações do formulário de avaliação
╰─ 🔗 https://github.com/px-center/px-painel/pull/1583
╰─ 👀 review pendente · ✅ 2 já aprovaram: felipesdl, tchiteu
╰─ ⛔ squads pendentes: px-center/squad-contracts
```

## Lines shown (only when they matter)

| Line | When shown |
|---|---|
| `🔗 <url>` | always |
| `🚧 rascunho (draft)` | only if draft |
| `🔄 mudanças solicitadas: …` | only if changes requested — names who requested them |
| `👀 review pendente` | only if not yet approved |
| `✅ N já aprovaram: …` (or `✅ 0 aprovou`) | always, in attention section — count + names regardless of approval state |
| `☢️ tem conflitos` · `⬇️ atrás da base` | only if not mergeable |
| `💥 CI falhando` · `⏳ CI rodando` | only if CI failing/pending |
| `⛔ squads pendentes: …` · `⛔ reviewers pendentes: …` | only if pending |
| `💬 N comentário(s) não resolvido(s)` | always — the only count shown regardless of value, including 0 |

Green stages (não-draft, aprovado, mergeable, CI passando, sem bloqueios) are **never printed** — their absence means they're fine. Comment count is the one exception: always printed, even at 0.

**Prontos pra merge** = not draft + approved + mergeable + no pending squads/reviewers + CI passing/none + not dirty + zero unresolved review comments.

Unresolved count comes from GitHub review threads (`isResolved == false`), same source `pr-comments-flow` uses — one PR with open threads always lands in "precisam de atenção" even if otherwise approved/green.
