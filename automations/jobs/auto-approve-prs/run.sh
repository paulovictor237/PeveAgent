#!/usr/bin/env bash
set -uo pipefail

OWNER="${OWNER:-px-center}"
REPO_NAMES=(${REPOS:-px-mobile-painel px-mobile-motorista px-painel})
CUTOFF_DATE="${CUTOFF_DATE:-2026-09-28}"
CUTOFF_TIME_UTC="${CUTOFF_TIME_UTC:-03:00:00}"
MAX_PRS_PER_REPO="${MAX_PRS_PER_REPO:-100}"
MAX_REVIEWS_PER_PR="${MAX_REVIEWS_PER_PR:-50}"
PR_ORDER_FIELD="${PR_ORDER_FIELD:-CREATED_AT}"
PR_ORDER_DIRECTION="${PR_ORDER_DIRECTION:-DESC}"
VERBOSE="${VERBOSE:-false}"
SKIP_DRAFTS="${SKIP_DRAFTS:-true}"
SKIP_OWN_PRS="${SKIP_OWN_PRS:-true}"

CUTOFF_ISO="${CUTOFF_DATE}T${CUTOFF_TIME_UTC}Z"
DRY_RUN="${DRY_RUN:-false}"
$DRY_RUN && VERBOSE=true

retry() {
  local i
  for i in 1 2 3; do
    "$@" && return 0
    (( i < 3 )) && sleep 5
  done
  return 1
}

log() {
  printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"
}

command -v gh >/dev/null || { echo "gh not found"; exit 1; }
command -v jq >/dev/null || { echo "jq not found"; exit 1; }

ME="$(retry gh api user -q .login)" || { echo "failed to get gh user"; exit 1; }

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
  if $r == null then ["ERROR", "0", "repo", "-", "-", "repository not accessible"]
  else
    (if $r.pullRequests.pageInfo.hasNextPage then ["ERROR", "0", $r.nameWithOwner, "-", "-", "more open PRs than the limit, some were not checked"] else empty end),
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
    log "DRY  $label $repo#$number PR by $author: $title $url"
  elif out="$(retry gh pr review "$number" --repo "$repo" --approve 2>&1)"; then
    log "$label $repo#$number PR by $author: $title $url"
  else
    log "ERROR $repo#$number failed to approve $url: $out"
    return 1
  fi
}

run_cycle() {
  local json rows approved=0 skipped=0 errors=0
  json="$(retry gh api graphql -f query="$QUERY")" || { log "ERROR GraphQL query failed"; return 1; }
  rows="$(jq -r --arg me "$ME" --arg cutoff "$CUTOFF_ISO" --argjson skipOwn "$SKIP_OWN_PRS" --argjson skipDrafts "$SKIP_DRAFTS" "$JQ_FILTER" <<< "$json")" \
    || { log "ERROR failed to parse GraphQL response"; return 1; }

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
      ERROR)
        log "ERROR $repo $title"
        errors=$((errors + 1))
        ;;
      SKIP_*)
        skipped=$((skipped + 1))
        $VERBOSE && log "SKIP $repo#$number (${action#SKIP_}) $title"
        ;;
    esac
  done <<< "$rows"

  log "CYCLE approved=$approved skipped=$skipped errors=$errors"
  (( errors == 0 ))
}

log "START user=$ME org=$OWNER repos=${REPO_NAMES[*]} cutoff=$CUTOFF_DATE dry_run=$DRY_RUN"
run_cycle
