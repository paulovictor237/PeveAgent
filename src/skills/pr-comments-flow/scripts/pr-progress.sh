#!/bin/bash
# pr-progress.sh — Exibe o estado atual da revisão de um PR
# Uso: pr-progress.sh [PR_NUMBER]

PR_NUMBER="${1:-$(gh pr view --json number --jq '.number' 2>/dev/null)}"
PROGRESS="/tmp/pr-${PR_NUMBER}-progress.json"

if [ ! -f "$PROGRESS" ]; then
  echo "Nenhum progresso para PR #${PR_NUMBER}. Execute pr-fetch.sh primeiro."
  exit 1
fi

jq -r '"PR #\(.pr) — Progresso\n  Total:     \(.total)\n  Aplicados: \(.applied)\n  Pulados:   \(.skipped)\n  Resolvidos:\(.resolved)\n  Pendentes: \(.total - .applied - .skipped)"' "$PROGRESS"
