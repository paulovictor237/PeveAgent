#!/usr/bin/env bash
set -uo pipefail

REPOS=(
  "/Users/paulo.duarte/workspace/outros/Obsidian Vault"
  "$PEVE_REPO_ROOT"
)

failed=0
stamp="$(date '+%Y-%m-%d %H:%M')"

sync_repo() {
  local repo="$1"
  cd "$repo" || return 1
  if [[ -n "$(git status --porcelain)" ]]; then
    git add -A || return 1
    git commit -q -m "chore(autosync): $stamp" || return 1
  fi
  if ! git pull -q --rebase --autostash; then
    git rebase --abort 2>/dev/null
    echo "pull --rebase failed, rebase aborted"
    return 1
  fi
  if [[ -n "$(git log '@{u}..HEAD' --oneline 2>/dev/null)" ]]; then
    git push -q || return 1
    echo "push ok"
  else
    echo "nothing to push"
  fi
}

for repo in "${REPOS[@]}"; do
  echo "== $repo"
  sync_repo "$repo" || { echo "FAILED: $repo"; failed=1; }
done

exit "$failed"
