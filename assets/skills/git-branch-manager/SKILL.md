---
name: git-branch-manager
description: >
  Git branch hygiene — audit, classify, and safely delete branches.
  Detects merged, stale, and active branches. Auto-detects protected branches.
  Trigger: "clean up branches", "stale branches", "branch audit", "delete merged",
  "which branches can I delete", "branch status", "/branches", "/git-branch-manager".
---

## When to Use

- User wants to clean up git branches
- User asks which branches are safe to delete
- User mentions stale, merged, or old branches
- User wants a branch health audit
- Periodic maintenance (branches piling up)

## Procedure

### Step 1 — Gather Branch Data

Run the script:

```
~/.claude/skills/git-branch-manager/scripts/branch-scan.sh
```

It outputs a JSON report with:
- `current_branch` — branch you're on (never deleteable)
- `protected` — main/master + other protected refs
- `local_only` — branches with no remote tracking
- `merged` — branches already merged into HEAD
- `stale` — branches with last commit older than 30 days (configurable via `STALE_DAYS` env var)
- `with_pr` — branches that have an open GitHub PR (if `gh` CLI is available)

### Step 2 — Present Summary

Display the scan results as a table:

| Branch | Status | Last Commit | Safe to Delete? |
|--------|--------|-------------|-----------------|
| feat/x | merged | 3 days ago | ✅ yes |
| old-hack | stale, merged | 47 days ago | ✅ yes |
| wip-auth | active | 1 day ago | ⚠️ has open PR |
| temp | local-only, stale | 90 days ago | ✅ yes |

### Step 3 — Confirm Deletion

Show the list of branches marked "safe to delete." Ask the user to confirm which to delete. Never delete without explicit confirmation.

Rules for safe deletion:
- **NEVER** delete the current branch
- **NEVER** delete protected branches (main, master, develop, or whatever the default branch is)
- **NEVER** delete a branch with an open PR
- Always offer `--dry-run` first (show `git branch -d` commands without executing)

### Step 4 — Execute

For each confirmed branch:

```
git branch -d <name>   # safe delete (refuses if unmerged)
```

If `-d` fails because the branch isn't fully merged, warn the user and skip. Only use `-D` (force delete) if the user explicitly requests it for a specific branch.

### Step 5 — Remote Cleanup (Optional)

If local branches were deleted and their remote counterparts still exist:

```
git push origin --delete <name>
```

Ask before deleting remote branches. Offer `git remote prune origin` as a safe alternative.

### Step 6 — Verify

Run `git branch -a` to show the final state. Confirm what was removed.

## Pitfalls

- **Default branch detection:** Always auto-detect the default branch via `git symbolic-ref refs/remotes/origin/HEAD` or `gh repo view --json defaultBranchRef`. Never hardcode "main" or "master."
- **Worktree branches:** Branches checked out in other worktrees should not be deleted. Script handles this.
- **Detached HEAD:** If HEAD is detached, treat all branches as potentially protected — warn the user.
- **Partial merges:** A branch may be merged into `develop` but not `main`. Only mark as "merged" if merged into the current branch or default branch.
- **Squash merges:** `git branch --merged` may not detect squash-merged branches. The `gh pr list --merged` check helps catch these.
- **Permission errors:** User may not have push access to delete remote branches. Fall back gracefully.

## Verification

- `git branch -a` shows fewer branches than before
- Protected branches (current, default, with-open-PR) are untouched
- No unmerged work was lost
- `git reflog` still has history of deleted branches (safety net)
