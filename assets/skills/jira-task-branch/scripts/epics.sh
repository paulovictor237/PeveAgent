#!/usr/bin/env bash
set -euo pipefail
PROJECT="${1:-AB}"
acli jira workitem search \
  --jql "project = $PROJECT AND issuetype = Epic AND statusCategory != Done ORDER BY updated DESC" \
  --fields "summary,status" --limit 10 --json |
  jq -r '.[] | "\(.key)\t\(.fields.status.name)\t\(.fields.summary)"'
