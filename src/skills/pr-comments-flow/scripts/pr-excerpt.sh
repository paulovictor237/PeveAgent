#!/bin/bash
# pr-excerpt.sh — Extrai trecho de um arquivo ao redor de uma linha
# Uso: pr-excerpt.sh <file_path> <line_number> [context_lines=15]
# Retorna as linhas com numeração, ±context_lines ao redor de <line_number>

FILE="$1"
LINE="${2:-1}"
CONTEXT="${3:-15}"

if [ -z "$FILE" ]; then
  echo "Uso: pr-excerpt.sh <file_path> <line_number> [context_lines=15]" >&2
  exit 1
fi

# Tenta o caminho direto; se não achar, tenta a partir da raiz do repo git
if [ ! -f "$FILE" ]; then
  REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
  FILE="${REPO_ROOT}/${FILE}"
fi

if [ ! -f "$FILE" ]; then
  echo "Arquivo não encontrado: $1" >&2
  exit 1
fi

TOTAL=$(wc -l < "$FILE")
START=$((LINE - CONTEXT))
END=$((LINE + CONTEXT))
[ "$START" -lt 1 ] && START=1
[ "$END" -gt "$TOTAL" ] && END="$TOTAL"

echo "📄 ${1} (linhas ${START}-${END}, destaque: ${LINE})"
echo "───────────────────────────────────────"

# Extrai com numeração; marca a linha alvo com ▶
awk -v start="$START" -v end="$END" -v target="$LINE" '
  NR >= start && NR <= end {
    marker = (NR == target) ? "▶" : " "
    printf "%s %4d │ %s\n", marker, NR, $0
  }
' "$FILE"
