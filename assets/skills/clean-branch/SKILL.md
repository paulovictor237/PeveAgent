---
name: clean-branch
description: Apaga branches locais já mergeadas na origin/main (ou origin/master) em um repositório ou em todos os repositórios filhos do diretório atual. Usar quando o usuário pedir para limpar/deletar branches mergeadas.
---

# clean-branch

Script: `~/.claude/skills/clean-branch/clean-branch.sh`

- Dentro de um repo git: atua nele. Fora: atua em cada subdiretório com `.git`.
- Faz `fetch --prune`, lista `branch --merged origin/main`.
- Nunca toca em `main|master|develop|staging`, na branch atual nem em branches de outros worktrees (só reporta).
- Apenas local. Não apaga remotas, salvo pedido explícito.

## Fluxo

1. `~/.claude/skills/clean-branch/clean-branch.sh` (dry-run, lista o que apagaria).
2. Se algo suspeito (ex.: branch com PR aberta), conferir com `gh pr view <branch>`.
3. Pedido explícito do usuário para apagar: `~/.claude/skills/clean-branch/clean-branch.sh --apply`.
4. Reportar por projeto: quantidade apagada, branches puladas e o motivo. Lembrar que o SHA no output permite restaurar (`git branch <nome> <sha>`).
