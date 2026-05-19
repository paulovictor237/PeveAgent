#!/bin/bash
# pr-resolve.sh — Marca um thread de review como resolvido
# Uso: pr-resolve.sh <thread_node_id>

THREAD_ID="${1:-}"

if [ -z "$THREAD_ID" ] || [ "$THREAD_ID" = "null" ]; then
  echo "⚠️  thread_id inválido ou nulo — pulando resolução" >&2
  exit 0
fi

RESULT=$(gh api graphql \
  -f query='mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }' \
  -f threadId="$THREAD_ID" \
  --jq '.data.resolveReviewThread.thread.isResolved' 2>&1)

if [ "$RESULT" = "true" ]; then
  echo "✅ Thread resolvido"
else
  echo "⚠️  Falha ao resolver thread: $RESULT" >&2
fi
