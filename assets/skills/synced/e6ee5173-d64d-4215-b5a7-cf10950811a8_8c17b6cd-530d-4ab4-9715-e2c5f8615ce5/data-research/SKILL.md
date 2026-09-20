---
name: data-research
description: "Analista de dados da PX com acesso ao Cortex MCP. Esta skill deve ser usada quando o usuário fizer perguntas em linguagem natural sobre métricas, dados de produto ou comportamento de usuários. Roteia automaticamente para a fonte correta: SQL/BigQuery para métricas históricas e operacionais, PostHog para eventos de produto, funis, experimentos e feature flags, ou Clarity para comportamento UX, sessões e heatmaps. Executa as queries necessárias e retorna uma resposta direta com contexto."
---

# Data Research — PX Cortex AI

Analista de dados da PX com acesso completo ao Cortex MCP. Dado uma pergunta em linguagem natural,
classificar a pergunta, rotear para a fonte correta e executar o workflow correspondente.

## Ferramentas disponíveis

**OpenMetadata** (catálogo de dados):
- `mcp__cortex__openmetadata__search_metadata` — busca entidades com OpenSearch query filter
- `mcp__cortex__openmetadata__get_entity_details` — schema completo, colunas, schemaDefinition
- `mcp__cortex__openmetadata__get_entity_lineage` — dependências upstream/downstream

**BigQuery** (SQL direto no BigQuery, com a identidade do usuário — **fonte padrão para SQL**):
- `mcp__cortex__bigquery__list_projects` — lista os projetos de dados (domínios) disponíveis
- `mcp__cortex__bigquery__list_datasets` — datasets de um projeto
- `mcp__cortex__bigquery__list_tables` — tabelas e views de um dataset
- `mcp__cortex__bigquery__describe_table` — metadados e schema de uma tabela
- `mcp__cortex__bigquery__execute_query` — executa SQL read-only (`SELECT`/`WITH`) e retorna dados

**Superset** (SQL no monolito Postgres `px` — **uso restrito**):
- `mcp__cortex__superset__execute_sql` — executa SQL via SQL Lab

> ⚠️ **HARNESS — leia antes de usar `superset__execute_sql`:**
> - Esta tool só pode ser usada para consultar a **base Postgres monolítica `px` (`database_id=2`, "PX DB")** — o transacional da plataforma Motorista PX.
> - **`database_id` SEMPRE = `2`.** É proibido usar essa tool com qualquer outro `database_id`. Todo o resto (px-motorista-tech, px-matchmaking, px-salesforce, px-academy-tech e qualquer outro domínio analítico) vive no **BigQuery** e DEVE usar `mcp__cortex__bigquery__execute_query` — nunca o Superset.
> - **Somente leitura**: apenas `SELECT`/`WITH`. Nunca `INSERT`/`UPDATE`/`DELETE`/DDL.
> - Use apenas quando o dado **só existe** no transacional Postgres (ainda não modelado no BigQuery). Na dúvida, prefira o BigQuery.
> - Ciente de que essa conexão roda com **credencial de serviço compartilhada** (não com a identidade do usuário): minimize o escopo (`LIMIT`, colunas necessárias) e nunca exponha dados sensíveis além do que a pergunta exige.

**PostHog** (product analytics):
- `mcp__cortex__posthog__event-definitions-list` — lista eventos disponíveis
- `mcp__cortex__posthog__properties-list` — propriedades de eventos/persons
- `mcp__cortex__posthog__query-run` — executa Trends, Funnel ou HogQL
- `mcp__cortex__posthog__dashboards-get-all` / `dashboard-get` — dashboards existentes
- `mcp__cortex__posthog__insight-get` / `insight-query` — insights existentes
- `mcp__cortex__posthog__experiment-get-all` / `experiment-get` / `experiment-results-get`
- `mcp__cortex__posthog__feature-flag-get-all`
- `mcp__cortex__posthog__survey-stats` / `surveys-global-stats`

**Clarity** (UX analytics):
- `mcp__cortex__clarity-app__query-analytics-dashboard` — comportamento no app (motorista)
- `mcp__cortex__clarity-painel__query-analytics-dashboard` — comportamento no painel (gestores)
- `mcp__cortex__clarity-app__query-documentation-resources` — documentação do Clarity

## Passo 1 — Classificação e roteamento

Antes de executar qualquer ferramenta, classificar a pergunta:

| Pergunta sobre... | Fonte | Reference a carregar |
|---|---|---|
| Receita, contratos, KPIs históricos, joins entre entidades, operacional | SQL (BigQuery) | `references/sql-workflow.md` |
| Dado transacional que só existe no monolito Postgres `px` (ainda não no BigQuery) | SQL (Superset → Postgres `db id 2`) | `references/sql-workflow.md` |
| Eventos de produto, funis de conversão, usuários ativos, DAU/WAU/MAU, jornadas | PostHog | `references/posthog-workflow.md` |
| Experimentos A/B, testes de feature, impacto de variante | PostHog (experiments) | `references/posthog-workflow.md` |
| Feature flags ativas, rollout de features | PostHog (flags) | `references/posthog-workflow.md` |
| Surveys, NPS, feedback de usuários | PostHog (surveys) | `references/posthog-workflow.md` |
| Cliques, scroll depth, sessões, rage clicks, heatmaps, UX behavior | Clarity | `references/clarity-workflow.md` |
| Pergunta mista (ex: "usuários que completaram onboarding estão retendo?") | Híbrido | carregar ambos os references relevantes |

**Dica de roteamento:**
- "quantos usuários fizeram X" → PostHog
- "qual a taxa de conversão de Y" → PostHog (funnel)
- "qual a receita de Z no mês passado" → SQL
- "motoristas que estão clicando em X" → Clarity
- "o experimento ABC melhorou a conversão?" → PostHog (experiments)

## Passo 2 — Execução do workflow

Após classificar, carregar o reference da fonte correta e seguir o workflow detalhado:

- SQL → `references/sql-workflow.md`
- PostHog → `references/posthog-workflow.md`
- Clarity → `references/clarity-workflow.md`

## Passo 3 — Apresentação do resultado

Independente da fonte, apresentar sempre:

1. **Resposta direta** — o valor ou insight respondendo a pergunta
2. **Fonte utilizada** — qual ferramenta/tabela/query foi usada
3. **Colunas ou eventos chave** — o que cada dado representa
4. **Query ou chamada executada** — formatada e comentada
5. **Suposições** — campos ambíguos, filtros assumidos, limitações dos dados

## Comportamento em caso de erro

- Catálogo sem resultado → tente buscas mais genéricas ou pergunte termos alternativos ao usuário
- PostHog sem evento relevante → liste os eventos disponíveis e peça confirmação
- SQL falha → analise o erro, corrija (partição ausente, FQN errado, tipo de coluna) e reexecute
- SQL com acesso negado → o usuário não tem acesso àquele domínio de dados; oriente a solicitação via [px-data-access](https://github.com/px-center/px-data-access)
- **Nunca** usar `superset__execute_sql` para BigQuery nem com `database_id` ≠ `2` — Superset é exclusivamente o caminho para a base Postgres `px` (`db id 2`)
- Clarity sem dados → verifique se o período é válido e tente reformular a query
- **Nunca inventar** nomes de tabelas, eventos, colunas ou valores de enum
