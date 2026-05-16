---
name: jira-board-report
description: Gera um relatório detalhado das tarefas do board Kanban Academia (APX) filtradas por colunas específicas (IN PROGRESS, CODE REVIEW, TO TEST, TESTING & MERGE, Waiting to deploy) com contagem de dias em andamento e parado na coluna. Pode enviar o relatório para o Slack criando uma thread.
---

## Propósito
Use esta skill para gerar o relatório diário ou periódico do board AcademiaPX. Ela extrai tarefas das colunas de desenvolvimento e formata a saída com links, responsáveis (@mencionados) e tempo de permanência.

## Fluxo de Execução

1. **Execute o script Python** para gerar o relatório:
   ```bash
   # Por padrão, não mostra tarefas IN PROGRESS
   python3 scripts/fetch_jira_board.py

   # Para incluir tarefas IN PROGRESS
   python3 scripts/fetch_jira_board.py --in-progress
   ```

2. **Exiba o resultado** para o usuário

3. **Pergunte ao usuário** se deseja enviar o relatório para o Slack:
   - Use AskUserQuestion para perguntar: "Deseja enviar este relatório para o Slack?"
   - Opções: "Sim" ou "Não"

4. **Se o usuário escolher "Sim"**:

   a. **Pergunte o destino**:
      - "Para onde deseja enviar?"
      - Opções:
        - "Para mim mesmo" (usa o ID salvo do usuário)
        - "Para um canal específico"
        - "Para outro usuário"

   b. **Envie usando MCP do Slack**:
      - **IMPORTANTE**: Use SEMPRE as ferramentas MCP do Slack (prefixo `mcp__claude_ai_Slack__`)
      - **NÃO use** `gh` ou `acli` para operações do Slack
      - Use `ToolSearch` para carregar as ferramentas do Slack se necessário

   c. **Crie uma thread com cabeçalho**:
      - Use `mcp__claude_ai_Slack__slack_send_message` para criar a mensagem inicial
      - Formato do cabeçalho (com backticks): `` `[dev] Daily Report - AcademiaPX - YYYY-MM-DD` ``
      - Use a data atual no formato ISO (ex: 2026-02-15)
      - Exemplo: `` `[dev] Daily Report - AcademiaPX - 2026-02-15` ``

   d. **Poste o conteúdo do relatório na thread**:
      - Use `mcp__claude_ai_Slack__slack_send_message` com o parâmetro `thread_ts` da mensagem inicial
      - O conteúdo deve ser o output completo do script Python

## Formato de Saída
O relatório é gerado em formato Slack-friendly:

*Nome da Coluna*

*Nome da tarefa (Chave)*
• *Link:* https://motoristapx.atlassian.net/browse/CHAVE
• *Responsável:* @Nome
• *Dias em andamento:* *X dias* (Início: YYYY-MM-DD)
• *Dias parado na coluna atual:* *Z dias* (Desde: YYYY-MM-DD)

## Configuração do Usuário

### ID do Slack do Usuário (Paulo Victor)
**Slack User ID**: `U02FG3C0Y3H`

Este ID deve ser usado quando o usuário escolher "Para mim mesmo" como destino.

## Notas Técnicas
- A contagem de "Dias em andamento" utiliza a data de criação da issue como base inicial (proxy) na ausência do histórico completo.
- A contagem de "Dias parado na coluna atual" utiliza a data da última mudança de categoria de status.
- Membros da equipe são automaticamente mapeados para seus respectivos arrobas conforme solicitado.
- **MCP Slack**: Use sempre as ferramentas MCP do Slack com prefixo `mcp__claude_ai_Slack__`
- **Thread no Slack**: A mensagem inicial retorna um `thread_ts` que deve ser usado para postar respostas na thread
