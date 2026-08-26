---
name: pr-comments-flow
description: "Step-by-step interactive flow to review, apply, skip, or reply to open GitHub PR review comments. Triggers on: /pr-comments-flow, 'review PR comments', 'go through PR comments', 'address review feedback', 'respond to PR review', 'resolve review threads'."
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, AskUserQuestion, TodoWrite
disable-model-invocation: true
---

# Skill: Interactive PR Comment Review

## Flow Overview

```
1 Identify PR → 1b Stash → 1c Read PR scope → 2 Fetch → 3 Summary →
LOOP per comment: [4 Review → 5 Progress/Resolve → (6 CLAUDE.md) → 6b Commit] →
7 Next file → repeat LOOP until pr-next-comment.sh returns no pending comment →
8 Final commit → 9 Push → 9b Unstash → 10 Summary
```

The loop ends ONLY when `pr-next-comment.sh` returns empty/no pending comment. Never stop mid-loop because the conversation is long; state lives in `/tmp/pr-{N}-progress.json`, so after a context compaction resume by running `pr-progress.sh` then `pr-next-comment.sh`.

## Available Scripts

Scripts in `~/.claude/skills/pr-comments-flow/scripts/` (set `SKILL_SCRIPTS=~/.claude/skills/pr-comments-flow/scripts` once and reuse). Call via Bash tool.

| Script | Use | Description |
|--------|-----|-------------|
| `pr-fetch.sh <PR>` | Step 2 | Fetch, deduplicate, save comments to `/tmp/pr-{N}-comments.json` |
| `pr-next-comment.sh [PR]` | Step 4 | Return next pending comment JSON |
| `pr-excerpt.sh <file> <line> [ctx=15]` | Step 4 | Extract file snippet around line |
| `pr-reply.sh <comment_id> <body>` | Step 5 | Post reply to thread |
| `pr-resolve.sh <thread_id>` | Step 5 | Mark thread resolved on GitHub |
| `pr-update-progress.sh <PR> <id> <status>` | Step 5 | Update progress file (`applied`/`skipped`/`ignored`) |
| `pr-progress.sh [PR]` | Anytime | Show current progress summary |

**State files in `/tmp/`:**
- `/tmp/pr-{N}-comments.json` — pre-processed comments
- `/tmp/pr-{N}-progress.json` — progress tracking

---

## Step 1 — Identify PR

```bash
gh pr view --json number,title,url,body 2>/dev/null
```

If found, proceed. Inform:

```
PR #{number} — {title}
Fetching comments...
```

If fail/not found, use AskUserQuestion:

```yaml
question: "No open PR found on branch. What is the number?"
header: "PR"
options:
  - label: "Provide number"
    description: "Enter PR number in 'Other' field"
  - label: "Cancel"
    description: "End review"
```

If cancel, end. If provided, use given number.

---

## Step 1b — Save local changes

Silently save uncommitted changes:

```bash
git stash --include-untracked
```

- If output has `Saved working directory` → remember `HAS_STASH=true` (you must restore in Step 9b)
- If output is `No local changes to save` → `HAS_STASH=false`
- If command fails for another reason → warn user and ask whether to continue
- Do not inform user on success.

---

## Step 1c — Read PR scope

Read the `body` from Step 1 (if Step 1 used a user-supplied number, fetch it: `gh pr view {PR_NUMBER} --json title,body`).

Extract and hold for the whole session — this is `PR_SCOPE`:
- **Goal** — what the PR sets out to do (feature, refactor, bugfix, chore).
- **Explicit non-goals** — anything the description defers or declares out of scope.
- **Referenced spec** — handoff, Jira ticket, design doc named in the body.

If the body is empty or says nothing about intent, set `PR_SCOPE = unknown` and judge comments on their own merit.

Inform the user in one or two lines, then proceed:

```
🎯 PR SCOPE: {one-line goal}
   Out of scope: {non-goals, or "none stated"}
```

`PR_SCOPE` weights every recommendation in Step 4c — it never silences a comment. See **Scope-Weighted Recommendation** in Guiding Principles.

---

## Step 2 — Pre-process comments

