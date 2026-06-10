---
name: pr-comments-flow
description: "Interactive PR comment review — goes through each review suggestion one by one, decides with the user how to proceed, marks as resolved on GitHub, and learns patterns for CLAUDE.md. Use this skill whenever the user wants to review PR comments, respond to code review suggestions, resolve PR threads, or says: 'let's review the PR comments', 'let's see the PR comments', 'there are comments on the PR to resolve', 'show me what the reviewer asked for', 'let's go through the comments', '/pr-comments-flow', or any variation of wanting to work on code review feedback."
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
---

# Skill: Interactive PR Comment Review

## Available Scripts

All scripts are in `~/.claude/skills/pr-comments-flow/scripts/` and must be called via the Bash tool.

| Script | Use | Description |
|--------|-----|-------------|
| `pr-fetch.sh <PR>` | Step 2 | Fetches, deduplicates, and saves comments to `/tmp/pr-{N}-comments.json` |
| `pr-next-comment.sh [PR]` | Step 4 | Returns the next pending comment as JSON |
| `pr-excerpt.sh <file> <line> [ctx=15]` | Step 4 | Extracts file snippet around a specific line |
| `pr-reply.sh <comment_id> <body>` | Step 5 | Posts a reply to the comment thread |
| `pr-resolve.sh <thread_id>` | Step 5 | Marks thread as resolved on GitHub |
| `pr-update-progress.sh <PR> <id> <status>` | Step 5 | Updates progress file (`applied`/`skipped`) |
| `pr-progress.sh [PR]` | Anytime | Displays current progress summary |

**State files in `/tmp/`:**
- `/tmp/pr-{N}-comments.json` — pre-processed and deduplicated comments
- `/tmp/pr-{N}-progress.json` — session progress tracking

---

## Step 1 — Identify PR

```bash
gh pr view --json number,title,url 2>/dev/null
```

If found, proceed directly — just inform in the first message:

```
PR #123 — PR Title
Fetching comments...
```

If it fails or is not found, use AskUserQuestion:

```
question: "I couldn't find an open PR on this branch. What is the number?"
header: "PR"
options:
  - label: "Provide number"
    description: "Enter the PR number in the 'Other' field"
  - label: "Cancel"
    description: "Ends the review"
```

If the user cancels, end. If provided via "Other", use the given number.

---

## Step 1b — Save local changes

Immediately after confirming the PR, silently save any uncommitted changes:

```bash
git stash --include-untracked
```

- If output contains `Saved working directory` → record `HAS_STASH=true`
- If output is `No local changes to save` → record `HAS_STASH=false`
- **Do not inform the user** — proceed silently.

---

## Step 2 — Pre-process comments

Always re-fetch from GitHub to ensure up-to-date data:

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-fetch.sh {PR_NUMBER}
```

If previous progress exists (`/tmp/pr-{N}-progress.json`), after fetching use AskUserQuestion:

```
question: "I found progress from a previous session (X applied, Y skipped). How should we proceed?"
header: "Progress"
options:
  - label: "Continue from where I left off"
    description: "Skips already handled comments"
  - label: "Start from scratch"
    description: "Revisits all comments, including those already handled"
```

If "Start from scratch", delete the progress file:
```bash
rm /tmp/pr-{PR_NUMBER}-progress.json
```

If no pending comments are found, inform: `No open review comments found for this PR.`

---

## Step 3 — Present summary

Read the comments file and show the summary organized by file. **Read only the necessary fields for the summary:**

```bash
jq -r '.files[] | "  📄 \(.path) (\(.comments | length) comment(s))"' /tmp/pr-{N}-comments.json
```

```
Found X comments in Y file(s):

  📄 src/services/PaymentService.ts (2 comments)
  📄 src/Models/Contract.ts (1 comment)
```

Proceed directly to Step 4 without waiting for a response.

---

## Step 4 — Review comment by comment

### 4a. Get next comment

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-next-comment.sh {PR_NUMBER}
```

This returns a JSON with: `id`, `path`, `line`, `body`, `thread_id`, `diff_hunk`, `duplicate_count`.

If `duplicate_count > 0`, add a note: `⚠️ This comment appeared {N+1}x from different reviewers.`

### 4b. Get file context (lazy — only relevant lines)

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-excerpt.sh "{path}" {line}
```

**Do not use the Read tool to read the entire file.** Use `pr-excerpt.sh` which returns ±15 lines around the commented line. Only use Read if you need much broader context and it is clearly necessary.

### 4c. Display and propose

Always show in this format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 src/services/PaymentService.ts — line 42
[X/TOTAL]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 Reviewer:
"This method can throw an unhandled exception if $amount is negative."

📌 Diff:
  (last lines of diff_hunk)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Analyze the comment + file context, write the proposal in text, then use AskUserQuestion:

```
question: "💡 What I plan to do: {summarized proposal}. How should we proceed?"
header: "Comment X/TOTAL"
options:
  - label: "Apply"
    description: "Implements the proposed change"
  - label: "Apply + CLAUDE.md"
    description: "Implements and adds a rule to CLAUDE.md to reinforce the pattern"
  - label: "Skip"
    description: "Does not apply; marks as handled and moves to the next"
  - label: "Discuss / Reply on PR"
    description: "Suggests something different or posts a reply to the thread without changing code"
```

Wait for a response before any action.

### 4d. Responses

- **Apply** — implement. After implementing, briefly confirm.
- **Apply + CLAUDE.md** — implement and then go directly to Step 6 to propose the instruction without asking again.
- **Skip** — do not change anything. Move to the next.
- **Discuss / Reply on PR** — use AskUserQuestion to distinguish:

```
question: "How do you want to proceed?"
header: "Action"
options:
  - label: "Discuss"
    description: "Suggest a different approach and I will update the proposal"
  - label: "Reply on PR"
    description: "I will draft a reply for the GitHub thread without changing code"
