#!/bin/bash
# pr-update-progress.sh — Atualiza o progresso de um comentário
# Uso: pr-update-progress.sh <PR_NUMBER> <COMMENT_ID> <STATUS: applied|skipped>

PR_NUMBER="$1"
COMMENT_ID="$2"
STATUS="$3"
PROGRESS="/tmp/pr-${PR_NUMBER}-progress.json"

if [ ! -f "$PROGRESS" ]; then
  echo "⚠️  Arquivo de progresso não encontrado: $PROGRESS" >&2
  exit 1
fi

jq --arg id "$COMMENT_ID" --arg status "$STATUS" '
  .statuses[$id] = $status |
  if $status == "applied" then .applied += 1
  elif $status == "skipped" then .skipped += 1
  else . end
' "$PROGRESS" > "${PROGRESS}.tmp" && mv "${PROGRESS}.tmp" "$PROGRESS"

echo "✅ Comentário #${COMMENT_ID} → ${STATUS}"
