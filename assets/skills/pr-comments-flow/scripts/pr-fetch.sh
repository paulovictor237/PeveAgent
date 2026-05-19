#!/bin/bash
# pr-fetch.sh — Busca, deduplica e pré-processa comentários de um PR
# Uso: pr-fetch.sh <PR_NUMBER>
# Saída: /tmp/pr-{N}-comments.json + /tmp/pr-{N}-progress.json

set -euo pipefail

PR_NUMBER="${1:-$(gh pr view --json number --jq '.number' 2>/dev/null)}"
if [ -z "$PR_NUMBER" ]; then
  echo "Erro: não foi possível detectar o número do PR. Passe como argumento." >&2
  exit 1
fi

REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
OWNER=$(echo "$REPO" | cut -d'/' -f1)
REPO_NAME=$(echo "$REPO" | cut -d'/' -f2)
OUTPUT="/tmp/pr-${PR_NUMBER}-comments.json"
PROGRESS="/tmp/pr-${PR_NUMBER}-progress.json"
TMP_RAW="/tmp/pr-raw-${PR_NUMBER}.json"
TMP_THREADS="/tmp/pr-threads-${PR_NUMBER}.json"

echo "📥 Buscando comentários do PR #${PR_NUMBER} (${REPO})..."

# 1. Busca comentários: apenas campos necessários + diff_hunk truncado (últimas 6 linhas)
gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
  --paginate \
  --jq '[.[] | select(.in_reply_to_id == null) | {
    id: .id,
    path: .path,
    line: (.line // .original_line),
    body: .body,
    node_id: .node_id,
    diff_hunk: (.diff_hunk | split("\n") | .[-6:] | join("\n"))
  }]' | jq -s 'add // []' > "$TMP_RAW"

RAW_COUNT=$(jq 'length' "$TMP_RAW")
echo "   → ${RAW_COUNT} comentários raiz encontrados"

# 2. Busca thread node IDs via GraphQL (para resolver depois)
echo "🔗 Buscando thread IDs..."
gh api graphql \
  -f query='query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            comments(first: 1) {
              nodes { databaseId }
            }
          }
        }
      }
    }
  }' \
  -f owner="$OWNER" \
  -f repo="$REPO_NAME" \
  -F pr="$PR_NUMBER" \
  --jq '(.data.repository.pullRequest.reviewThreads.nodes |
    map({
      ((.comments.nodes[0].databaseId // 0) | tostring):
        {thread_id: .id, is_resolved: .isResolved}
    }) | add) // {}' > "$TMP_THREADS"

# 3. Merge, filtra resolvidos, deduplica por (path + body) e agrupa por arquivo
echo "⚙️  Processando e deduplicando..."
jq -s --arg pr "$PR_NUMBER" --arg repo "$REPO" '
  .[0] as $comments |
  (.[1] // {}) as $threads |

  # Adiciona info de thread a cada comentário
  ($comments | map(. + ($threads[(.id | tostring)] // {thread_id: null, is_resolved: false}))) |

  # Remove já resolvidos
  map(select(.is_resolved == false)) |

  # Deduplica: mesmo path + mesmo body → mantém primeiro, conta duplicatas
  group_by(.path + "|||" + .body) |
  map({
    id: .[0].id,
    path: .[0].path,
    line: .[0].line,
    body: .[0].body,
    node_id: .[0].node_id,
    thread_id: .[0].thread_id,
    diff_hunk: .[0].diff_hunk,
    duplicate_count: (length - 1)
  }) |

  # Agrupa por arquivo
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
' "$TMP_RAW" "$TMP_THREADS" > "$OUTPUT"

# 4. Inicializa arquivo de progresso (se não existir)
if [ ! -f "$PROGRESS" ]; then
  TOTAL=$(jq '.total' "$OUTPUT")
  echo "{\"pr\": $PR_NUMBER, \"applied\": 0, \"skipped\": 0, \"resolved\": 0, \"total\": $TOTAL, \"statuses\": {}}" > "$PROGRESS"
  echo "   → Progresso inicializado"
fi

# Limpeza
rm -f "$TMP_RAW" "$TMP_THREADS"

TOTAL=$(jq '.total' "$OUTPUT")
FILES=$(jq '.files_count' "$OUTPUT")
echo ""
echo "✅ Pronto! ${TOTAL} comentários em ${FILES} arquivo(s)"
echo "   Dados: $OUTPUT"
echo "   Progresso: $PROGRESS"
