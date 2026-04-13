# PeveWave

Configuração pessoal do ambiente Claude Code.

🌐 **[Agent Overview](https://paulovictor237.github.io/PeveAgent/)** — catálogo dinâmico de skills, agents e commands.

## Setup

```bash
bash scripts/link-claude.sh
```

Cria symlinks de `wave/`, `AGENT.md`, `RTK.md` e `settings.json` para `~/.claude/`.

---

### ccstatusline

Status line para o Claude Code.

- Repo: https://github.com/sirmalloc/ccstatusline

```bash
npx -y ccstatusline@latest
```

---

## Ferramentas

### RTK

Token-optimized CLI proxy para Claude Code (60–90% de economia).

- Docs: https://www.rtk-ai.app/#install

```bash
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
```

> Não execute `rtk init --global` se o `link-claude.sh` já tiver instalado o `RTK.md`.

---

### Peon Ping

Notificações sonoras com vozes de personagens para o Claude Code.

- Site: https://www.peonping.com/

```bash
brew install peonping/tap/peon-ping
peon-ping-setup
```

---

### CodeGraph

Grafo semântico de código para navegação inteligente.

- Repo: https://github.com/colbymchenry/codegraph

```bash
npx @colbymchenry/codegraph
```

---
