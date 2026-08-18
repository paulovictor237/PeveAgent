#!/bin/bash
# pr-next-comment.sh — Retorna o próximo comentário pendente como JSON
# Uso: pr-next-comment.sh [PR_NUMBER]
# Saída: JSON do comentário, ou "null" se não houver pendentes

PR_NUMBER="${1:-$(gh pr view --json number --jq '.number' 2>/dev/null)}"
PROGRESS="/tmp/pr-${PR_NUMBER}-progress.json"
COMMENTS="/tmp/pr-${PR_NUMBER}-comments.json"

if [ ! -f "$PROGRESS" ] || [ ! -f "$COMMENTS" ]; then
  echo "null"
  exit 0
fi

STATUSES=$(jq -c '.statuses' "$PROGRESS")

jq -c --argjson statuses "$STATUSES" '
  [.files[] | .path as $path | .comments[] | . + {file_path: $path}] |
  map(select(($statuses[(.id | tostring)] // "pending") == "pending")) |
  first // null
' "$COMMENTS"
