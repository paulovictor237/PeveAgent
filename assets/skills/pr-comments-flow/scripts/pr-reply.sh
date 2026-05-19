#!/bin/bash
COMMENT_ID="${1:-}"
BODY="${2:-}"

if [ -z "$COMMENT_ID" ] || [ -z "$BODY" ]; then
  echo "Uso: pr-reply.sh <comment_id> <body>" >&2
  exit 1
fi

REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null)
if [ -z "$REPO" ]; then
  echo "⚠️  Não foi possível detectar o repositório" >&2
  exit 1
fi

PR_NUMBER=$(gh pr view --json number --jq '.number' 2>/dev/null)
if [ -z "$PR_NUMBER" ]; then
  echo "⚠️  Não foi possível detectar o PR" >&2
  exit 1
fi

RESULT=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
  -X POST \
  -f body="$BODY" \
  -F in_reply_to="$COMMENT_ID" \
  --jq '.id' 2>&1)

if [[ "$RESULT" =~ ^[0-9]+$ ]]; then
  echo "✅ Resposta postada (comment #${RESULT})"
else
  echo "⚠️  Falha ao responder: $RESULT" >&2
  exit 1
fi
