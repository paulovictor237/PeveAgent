#!/usr/bin/env bash
set -u

apply=0
[ "${1:-}" = "--apply" ] && apply=1

if git rev-parse --git-dir >/dev/null 2>&1; then
  repos=("$PWD")
else
  repos=()
  for d in */; do
    [ -e "${d}.git" ] && repos+=("$PWD/${d%/}")
  done
fi

[ ${#repos[@]} -eq 0 ] && { echo "nenhum repositório git encontrado"; exit 1; }

for repo in "${repos[@]}"; do
  echo "=== $(basename "$repo")"
  git -C "$repo" fetch --prune origin >/dev/null 2>&1

  base=origin/main
  git -C "$repo" rev-parse --verify -q "$base" >/dev/null || base=origin/master
  git -C "$repo" rev-parse --verify -q "$base" >/dev/null || { echo "sem origin/main nem origin/master"; continue; }

  current=$(git -C "$repo" branch --show-current)
  worktrees=$(git -C "$repo" worktree list --porcelain | sed -n 's|^branch refs/heads/||p')

  git -C "$repo" branch --merged "$base" --format='%(refname:short)' \
    | grep -vE '^(main|master|develop|staging)$' \
    | while read -r b; do
        if [ "$b" = "$current" ]; then
          echo "pulada (branch atual): $b"
        elif grep -qxF "$b" <<<"$worktrees"; then
          echo "pulada (em outro worktree): $b"
        elif [ $apply -eq 1 ]; then
          git -C "$repo" branch -D "$b" | sed 's/^Deleted branch/apagada:/'
        else
          echo "apagaria: $b"
        fi
      done
done
