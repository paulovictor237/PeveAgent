#!/usr/bin/env bash
set -euo pipefail

# analyze.sh — for each uncovered file, report new/old + dominant author on base branch
#              and a heuristic cluster suggestion. Replaces per-file git fan-out.
#
# Usage:
#   scripts/analyze.sh [-b BASE] [-c CODEOWNERS] FILE...
#   scripts/analyze.sh [-b BASE] [-c CODEOWNERS] < files.txt   # one path per line
#
# Reads file list from args or stdin (paste straight from the CI "no CODEOWNERS entry" block).

BASE="main"
CODEOWNERS=".github/CODEOWNERS"

while getopts "b:c:" opt; do
  case "$opt" in
    b) BASE="$OPTARG" ;;
    c) CODEOWNERS="$OPTARG" ;;
    *) echo "usage: analyze.sh [-b BASE] [-c CODEOWNERS] FILE..." >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  while IFS= read -r line; do
    line="${line%%#*}"; line="$(printf '%s' "$line" | tr -d '[:space:]')"
    [ -z "$line" ] && continue
    files+=("$line")
  done
fi
[ ${#files[@]} -eq 0 ] && { echo "no files given" >&2; exit 2; }

cluster_for() {
  case "$1" in
    *Falcon*)                    echo "Falcon" ;;
    *ScoreStatus*|*DriverScore*) echo "DriverScore" ;;
    *Discount*)                  echo "Discounts" ;;
    *ProfileDetailsResource*|*AvailableDriverResource*|*WorkProfileDetail*) echo "shared?-profile-resource" ;;
    *)                           echo "UNGROUPED" ;;
  esac
}

printf '%-6s | %-26s | %-22s | %s\n' "STATE" "CLUSTER" "TOP AUTHOR (base)" "FILE"
printf '%s\n' "------------------------------------------------------------------------------------------"
for f in "${files[@]}"; do
  cl="$(cluster_for "$f")"
  if git cat-file -e "$BASE:$f" 2>/dev/null; then
    author="$(git log --no-merges "$BASE" --format='%an' -- "$f" | sort | uniq -c | sort -rn | head -1 | sed 's/^ *//')"
    state="OLD"
  else
    author="(new file)"
    state="NEW"
  fi
  printf '%-6s | %-26s | %-22s | %s\n' "$state" "$cl" "$author" "$f"
done

echo
echo "Heuristic clusters only. Confirm owner per cluster with the user (AskUserQuestion)."
echo "CODEOWNERS=$CODEOWNERS  BASE=$BASE"
