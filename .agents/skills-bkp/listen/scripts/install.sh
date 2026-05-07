#!/usr/bin/env bash
# install.sh — Instala as dependências da skill /listen

set -e

echo "==> Verificando dependências da skill /listen..."

# ── edge-tts ──────────────────────────────────────────────────────────────────
# Pacote Python que usa a API neural do Microsoft Edge para TTS.
# Requer Python 3.8+ e pip.
if ! command -v edge-tts &>/dev/null; then
  echo "Instalando edge-tts..."
  pip install edge-tts
else
  echo "✓ edge-tts já instalado ($(edge-tts --version 2>/dev/null || echo 'versão desconhecida'))"
fi

# ── afplay ────────────────────────────────────────────────────────────────────
# Utilitário nativo do macOS para reprodução de áudio.
# Não precisa de instalação — já vem no sistema.
if ! command -v afplay &>/dev/null; then
  echo "✗ afplay não encontrado. Este script requer macOS."
  echo "  Em Linux, instale mpg123 ou ffplay como alternativa e ajuste o SKILL.md."
  exit 1
else
  echo "✓ afplay disponível (macOS detectado)"
fi

echo ""
echo "Todas as dependências estão prontas. A skill /listen pode ser usada."
