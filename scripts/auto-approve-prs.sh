#!/usr/bin/env bash
# auto-approve-prs.sh
#
# Aprova automaticamente PRs abertos nos repos configurados, via gh CLI.
#
# Uso:
#   bash scripts/auto-approve-prs.sh             loop contínuo
#   bash scripts/auto-approve-prs.sh --once      uma varredura e sai
#   bash scripts/auto-approve-prs.sh --dry-run   simula, sem aprovar
#
# Regras:
#   - Ignora PRs seus, drafts e PRs criados antes da data de corte
#   - Ignora PRs que você já aprovou no commit atual
#   - Reaprova se entrou commit novo depois da aprovação
#
# Configuração: variáveis logo abaixo, todas sobrescrevíveis por ambiente
#   INTERVAL é em minutos (padrão 30)
#   Ex: INTERVAL=5 VERBOSE=true bash scripts/auto-approve-prs.sh
#
# Log: scripts/auto-approve-prs.log (limpo a cada início)
#   APPR aprovado | REAPPR reaprovado | SKIP ignorado | DRY simulado | ERRO falha | CICLO resumo
#
# Atenção: aprova sem revisar o código (inclui dependabot, [HOTFIX] e [RELEASE]).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OWNER="${OWNER:-px-center}"
REPO_NAMES=(${REPOS:-px-mobile-painel px-mobile-motorista px-painel})
INTERVAL="${INTERVAL:-30}"
CUTOFF_DATE="${CUTOFF_DATE:-2026-09-28}"
CUTOFF_TIME_UTC="${CUTOFF_TIME_UTC:-03:00:00}"
MAX_PRS_PER_REPO="${MAX_PRS_PER_REPO:-100}"
MAX_REVIEWS_PER_PR="${MAX_REVIEWS_PER_PR:-50}"
PR_ORDER_FIELD="${PR_ORDER_FIELD:-CREATED_AT}"
PR_ORDER_DIRECTION="${PR_ORDER_DIRECTION:-DESC}"
LOG_FILE="${LOG_FILE:-$SCRIPT_DIR/auto-approve-prs.log}"
VERBOSE="${VERBOSE:-false}"
SKIP_DRAFTS="${SKIP_DRAFTS:-true}"
SKIP_OWN_PRS="${SKIP_OWN_PRS:-true}"

CUTOFF_ISO="${CUTOFF_DATE}T${CUTOFF_TIME_UTC}Z"
DRY_RUN=false
ONCE=false

for arg in "$@"; do
  case "$arg" in
    --once) ONCE=true ;;
    --dry-run) DRY_RUN=true; ONCE=true; VERBOSE=true ;;
    *) echo "uso: $0 [--once] [--dry-run]"; exit 1 ;;
  esac
done

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

command -v gh >/dev/null || { echo "gh não encontrado"; exit 1; }
command -v jq >/dev/null || { echo "jq não encontrado"; exit 1; }

ME="$(gh api user -q .login)" || { echo "falha ao obter usuário do gh"; exit 1; }

build_query() {
  local i=0 name fragments=""
  for name in "${REPO_NAMES[@]}"; do
    fragments+="r$i: repository(owner: \"$OWNER\", name: \"$name\") {
      nameWithOwner
      pullRequests(states: OPEN, first: $MAX_PRS_PER_REPO, orderBy: {field: $PR_ORDER_FIELD, direction: $PR_ORDER_DIRECTION}) {
        pageInfo { hasNextPage }
        nodes {
          number title url isDraft headRefOid createdAt
          author { login }
          latestReviews(first: $MAX_REVIEWS_PER_PR) { nodes { state author { login } commit { oid } } }
        }
      }
    } "
    i=$((i + 1))
  done
  echo "query { $fragments }"
}

QUERY="$(build_query)"

JQ_FILTER='
  .data | to_entries[] | .value as $r |
  if $r == null then ["ERRO", "0", "repo", "-", "-", "repositório inacessível"]
  else
    (if $r.pullRequests.pageInfo.hasNextPage then ["ERRO", "0", $r.nameWithOwner, "-", "-", "mais PRs abertos que o limite, alguns não foram verificados"] else empty end),
    ($r.pullRequests.nodes[] |
      (.author.login // "ghost") as $author |
      (.headRefOid) as $head |
      ([.latestReviews.nodes[] | select(.author.login == $me and .state == "APPROVED")] | first) as $mine |
      (if $skipOwn and $author == $me then "SKIP_MINE"
       elif $skipDrafts and .isDraft then "SKIP_DRAFT"
       elif .createdAt < $cutoff then "SKIP_OLD"
       elif $mine == null then "APPROVE"
       elif $mine.commit.oid == $head then "SKIP_APPROVED"
       else "REAPPROVE" end) as $action |
      [$action, (.number | tostring), $r.nameWithOwner, $author, .url, .title])
  end | @tsv
'

approve() {
  local action="$1" repo="$2" number="$3" author="$4" url="$5" title="$6" label
  [[ "$action" == "REAPPROVE" ]] && label="REAPPR" || label="APPR "
  if $DRY_RUN; then
    log "DRY  $label $repo#$number PR de $author: $title $url"
  elif gh pr review "$number" --repo "$repo" --approve >/dev/null 2>&1; then
    log "$label $repo#$number PR de $author: $title $url"
  else
    log "ERRO $repo#$number falha ao aprovar $url"
    return 1
  fi
}

run_cycle() {
  local rows approved=0 skipped=0 errors=0
  rows="$(gh api graphql -f query="$QUERY" | jq -r --arg me "$ME" --arg cutoff "$CUTOFF_ISO" --argjson skipOwn "$SKIP_OWN_PRS" --argjson skipDrafts "$SKIP_DRAFTS" "$JQ_FILTER")" \
    || { log "ERRO falha na consulta GraphQL"; return; }

  while IFS=$'\t' read -r action number repo author url title; do
    [[ -z "$action" ]] && continue
    case "$action" in
      APPROVE|REAPPROVE)
        if approve "$action" "$repo" "$number" "$author" "$url" "$title"; then
          approved=$((approved + 1))
        else
          errors=$((errors + 1))
        fi
        ;;
      ERRO)
        log "ERRO $repo $title"
        errors=$((errors + 1))
        ;;
      SKIP_*)
        skipped=$((skipped + 1))
        $VERBOSE && log "SKIP $repo#$number (${action#SKIP_}) $title"
        ;;
    esac
  done <<< "$rows"

  log "CICLO aprovados=$approved ignorados=$skipped erros=$errors"
}

: > "$LOG_FILE"

log "INÍCIO usuário=$ME org=$OWNER repos=${REPO_NAMES[*]} intervalo=${INTERVAL}min corte=$CUTOFF_DATE dry_run=$DRY_RUN"

while true; do
  run_cycle
  $ONCE && break
  sleep $((INTERVAL * 60))
done