```

If **Discuss**: listen to the suggestion via "Other", update the proposal, and use AskUserQuestion again (Step 4c).

If **Reply on PR**: draft the reply in text and use AskUserQuestion to confirm:

```
question: "Confirm sending this reply to the thread?\n\n{reply text}"
header: "Reply on PR"
options:
  - label: "Post"
    description: "Sends the reply to the GitHub thread"
  - label: "Cancel"
    description: "Does not post anything"
```

Only post after confirming "Post":

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-reply.sh {COMMENT_ID} "{REPLY_BODY}"
```

---

## Step 5 — Update progress and resolve thread

After each comment (applied or consciously skipped), execute **in parallel**:

```bash
# Update local progress
~/.claude/skills/pr-comments-flow/scripts/pr-update-progress.sh {PR_NUMBER} {COMMENT_ID} {applied|skipped}

# Mark thread as resolved on GitHub
~/.claude/skills/pr-comments-flow/scripts/pr-resolve.sh {THREAD_ID}
```

If `thread_id` is `null`, skip resolution without error.

> If the resolution script fails, notify and continue.

---

## Step 6 — Propose learning for CLAUDE.md

This step is only executed when the user chose the **[2] Apply + CLAUDE.md** option in Step 4d. Do not ask again — go straight to the proposal.

Analyze the identified pattern, formulate the rule, and use AskUserQuestion:

```
question: "📚 Add to CLAUDE.md:\n\n\"{proposed rule}\""
header: "CLAUDE.md"
options:
  - label: "Add"
    description: "Saves the rule to the nearest CLAUDE.md from the CWD"
  - label: "Don't add"
    description: "Moves to the next comment without saving"
```

If "Add", find the nearest CLAUDE.md from the current directory and add to the `## Rules derived from Code Review` section (create the section if it doesn't exist):

```bash
# Finds the nearest CLAUDE.md by moving up from CWD
dir=$(pwd)
while [[ "$dir" != "/" ]]; do
  [[ -f "$dir/CLAUDE.md" ]] && { echo "$dir/CLAUDE.md"; break; }
  dir=$(dirname "$dir")
done
```

If no file is found, create `CLAUDE.md` in the current directory.

> Use `CLAUDE.local.md` only if the user explicitly requests it (e.g., "add to local", "I don't want to version it").

**If "Don't add":** proceed to the next comment without any additional action.

---

## Step 6b — Incremental commit

After each **applied** comment (and after deciding on CLAUDE.md), commit immediately. Generate a semantic message consistent with the applied change — based on what was changed in the file and what the reviewer requested:

```bash
git add -A && git commit -m "{type}: {description consistent with the applied change}"
```

Example: if the reviewer asked to extract a function and you extracted it in `PaymentService.ts`, the message would be `refactor: extract fee calculation to dedicated method`.

---

## Step 7 — Move to next file

When finished with all comments in a file:

```
✅ src/services/PaymentService.ts completed (2/2 comments handled).

Next: 📄 src/Models/Contract.ts (1 comment).
```

Go back to **Step 4** with `pr-next-comment.sh` for the next comment.

---

## Step 8 — Final commit (if there are pending changes)

Before the final summary, check if there are any uncommitted changes left (could happen if an incremental commit failed):

```bash
git status --porcelain
```

If there are any changes (modified, deleted, untracked), commit immediately:

```bash
git add -A && git commit -m "{type}: {description consistent with the remaining changes}"
```

---

## Step 9 — Push

After Step 8, push immediately without asking:

```bash
git push
```

---

## Step 9b — Restore local changes

After pushing, if `HAS_STASH=true`, restore the saved changes:

```bash
git stash pop
```

If it fails (conflict), inform:
```
⚠️ Could not restore saved changes automatically.
Run `git stash pop` manually to resolve conflicts.
```

---

## Step 10 — Final summary

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-progress.sh {PR_NUMBER}
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Review completed — PR #123

  Applied:              3
  Skipped:              1
  Resolved on GitHub:   4

  Rules added to CLAUDE.md: 1
  Commits made:         3
  Push made:            yes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Guiding Principles

- **Mandatory automatic stash** — immediately after confirming the PR (Step 1b), always run `git stash --include-untracked` to ensure a clean working tree. Restore with `git stash pop` after pushing (Step 9b) if there were saved changes.
- **Always use AskUserQuestion** — every user decision must be made via AskUserQuestion, never via free text `[y/N]` or numbered lists in the output.
- **Always propose before acting** — never change anything without confirmation.
- **Use scripts, not inline API** — never call `gh api` directly when a script is available.
- **Minimal context** — use `pr-excerpt.sh` instead of Read for files; use `pr-next-comment.sh` instead of reading the entire JSON.
- **Always re-fetch** — never use a comments cache; always run `pr-fetch.sh` at the start to ensure synchronization with GitHub.
- **Don't get stuck on API errors** — if resolving the thread fails, notify and continue.
- **CLAUDE.md only on demand** — Step 6 is only executed when the user chooses `[2] Apply + CLAUDE.md`. Never ask automatically after applying. When triggered, propose the rule directly without asking again. Always use the `CLAUDE.md` nearest to the CWD. Only use `CLAUDE.local.md` if the user explicitly requests it.
- **Mandatory incremental commit** — after each applied comment (Step 6b), commit immediately with a message consistent with the change. Do not ask, just commit. Step 8 only handles remaining pending changes.
- **Mandatory push at the end** — after Step 8, push without asking.
- **Language**: always respond in English.
