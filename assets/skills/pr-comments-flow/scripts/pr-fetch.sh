#!/bin/bash
# pr-fetch.sh — Busca, deduplica e pré-processa comentários de um PR
# Uso: pr-fetch.sh <PR_NUMBER>
# Saída: /tmp/pr-{N}-comments.json + /tmp/pr-{N}-progress.json

set -euo pipefail

PR_NUMBER="${1:-$(gh pr view --json number --jq '.number' 2>/dev/null)}"
if [ -z "$PR_NUMBER" ]; then
  echo "Error: could not detect PR number. Pass it as argument." >&2
  exit 1
fi

REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
if [[ "$REMOTE_URL" =~ github\.com ]]; then
  REPO_PATH="${REMOTE_URL#*github.com[:/]}"
  REPO_PATH="${REPO_PATH%.git}"
  OWNER="${REPO_PATH%/*}"
  REPO_NAME="${REPO_PATH#*/}"
  REPO="${OWNER}/${REPO_NAME}"
else
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || echo "")
  OWNER=$(echo "$REPO" | cut -d'/' -f1)
  REPO_NAME=$(echo "$REPO" | cut -d'/' -f2)
fi

OUTPUT="/tmp/pr-${PR_NUMBER}-comments.json"
PROGRESS="/tmp/pr-${PR_NUMBER}-progress.json"
TMP_RAW="/tmp/pr-raw-${PR_NUMBER}.json"

echo "📥 Fetching comments for PR #${PR_NUMBER} (${REPO})..."

gh api graphql \
  -f query='query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            path
            line
            originalLine
            comments(first: 1) {
              nodes {
                databaseId
                body
                author {
                  login
                }
                createdAt
                diffHunk
              }
            }
          }
        }
      }
    }
  }' \
  -f owner="$OWNER" \
  -f repo="$REPO_NAME" \
  -F pr="$PR_NUMBER" > "$TMP_RAW"

jq --arg pr "$PR_NUMBER" --arg repo "$REPO" '
  (.data.repository.pullRequest.reviewThreads.nodes // []) |
  map(select(.comments.nodes[0] != null)) |
  map({
    id: .comments.nodes[0].databaseId,
    path: .path,
    line: (.line // .originalLine),
    body: .comments.nodes[0].body,
    user: (.comments.nodes[0].author.login // "ghost"),
    created_at: .comments.nodes[0].createdAt,
    thread_id: .id,
    is_resolved: .isResolved,
    diff_hunk: (.comments.nodes[0].diffHunk | split("\n") | .[-6:] | join("\n"))
  }) |
  map(select(.is_resolved == false)) |
  group_by(.path + "|||" + .body) |
  map({
    id: .[0].id,
    path: .[0].path,
    line: .[0].line,
    body: .[0].body,
    user: .[0].user,
    created_at: .[0].created_at,
    thread_id: .[0].thread_id,
    diff_hunk: .[0].diff_hunk,
    duplicate_count: (length - 1)
  }) |
  group_by(.path) |
  map({
    path: .[0].path,
    comments: .
  }) |
  {
    pr: ($pr | tonumber),
    repo: $repo,
    total: (map(.comments | length) | add // 0),
    files_count: length,
    files: .
  }
' "$TMP_RAW" > "$OUTPUT"

TOTAL=$(jq '.total' "$OUTPUT")
echo "{\"pr\": $PR_NUMBER, \"applied\": 0, \"skipped\": 0, \"ignored\": 0, \"resolved\": 0, \"total\": $TOTAL, \"statuses\": {}}" > "$PROGRESS"
echo "   → Progress initialized"

rm -f "$TMP_RAW"

TOTAL=$(jq '.total' "$OUTPUT")
FILES=$(jq '.files_count' "$OUTPUT")
echo ""
echo "✅ Done! ${TOTAL} comment(s) in ${FILES} file(s)"
echo "   Data: $OUTPUT"
echo "   Progress: $PROGRESS"
