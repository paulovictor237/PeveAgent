---
name: jira-task-branch
description: Cria task no Jira (board 1513, projeto AB), atribui ao usuário, move para desenvolvimento e cria/publica branch com o mesmo nome. Use quando pedirem "nova task", "cria task e branch", "abre task no jira", "começar task nova".
---

# Jira task + branch

Board 1513 "Engajamento e Retenção \ Ativação B2B" → projeto `AB`, tipo `Tarefa`.

## Passos

1. Listar épicos abertos:
   `~/.claude/skills/jira-task-branch/scripts/epics.sh`
   Saída: `KEY\tSTATUS\tSUMMARY`.

2. Um único `AskUserQuestion` com 3 perguntas (nunca perguntas separadas):
   - **Nome** (header `Nome`): 2 sugestões de título derivadas do contexto da conversa/branch atual; usuário digita o nome real via "Other".
   - **Épico** (header `Épico`): até 3 épicos da etapa 1 (prioridade status `Desenvolvimento`), label `AB-XX`, description = summary; opção `Sem épico`.
   - **Base** (header `Base`): `main (Recommended)` ou `Branch atual (<nome>)`.

3. Se houver alterações não commitadas e base = main, avisar que irão junto para a nova branch.

4. Executar:
   `~/.claude/skills/jira-task-branch/scripts/create.sh "<nome>" "<AB-XX ou vazio>" "<main|current>"`
   O script cria a task atribuída a `@me`, transiciona (`Em andamento`, fallback `Desenvolvimento`), cria branch `<KEY>-<slug-do-nome>` e faz `git push -u origin`.
   Saída: `TASK=`, `STATUS=`, `BRANCH=`, `URL=`.

5. Reportar key, link, status, branch e base. Se `STATUS=` ausente, avisar que a transição falhou.
