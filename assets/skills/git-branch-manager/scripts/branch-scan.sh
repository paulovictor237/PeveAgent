#!/usr/bin/env bash
set -eo pipefail

STALE_DAYS="${STALE_DAYS:-30}"

# Detect default branch
DEFAULT_BRANCH=""
if sym=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null); then
  DEFAULT_BRANCH="${sym#refs/remotes/origin/}"
elif head_line=$(git remote show origin 2>/dev/null | grep 'HEAD branch'); then
  DEFAULT_BRANCH="$(echo "$head_line" | sed 's/.*: //')"
fi

if [[ -z "$DEFAULT_BRANCH" ]]; then
  git show-ref --verify --quiet refs/heads/main 2>/dev/null && DEFAULT_BRANCH="main"
  [[ -z "$DEFAULT_BRANCH" ]] && git show-ref --verify --quiet refs/heads/master 2>/dev/null && DEFAULT_BRANCH="master"
  [[ -z "$DEFAULT_BRANCH" ]] && DEFAULT_BRANCH=""
fi

CURRENT="$(git branch --show-current 2>/dev/null || echo "")"
NOW="$(date +%s)"
STALE_THRESHOLD=$(( NOW - STALE_DAYS * 86400 ))

# Worktree branches
WT_BRANCHES="$(git worktree list --porcelain 2>/dev/null | grep '^branch ' | sed 's|branch refs/heads/||' || true)"

# Merged into HEAD
MERGED_LIST="$(git branch --merged HEAD 2>/dev/null | sed 's/^[* ]*//' | grep -v "^${CURRENT}$" || true)"

# Open PR branches
PR_BRANCHES=""
if command -v gh >/dev/null 2>&1 && git remote get-url origin >/dev/null 2>&1; then
  PR_BRANCHES="$(gh pr list --state open --json headRefName --jq '.[].headRefName' 2>/dev/null || true)"
fi

# Temp file for entries
TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT

git for-each-ref --format='%(refname:short) %(committerdate:unix)' refs/heads/ | sort -k2 -n | while IFS=' ' read -r name ts; do
  # Skip current
  [[ "$name" == "$CURRENT" ]] && continue
  # Skip default
  [[ "$name" == "$DEFAULT_BRANCH" ]] && continue
  # Skip worktree
  if [[ -n "$WT_BRANCHES" ]] && echo "$WT_BRANCHES" | grep -qx "$name" 2>/dev/null; then
    continue
  fi

  statuses=""
  safe="true"

  # Merged?
  if [[ -n "$MERGED_LIST" ]] && echo "$MERGED_LIST" | grep -qx "$name" 2>/dev/null; then
    statuses="merged"
  else
    safe="false"
  fi

  # Open PR?
  if [[ -n "$PR_BRANCHES" ]] && echo "$PR_BRANCHES" | grep -qx "$name" 2>/dev/null; then
    statuses="${statuses:+$statuses,}open-pr"
    safe="false"
  fi

  # No remote?
  if ! git show-ref --verify --quiet "refs/remotes/origin/$name" 2>/dev/null; then
    statuses="${statuses:+$statuses,}local-only"
  fi

  # Stale?
  if [[ "$ts" -lt "$STALE_THRESHOLD" ]]; then
    statuses="${statuses:+$statuses,}stale"
  fi

  # Active if nothing else
  [[ -z "$statuses" ]] && statuses="active"

  last_commit="$(date -r "$ts" '+%Y-%m-%d' 2>/dev/null || echo "$ts")"

  echo "${name}|${statuses}|${safe}|${last_commit}" >> "$TMPFILE"
done

# Count entries
TOTAL=0
[[ -s "$TMPFILE" ]] && TOTAL="$(wc -l < "$TMPFILE" | tr -d ' ')"

# Output JSON
echo "{"
echo "  \"current_branch\": \"${CURRENT}\","
echo "  \"default_branch\": \"${DEFAULT_BRANCH}\","
echo "  \"branches\": ["

IDX=0
while IFS='|' read -r name statuses safe last_commit; do
  IDX=$((IDX + 1))
  [[ $IDX -eq $TOTAL ]] && comma="" || comma=","

  status_json=""
  IFS=',' read -ra STATUS_PARTS <<< "$statuses"
  for s in "${STATUS_PARTS[@]}"; do
    status_json="${status_json:+$status_json,}\"$s\""
  done

  printf '    {"name":"%s","status":[%s],"safe":%s,"last_commit":"%s"}%s\n' \
    "$name" "$status_json" "$safe" "$last_commit" "$comma"
done < "$TMPFILE"

echo "  ]"
echo "}"
