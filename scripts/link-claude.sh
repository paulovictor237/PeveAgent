#!/usr/bin/env bash
# link-claude.sh
# Links PeveWave assets into ~/.claude for Claude Code

set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO — ajuste conforme necessário
# ---------------------------------------------------------------------------

# Diretório destino (onde os links serão criados)
TARGET_DIR="$HOME/.claude"

# Pasta de assets dentro do projeto
ASSETS_DIR="src"

# Subpastas de $ASSETS_DIR a serem linkadas em $TARGET_DIR
# Formato: "pasta_fonte:nome_no_destino"
SUBDIR_LINKS=(
  "agents:agents"
  "commands:commands"
  "skills:skills"
)

# Arquivos dentro de $ASSETS_DIR a serem linkados em $TARGET_DIR
# Formato: "arquivo_fonte:nome_no_destino"
FILE_LINKS=(
  "AGENT.md:CLAUDE.md"
  "RTK.md:RTK.md"
  "settings.json:settings.json"
)

# Links com destino fora de $TARGET_DIR
# Formato: "arquivo_fonte_em_ASSETS_DIR:caminho_destino_absoluto"
CUSTOM_LINKS=(
  "ccstatusline.json:$HOME/.config/ccstatusline/settings.json"
  "opencode.json:$HOME/.config/opencode/opencode.json"
  "AGENT.md:$HOME/.config/opencode/AGENTS.md"
)

# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="$TARGET_DIR"

# Links com caminhos absolutos arbitrários (source fora de $ASSETS_DIR)
# Formato: "caminho_fonte_absoluto:caminho_destino_absoluto"
RAW_LINKS=(
  "$PROJECT_DIR/src/zed.jsonc:$HOME/.config/zed/settings.json"
  "$PROJECT_DIR/src:$HOME/.agents"
)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[link]${NC} $1"; }
warn()    { echo -e "${YELLOW}[skip]${NC} $1"; }
error()   { echo -e "${RED}[error]${NC} $1"; }

# link_item <source> <target>
# Creates a symlink at <target> pointing to <source>.
# Skips if target is already the correct symlink.
# Backs up if target exists and is not a symlink.
link_item() {
  local src="$1"
  local target="$2"

  if [ ! -e "$src" ]; then
    error "Source not found: $src"
    return 1
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

  if [ -d "$target" ]; then
    info "Pulling dir:  $target -> $dst"
    rm -rf "$dst"
    cp -r "$target" "$dst"
  else
    info "Pulling file: $target -> $dst"
    cp "$target" "$dst"
  fi
}

do_link() {
  echo ""
  echo "PeveWave → Claude Code"
  echo "Project: $PROJECT_DIR"
  echo "Target:  $CLAUDE_DIR"
  echo ""

  for entry in "${SUBDIR_LINKS[@]}"; do
    src_name="${entry%%:*}"
    dst_name="${entry##*:}"
    link_item "$PROJECT_DIR/$ASSETS_DIR/$src_name" "$TARGET_DIR/$dst_name"
  done

  for entry in "${FILE_LINKS[@]}"; do
    src_name="${entry%%:*}"
    dst_name="${entry##*:}"
    link_item "$PROJECT_DIR/$ASSETS_DIR/$src_name" "$TARGET_DIR/$dst_name"
  done

  for entry in "${CUSTOM_LINKS[@]}"; do
    src_name="${entry%%:*}"
    dst_path="${entry##*:}"
    mkdir -p "$(dirname "$dst_path")"
    link_item "$PROJECT_DIR/$ASSETS_DIR/$src_name" "$dst_path"
  done

  for entry in "${RAW_LINKS[@]}"; do
    src_path="${entry%%:*}"
    dst_path="${entry##*:}"
    mkdir -p "$(dirname "$dst_path")"
    link_item "$src_path" "$dst_path"
  done

  echo ""
  echo "Done."
}

do_reverse() {
  echo ""
  echo "Claude Code → PeveWave (reverse pull)"
  echo "Source:  $CLAUDE_DIR"
  echo "Project: $PROJECT_DIR"
  echo ""

  for entry in "${SUBDIR_LINKS[@]}"; do
    src_name="${entry%%:*}"
    dst_name="${entry##*:}"
    pull_item "$TARGET_DIR/$dst_name" "$PROJECT_DIR/$ASSETS_DIR/$src_name"
  done

  for entry in "${FILE_LINKS[@]}"; do
    src_name="${entry%%:*}"
    dst_name="${entry##*:}"
    pull_item "$TARGET_DIR/$dst_name" "$PROJECT_DIR/$ASSETS_DIR/$src_name"
  done

  for entry in "${CUSTOM_LINKS[@]}"; do
    src_name="${entry%%:*}"
    dst_path="${entry##*:}"
    pull_item "$dst_path" "$PROJECT_DIR/$ASSETS_DIR/$src_name"
  done

  for entry in "${RAW_LINKS[@]}"; do
    src_path="${entry%%:*}"
    dst_path="${entry##*:}"
    pull_item "$dst_path" "$src_path"
  done

  echo ""
  echo "Pull done. Running link..."
  do_link
}

case "${1:-}" in
  --reverse|-r) do_reverse ;;
  *)            do_link ;;
esac
