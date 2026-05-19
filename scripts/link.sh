#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[link]${NC} $1"; }
warn()  { echo -e "${YELLOW}[skip]${NC} $1"; }
error() { echo -e "${RED}[error]${NC} $1"; }
dry()   { echo -e "${CYAN}[dry]${NC} $1"; }

DRY_RUN=false
REVERSE=false
TOOLS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --reverse) REVERSE=true ;;
    *) TOOLS+=("$arg") ;;
  esac
done

expand_path() {
  local p="$1"
  p="${p/#\~/$HOME}"
  p="${p/\$HOME/$HOME}"
  echo "$p"
}

link_item() {
  local src="$1"
  local target="$2"

  if [ ! -e "$src" ]; then
    error "Source not found: $src"
    return 1
  fi

  if $DRY_RUN; then
    if [ -L "$target" ] && [ "$(readlink "$target")" = "$src" ]; then
      dry "Already linked: $target -> $src"
    else
      dry "Would link: $target -> $src"
    fi
    return 0
  fi

  if [ -L "$target" ]; then
    local existing_src
    existing_src="$(readlink "$target")"
    if [ "$existing_src" = "$src" ]; then
      warn "Already linked: $target -> $src"
      return 0
    else
      warn "Replacing existing symlink: $target (was -> $existing_src)"
      rm "$target"
    fi
  elif [ -e "$target" ]; then
    local backup="${target}.bkp"
    warn "Backing up existing: $target -> $backup"
    mv "$target" "$backup"
  fi

  ln -s "$src" "$target"
  info "$target -> $src"
}

pull_item() {
  local target="$1"
  local dst="$2"

  if [ ! -e "$target" ]; then
    warn "Not found in target, skipping pull: $target"
    return 0
  fi

  if [ -L "$target" ]; then
    warn "Already a symlink, skipping pull: $target"
    return 0
  fi

  if $DRY_RUN; then
    dry "Would pull: $target -> $dst"
    return 0
  fi

  if [ -d "$target" ]; then
    info "Pulling dir:  $target -> $dst"
    rm -rf "$dst"
    cp -r "$target" "$dst"
  else
    info "Pulling file: $target -> $dst"
    cp "$target" "$dst"
  fi
}

process_manifest() {
  local manifest="$1"
  local tool
  tool="$(jq -r '.tool' "$manifest")"
  local target_root_raw
  target_root_raw="$(jq -r '.target_root' "$manifest")"
  local target_root
  target_root="$(expand_path "$target_root_raw")"

  if [[ "$target_root" != /* ]]; then
    target_root="$PROJECT_DIR/$target_root"
  fi

  echo ""
  echo "── $tool ──────────────────────────────"
  echo "   target: $target_root"
  echo ""

  mkdir -p "$target_root"

  local link_count
  link_count="$(jq '.links | length' "$manifest")"
  for i in $(seq 0 $((link_count - 1))); do
    [ "$link_count" -eq 0 ] && break
    local from to
    from="$(jq -r ".links[$i].from" "$manifest")"
    to="$(jq -r ".links[$i].to" "$manifest")"
    local src="$PROJECT_DIR/$from"
    local dst="$target_root/$to"

    if $REVERSE; then
      pull_item "$dst" "$src"
    else
      link_item "$src" "$dst"
    fi
  done

  local ext_count
  ext_count="$(jq '.external_links | length' "$manifest")"
  for i in $(seq 0 $((ext_count - 1))); do
    [ "$ext_count" -eq 0 ] && break
    local from to_raw to
    from="$(jq -r ".external_links[$i].from" "$manifest")"
    to_raw="$(jq -r ".external_links[$i].to" "$manifest")"
    to="$(expand_path "$to_raw")"
    local src="$PROJECT_DIR/$from"

    mkdir -p "$(dirname "$to")"

    if $REVERSE; then
      pull_item "$to" "$src"
    else
      link_item "$src" "$to"
    fi
  done
}

collect_manifests() {
  if [ ${#TOOLS[@]} -eq 0 ]; then
    for f in "$PROJECT_DIR/tools/"*.json; do
      echo "$f"
    done
  else
    for t in "${TOOLS[@]}"; do
      local mf="$PROJECT_DIR/tools/$t.json"
      if [ ! -f "$mf" ]; then
        error "No manifest found for tool: $t (looked for $mf)"
        exit 1
      fi
      echo "$mf"
    done
  fi
}

echo ""
if $DRY_RUN; then
  echo "PeveAgent link.sh [dry-run]"
elif $REVERSE; then
  echo "PeveAgent link.sh [reverse]"
else
  echo "PeveAgent link.sh"
fi
echo "Project: $PROJECT_DIR"

while IFS= read -r manifest; do
  process_manifest "$manifest"
done < <(collect_manifests)

echo ""
if $REVERSE; then
  echo "Pull done. Re-linking..."
  REVERSE=false
  while IFS= read -r manifest; do
    process_manifest "$manifest"
  done < <(collect_manifests)
fi

echo ""
echo "Done."