Re-fetch comments:

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-fetch.sh {PR_NUMBER}
```

If no comments, inform: `No open review comments found for this PR.`

---

## Step 3 — Present summary

Summarize files. Read only necessary fields:

```bash
jq -r '.files[] | "  📄 \(.path) (\(.comments | length) comment(s))"' /tmp/pr-{N}-comments.json
```

Format:
```
📁 ACTIVE REVIEW COMMENTS SUMMARY

  📄 src/services/PaymentService.ts (2 comments)
  📄 src/models/Contract.ts (1 comment)

  Total: X active comments in Y file(s)
--------------------------------------------------
```

Create a TodoWrite item per file (`{path} (N comments)`). Proceed to Step 4 without waiting.

---

## Step 4 — Review comment by comment

### 4a. Get next comment

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-next-comment.sh {PR_NUMBER}
```

Returns JSON: `id`, `path`, `line`, `body`, `user`, `created_at`, `thread_id`, `diff_hunk`, `duplicate_count`.

If output is empty or reports no pending comments, all comments are handled — go to Step 8.

If `duplicate_count > 0`, note: `⚠️ This comment appeared {N+1}x from different reviewers.`

### 4b. Get file context

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-excerpt.sh "{path}" {line}
```

Only use `pr-excerpt.sh` (±15 lines around commented line). Do not use Read tool unless broader context is required.

### 4c. Display and propose

MANDATORY SEQUENCE — two distinct outputs, in order:
1. Print the full display block below as a TEXT message in chat (comment body, diff, proposed change). This is the user's only way to see the comment — never skip or summarize it.
2. Only AFTER the display block is printed, call AskUserQuestion.

Calling AskUserQuestion without first printing the display block is a hard error: the user would be choosing blind.

Always show exactly in this format. The file location is its own top-level code block, formatted `{path}:{line}` (e.g. `src/components/DailyValuesBoard.tsx:72`), so the terminal renders the clickable path-with-line. Header/diff inside a plain fence; PROPOSED CHANGE must be a separate top-level fenced block with the language tag (NOT nested inside another fence), so the terminal applies syntax highlighting:

````
```
==================================================
💬 REVIEW COMMENT [X of TOTAL]
==================================================
```

📄 **File:**

```
{path}:{line}
```

```
👤 Reviewer: @{user} ({created_at})

"{body}"

--------------------------------------------------
📌 ORIGINAL DIFF:
  (last lines of diff_hunk)
```

💡 **PROPOSED CHANGE:**

```{language}
// Exact code showing the proposed new code or diff
```
````

Write detailed code block of proposed change above, then ask:

Use EXACTLY these 4 options and descriptions — do not rename, drop, or merge them. AskUserQuestion accepts max 4 options — never add a 5th.

Recommendation rule: decide which option best fits your assessment of the comment, weighed against `PR_SCOPE` from Step 1c. Append " (Recommended)" to that option's label and move it to FIRST position; keep the others in the order below. ALL 4 options must appear in every question — recommending one never removes the others.

Weigh the comment on two axes:

1. **Merit** — is the reviewer technically right? Verify the claim against the code; never take it on faith. A wrong premise is a `Skip` regardless of scope.
2. **Scope fit** — does fixing it belong in THIS PR, given `PR_SCOPE`?

| Situation | Lean |
|---|---|
| Right, and inside the PR's stated goal | `Apply` |
| Right, and a regression this PR introduced | `Apply` — always in scope, even if the goal never mentioned it |
| Right, user-visible bug or crash on a touched path | `Apply` — severity outranks scope |
| Right, but pre-existing and unrelated to the goal | `Skip` — say it is valid, out of scope, suggest a follow-up |
| Right, but the described fix makes things worse | `Skip` — explain the trade-off; do not apply a net-negative change |
| Explicitly listed as a non-goal in the description | `Skip` — cite the description |
| Style/preference with no behavioral effect on a refactor PR | `Skip` |
| Premise wrong, already handled elsewhere, or not applicable | `Skip` |
| Needs a product/architecture decision above this PR | `Ignore (Keep Open)` — leave it for the reviewer |

When scope is the deciding factor, state that explicitly in the assessment shown to the user, so the recommendation is auditable. If `PR_SCOPE = unknown`, use Merit alone and say so.

Descriptions are schema-required — keep them exactly this short, never longer:

```yaml
question: "Proposed change generated. How should we proceed?"
header: "Comment X/TOTAL"
options:
  - label: "Apply"
    description: "Write change to file"
  - label: "Apply + CLAUDE.md"
    description: "Write change + save rule"
  - label: "Skip (Resolve on GitHub)"
    description: "Reply in PT + resolve"
  - label: "Ignore (Keep Open)"
    description: "Keep thread open"
