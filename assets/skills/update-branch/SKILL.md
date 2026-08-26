---
name: update-branch
description: "Updates the current branch with the base branch (merge), resolves conflicts, validates, and pushes"
user-invocable: true
argument-hint: "[base-branch] (default: main)"
---

# Update branch with base branch, resolve conflicts, validate, push

## Usage

```
/update-branch           # uses main as base
/update-branch develop   # uses another branch as base
```

The base branch is `$ARGUMENTS` when given, otherwise `main`.

## 1. Fetch and preview

`git fetch origin <base>`, then `git log --oneline HEAD..origin/<base>` to show what's coming in.

Check whether the base already contains work equivalent to the current branch's (e.g. a sibling card already merged into `main`) — this is the strongest predictor of conflict, worth flagging before merging.

## 2. Merge

`git merge origin/<base>`.

## 3. Resolve conflicts

Each side usually represents a different intent, not competing versions of the same line. Default to **combining both intents**, not picking a side.

Before resolving, understand what each side was doing:

- `git log --oneline HEAD..origin/<base> -- <file>` — what the base changed there
- `git log --oneline origin/<base>..HEAD -- <file>` — what the current branch changed there
- Read the actual signatures (prop types, helper params) before writing the resolution — don't guess from the conflict markers

After resolving, verify nothing essential was lost: both features must still be present in the final file.

Never leave a conflict marker behind:

```bash
grep -rln '^<<<<<<< \|^>>>>>>> \|^======= ' src || echo none
```

If the two intents are genuinely incompatible, stop and ask the user instead of picking a side in the dark.

## 4. Check for hidden semantic conflicts

Git resolves by line, not by meaning. A file can come back `Auto-merging` — no conflict marker — and still be broken, because the merge kept one side's line even though it's incompatible with the other side's usage.

Real case from this repo: the base made a type private (`type X` instead of `export type X`) because nothing outside its module used it; the current branch still imported that type. The merge accepted the base's line without flagging a conflict, and the break only surfaced in `type:check`.

- Check every file marked `Auto-merging` that touches the same area as the feature, not just the ones with conflict markers.
- When fixing one, confirm which side was right first: `git show HEAD:<file>` vs `git show origin/<base>:<file>`. Restore the intent the current branch needs — don't invent a third version.

## 5. Validate

Run the project's validation script and check the exit code — the output is long and parallel, so reading only the tail is misleading:

```bash
npm run validate >/dev/null 2>&1; echo "validate exit: $status"
```

On error, filter instead of dumping the full output:

```bash
npm run validate 2>&1 | grep -E 'error TS|✖|Tests:|Test Suites:|ERROR' | head -20
```

This step is the detector for step 4's hidden conflicts, not a formality — run it before committing the merge, not after. Pre-existing lint warnings (not introduced by the merge) don't block; errors and broken tests do. Report a failing test with its output, verbatim.

## 6. Commit the merge

`git commit --no-edit` — keep the default merge message, don't write a custom one.

## 7. Push

**Non-fast-forward rejection** means the remote branch has commits that don't exist locally — someone pushed there. Investigate before anything else:

```bash
git fetch origin <current-branch>
git rev-list --count HEAD..origin/<current-branch>   # commits only on remote
git rev-list --count origin/<current-branch>..HEAD   # commits only local
git merge-base --is-ancestor origin/<current-branch> HEAD; echo "ancestor: $status"
git --no-pager log --oneline --no-decorate HEAD..origin/<current-branch> | cat
```

Count with `rev-list --count` and confirm with `merge-base --is-ancestor` — piping `git log` through a filter has come back misleadingly empty in this session (two commits actually existed) when the count said otherwise; don't trust an empty list unless the count agrees.

Commits found only on remote → merge them (`git merge origin/<current-branch>`), resolve (step 3), re-validate (step 5), then push again.

**Transient GitHub error** — `remote: fatal error in commit_refs` and similar `remote rejected ... (failure)` messages are server-side, not a ref problem. Retry the push once, unchanged. Still failing after the second attempt → report to the user instead of retrying again.

## 8. Confirm and report

Confirm local and remote point at the same SHA. Report: which conflicts existed and how each was resolved, which semantic conflicts (step 4) surfaced only during validation, the validation result, and the final SHA on both local and remote.

## Guardrails

- **Never `git push --force` or `--force-with-lease`** on your own — force discards whatever is on the remote. If it ever seems necessary, stop, explain what would be discarded (with the commit list), and get an explicit decision from the user.
- **Never `git rebase`** to update the branch here — this flow is merge-only; the branch is shared and likely has an open PR.
- No interactive flags (`-i`) — unsupported in this environment.
- Commit messages in English; never add "Generated with Claude Code" or "Co-Authored-By: Claude".
