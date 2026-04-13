---
name: jira-cli
description: Consulta read-only de épicos e tasks no Jira do planejamento
---

# Jira Reader

Consulta dados do Jira Cloud via wrapper seguro (read-only).

## Ferramenta

```bash
~/.claude/tools/jira_read.py <action> <ISSUE-KEY>
```

**IMPORTANTE**: Sempre use o caminho absoluto `~/.claude/tools/jira_read.py`, não o caminho relativo.

## Comandos Disponíveis

| Comando | Descrição |
|---------|-----------|
| `epic <KEY>` | Detalhes de um épico |
| `epic-children <KEY>` | Lista tasks filhas de um épico |

## Exemplos

```bash
# Ver detalhes do épico PROJ-123
~/.claude/tools/jira_read.py epic PROJ-123

# Listar todas as tasks do épico
~/.claude/tools/jira_read.py epic-children PROJ-123
```

## Restrições

- Apenas leitura (sem criar, editar ou comentar)
- Apenas épicos e seus filhos
- Formato de key: `PROJETO-NUMERO` (ex: PROJ-123)
- Não usar `acli` diretamente