```

Discuss/Reply has no dedicated option (4-option cap): the user types free text via the built-in "Type something" entry. Treat any typed text as Discuss/Reply input (see 4d).

Option annotations (TAB): the user may select an option AND append a note (e.g. "Apply, but use useMemo instead"). ALWAYS honor the note — adjust the proposal per the note before executing the chosen action. If the note changes the code, show the revised code block before applying.

Wait for response.

### 4d. Responses

- **Apply** — write proposed code to file via Edit tool (must match preview exactly). Briefly confirm. Before resolving, ALWAYS post a reply on the thread:

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-reply.sh {COMMENT_ID} "Ajustado conforme sugerido."
```

- **Apply + CLAUDE.md** — write proposed code to file via Edit tool. Before resolving, ALWAYS post a reply on the thread:

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-reply.sh {COMMENT_ID} "Ajustado conforme sugerido."
```

Then go to Step 6.
- **Skip** — no code change. Before resolving, ALWAYS post a reply on the thread in Portuguese explaining why the comment is being skipped (e.g. "Já tratado em outro ponto do PR" / "Decidimos manter a abordagem atual porque…"). When scope was the reason, acknowledge the point is valid and name the boundary (e.g. "Procede, mas está fora do escopo deste PR, que trata só de {goal} — vale abrir tarefa própria."):

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-reply.sh {COMMENT_ID} "{EXPLICAÇÃO_EM_PORTUGUÊS}"
```

Then mark resolved on GitHub (Step 5), move next.
- **Ignore (Keep Open)** — no code change, keep thread open on GitHub, move next.
- **Typed free text ("Other")** — interpret intent:
  - Feedback/disagreement about the proposal → **Discuss**: update proposal with the feedback, re-display Step 4c.
  - Request to answer the reviewer → **Reply on PR**: draft reply, confirm before posting.

Reply confirmation flow:

```yaml
question: "Post this reply?\n\n{reply text}"
header: "Reply on PR"
options:
  - label: "Post"
    description: "Send reply to GitHub thread"
  - label: "Cancel"
    description: "Cancel reply"
```

If Post, run:
```bash
~/.claude/skills/pr-comments-flow/scripts/pr-reply.sh {COMMENT_ID} "{REPLY_BODY}"
```

---

## Step 5 — Update progress and resolve thread

After each comment:

- For `Apply`, `Apply + CLAUDE.md`, or `Skip`, run these in parallel (three Bash calls in one message; or two for `Skip` since its reply is handled in Step 4d):

```bash
# Reply to comment (for Apply and Apply + CLAUDE.md)
~/.claude/skills/pr-comments-flow/scripts/pr-reply.sh {COMMENT_ID} "Ajustado conforme sugerido."

# Update local progress
~/.claude/skills/pr-comments-flow/scripts/pr-update-progress.sh {PR_NUMBER} {COMMENT_ID} {applied|skipped}

# Resolve on GitHub
~/.claude/skills/pr-comments-flow/scripts/pr-resolve.sh {THREAD_ID}
```

- For `Ignore`, run:

```bash
# Update local progress (does NOT resolve thread)
~/.claude/skills/pr-comments-flow/scripts/pr-update-progress.sh {PR_NUMBER} {COMMENT_ID} ignored
```

If `thread_id` is `null`, skip resolution silently.
If resolution script fails, notify and continue.

---

## Step 6 — Propose learning for CLAUDE.md

Triggered ONLY on `Apply + CLAUDE.md`. Direct proposal, do not ask again.
Formulate rule, ask:

