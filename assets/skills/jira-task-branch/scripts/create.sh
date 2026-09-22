#!/usr/bin/env bash
set -euo pipefail

SUMMARY="$1"
EPIC="${2:-}"
BASE="${3:-main}"
PROJECT="${PROJECT:-AB}"

create_args=(--project "$PROJECT" --type "Tarefa" --summary "$SUMMARY" --assignee "@me" --json)
[[ -n "$EPIC" ]] && create_args+=(--parent "$EPIC")

OUT=$(acli jira workitem create "${create_args[@]}")
KEY=$(jq -r '.key // empty' <<<"$OUT" 2>/dev/null || true)
[[ -z "$KEY" ]] && KEY=$(grep -oE "$PROJECT-[0-9]+" <<<"$OUT" | head -1 || true)
[[ -z "$KEY" ]] && { echo "ERRO: falha ao criar task: $OUT" >&2; exit 1; }
echo "TASK=$KEY"

for status in "Em andamento" "Desenvolvimento"; do
  if acli jira workitem transition --key "$KEY" --status "$status" --yes >/dev/null 2>&1; then
    echo "STATUS=$status"
    break
  fi
done

SLUG=$(python3 - "$SUMMARY" <<'PY'
import re, sys, unicodedata
s = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode()
s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
print(s[:80].rstrip("-"))
PY
)
BRANCH="$KEY${SLUG:+-$SLUG}"

if [[ "$BASE" == "current" ]]; then
  git checkout -b "$BRANCH"
else
  git fetch origin "$BASE"
  git checkout -b "$BRANCH" "origin/$BASE"
fi
git push -u origin "$BRANCH"

echo "BRANCH=$BRANCH"
echo "URL=https://motoristapx.atlassian.net/browse/$KEY"