```yaml
question: "📚 Add to CLAUDE.md:\n\n\"{proposed rule}\""
header: "CLAUDE.md"
options:
  - label: "Add"
    description: "Save rule to nearest CLAUDE.md"
  - label: "Don't add"
    description: "Move next without saving"
```

If "Add", find nearest `CLAUDE.md` moving up from CWD. Append to `## Rules derived from Code Review` (create section if missing).

If no `CLAUDE.md` found, create in current directory.

Only use `CLAUDE.local.md` if user explicitly requests it.

---

## Step 6b — Incremental commit

After each applied comment (and CLAUDE.md choice), commit immediately. Match message to change:

```bash
git add -A && git commit -m "{type}: {description}"
```

*Example:* `refactor: extract fee calculation to dedicated method`

---

## Step 7 — Move to next file

When all comments in file finished:

```
✅ {path} completed ({handled}/{total} comments handled).

Next: 📄 {next_path} ({next_total} comment(s)).
```

Go back to Step 4.

---

## Step 8 — Final commit

Before final summary, check for uncommitted changes:

```bash
git status --porcelain
```

If changes exist, commit:

```bash
git add -A && git commit -m "{type}: {description}"
```

---

## Step 9 — Push

Push immediately without asking:

```bash
git push
```

---

## Step 9b — Restore local changes

If `HAS_STASH=true`, restore changes:

```bash
git stash pop
```

If conflict:
```
⚠️ Could not restore saved changes automatically. Run `git stash pop` manually to resolve conflicts.
```

---

## Step 10 — Final summary

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-progress.sh {PR_NUMBER}
```

Format:
```
==================================================
✅ REVIEW COMPLETED — PR #{PR_NUMBER}
==================================================

📊 SESSION STATISTICS:
  • Applied:             3
  • Skipped:             1
  • Ignored:             1
  • GitHub Resolved:     4

📝 CHANGELOG & SYNC:
  • Rules added to CLAUDE.md:  1
  • Commits made:              3
  • Push made:                 yes

==================================================
```

---

## Guiding Principles

- **Auto Stash** — Silent stash (`git stash --include-untracked`) on start. Restore with `git stash pop` on end.
- **AskUserQuestion** — All decisions via `AskUserQuestion` tool. No raw text options.
- **Propose First** — Never modify files without confirmation.
- **Proposed Change Preview** — Show exact proposed code block in chat before asking.
- **Use Scripts** — Do not call raw `gh api` when script exists.
- **Min Context** — Use `pr-excerpt.sh` and `pr-next-comment.sh`. Avoid whole-file reads.
- **Fresh Fetch** — No comment cache. Always run `pr-fetch.sh` at start.
- **No Translation** — Keep comment body, user, timestamp exactly as retrieved.
- **Direct CLAUDE.md** — Only on `Apply + CLAUDE.md`. Propose rule directly.
- **Incremental Commit** — Commit after each applied comment immediately.
- **Auto Push** — Push at end without asking.
- **Language** — Always respond in English.
- **Resumable** — After interruption or context compaction, run `pr-progress.sh` + `pr-next-comment.sh` to resume; never re-apply already-handled comments.
- **Loop Discipline** — One comment fully handled (Steps 4→6b) before fetching the next. Never batch.
- **Read Scope First** — Always read the PR description (Step 1c) BEFORE the first comment. Never enter the loop without `PR_SCOPE`.
- **Scope-Weighted Recommendation** — Recommendations weigh Merit (is the reviewer right?) against Scope fit (does it belong in THIS PR?). Scope adjusts the recommendation; it never hides a comment or skips its display. Regressions introduced by the PR and user-visible crashes are always in scope.
- **Recommend** — Tag best-fit option with "(Recommended)" and list it first in every Step 4c question.
- **Apply Explains** — Apply and Apply + CLAUDE.md always post the Portuguese reply `"Ajustado conforme sugerido."` on the thread before resolving.
- **Skip Explains** — Skip always posts a Portuguese reply on the thread justifying the decision before resolving.
- **Honor Annotations** — TAB-appended notes on a selected option modify the action; apply them before executing.
