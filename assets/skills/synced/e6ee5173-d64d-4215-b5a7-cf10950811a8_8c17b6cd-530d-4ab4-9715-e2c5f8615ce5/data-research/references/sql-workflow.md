# SQL Workflow — OpenMetadata + BigQuery (+ Postgres `px`)

Usar quando a pergunta envolve métricas históricas, operacionais, KPIs de negócio ou qualquer
dado estruturado no BigQuery.

As queries rodam pelo MCP de BigQuery do Cortex **com a identidade do usuário**: cada pessoa só
enxerga e consulta o que o próprio acesso permite. Acesso negado a um domínio → solicitar via
[px-data-access](https://github.com/px-center/px-data-access).

## Qual fonte de SQL usar

| Caso | Fonte | Tool |
|---|---|---|
| **Padrão** — qualquer dado modelado no BigQuery (analítico, gold/silver, KPIs, domínios) | BigQuery | `mcp__cortex__bigquery__execute_query` |
| **Exceção** — dado transacional que só existe no monolito Postgres `px` (ainda não no BigQuery) | Postgres `px` | `mcp__cortex__superset__execute_sql` com `database_id=2` |

> ⚠️ **O Superset é exclusivamente o caminho para a base Postgres `px` (`database_id=2`, "PX DB").**
> Nunca use `superset__execute_sql` para BigQuery, nem com qualquer `database_id` diferente de `2`.
> Na dúvida sobre onde o dado vive, comece pelo catálogo/BigQuery e só caia para o Postgres se
> confirmar que a tabela não está modelada no BigQuery.

## Projetos BigQuery (domínios de dados)

Cada domínio = um projeto GCP com o lake `backbone` (datasets `backbone_bronze` / `backbone_silver` /
`backbone_gold` / `backbone_secure` / `backbone_sandbox`). A **fonte de verdade** dos domínios é o
[px-data-access](https://github.com/px-center/px-data-access) (`domains/*.yaml`); para o catálogo vivo,
usar `mcp__cortex__bigquery__list_projects`. Domínios declarados:

| Projeto BigQuery | Domínio |
|---|---|
| px-torre | Torre — empresas (`bt_companies`), motoristas, contratos e Gestão de Sucesso (GS); núcleo operacional |
| px-matchmaking | Matchmaking de fretes/motoristas: contratos, eventos de matching, exames (toxicológico/Senatran) |
| px-execution | Execução — eventos de execução de operações (`events`, `operations`) |
| px-ear | EAR — engajamento e retenção de empresas e motoristas (churn, ativos, séries mensais) |
| px-salesforce | CRM (Salesforce): leads, oportunidades, pipeline comercial |
| px-commercial | Comercial — dados de vendas/negociação |
| px-customer-support | Atendimento/suporte ao cliente (domínio isolado) |
| px-acquisition | Aquisição — topo de funil, captação de leads/usuários |
| px-activation | Ativação — onboarding e ativação no funil de growth |
| px-marketing | Marketing / mídia paga: Google Ads, Meta, Instagram, YouTube, GA, ClickUp |
| px-financial | Financeiro |
| px-risk | Risco |
| px-telemetry | Telemetria de dispositivos/veículos |
| px-wearable | Wearables — dados de dispositivos vestíveis |
| px-executive | Executivo — KPIs e consolidação para diretoria (lê gold de vários domínios) |
| px-feature-store | Feature Store — features para modelos de ML |
| px-ml-platform | Plataforma de ML — dados/artefatos de modelos |
| px-data-science | Data Science — datasets e experimentos |
| px-data-platform | Data Platform — infraestrutura de dados, auditoria e monitoramento (`backbone_audit`) |
| px-event-store | Event Store — ingestão bruta de eventos (apenas `bronze`) |
| formal-purpose-354320 | Formal Purpose — export de billing/custos GCP (apenas `bronze`) |

## Workflow

### Passo 1 — Decomposição da pergunta

Extrair:
- **Métricas** (ex: "dias agenciados", "receita", "conversão")
- **Filtros temporais** (ex: "mês passado", "janeiro", "últimos 7 dias")
- **Dimensões** (ex: "por empresa", "por região", "por tipo de carga")
- **Entidades de negócio** (ex: "motoristas", "fretes", "contratos")

### Passo 2 — Busca no catálogo (OpenMetadata)

Usar `mcp__cortex__openmetadata__search_metadata` com `queryFilter` OpenSearch.

**Estratégia A — Termos de negócio:**
- Primeiro em inglês (tabelas são geralmente em inglês): "days contracts kpi", "freight days"
- Depois em português se necessário: "dias agenciados", "meta contrato"
- Fazer de 2 a 4 buscas com variações

**Estratégia B — Filtros por serviço (obrigatório para reduzir ruído — catálogo tem 1200+ tabelas):**

```json
{
  "bool": {
    "must": [
      { "term": { "entityType": "table" } },
      { "term": { "databaseSchema.name.keyword": "backbone_gold" } },
      { "term": { "service.name": "px-torre" } }
    ]
  }
}
```

Ajustar `service.name` conforme o domínio (o `service.name` = o projeto BigQuery da tabela de
domínios acima):
- Empresas/GS/operacional → `px-torre`
- Matchmaking/contratos/fretes → `px-matchmaking`
- CRM/leads → `px-salesforce`
- Marketing/mídia paga → `px-marketing`
- Financeiro → `px-financial`

**Estratégia C — Priorizar views e tabelas KPI:**
Views (`tableType: View`) e tabelas prefixadas com `kpi_`, `vw_`, `bt_` contêm lógica de negócio
consolidada. Priorize-as — o campo `schemaDefinition` revela as tabelas-fonte e a lógica de cálculo.

### Passo 3 — Seleção de candidatas

Selecionar 2 a 3 tabelas mais relevantes com base em:
- Descrição compatível com a pergunta
- Nomes de colunas que sugerem as métricas buscadas
- Preferência: `backbone_gold` > `backbone_silver` > transacional

### Passo 4 — Detalhamento do schema

Usar `mcp__cortex__openmetadata__get_entity_details` com o FQN exato. Como alternativa (ou para
confirmar o schema real), usar `mcp__cortex__bigquery__describe_table`.

Analisar:
- Todas as colunas, tipos e descrições
- Colunas de partição (obrigatórias nos filtros de data)
- Se for view: ler `schemaDefinition` para descobrir tabelas-fonte e lógica de cálculo

**Usar lineage quando necessário:**
Usar `mcp__cortex__openmetadata__get_entity_lineage` para entender dependências quando:
- A view referencia tabelas desconhecidas
- Precisar rastrear a origem de uma métrica calculada
- Investigar o impacto de uma mudança upstream

### Passo 5 — Geração da SQL

**Regras obrigatórias:**
- FQN completo: `` `px-torre`.`backbone_gold`.`bt_companies` `` — **toda tabela deve ser
  totalmente qualificada** (`projeto.dataset.tabela`); queries com tabelas não qualificadas são rejeitadas
- **Somente leitura**: apenas `SELECT`/`WITH` — DML/DDL são rejeitados antes de executar
- **Sempre filtrar pela coluna de partição** — tabelas gold são particionadas por data; sem esse filtro fazem full scan
- Timezone: `DATE(coluna, 'America/Sao_Paulo')` em todas as funções de data
- Comentar a query explicando cada bloco

**Filtro de mês passado correto:**
```sql
DATE_TRUNC(DATE(coluna, 'America/Sao_Paulo'), MONTH) =
  DATE_TRUNC(DATE_SUB(DATE(CURRENT_TIMESTAMP(), 'America/Sao_Paulo'), INTERVAL 1 MONTH), MONTH)
```

**Ambiguidade:** Se houver campo ambíguo (ex: `type` sem valores documentados), gerar a query mais
provável, mencionar a suposição e sinalizar que pode precisar de ajuste.

### Passo 6 — Execução no BigQuery

Usar `mcp__cortex__bigquery__execute_query`:
- `sql`: a query gerada (com todas as tabelas totalmente qualificadas)

Não há `database_id` nem `schema` para configurar — o projeto de billing é derivado automaticamente
das tabelas referenciadas na query.

Se falhar, analisar o erro e ajustar:
- Partição ausente, sintaxe incorreta ou FQN errado → corrigir e reexecutar
- Query rejeitada por tabela não qualificada → usar o FQN completo `projeto.dataset.tabela`
- Limite de bytes excedido → reduzir o período do filtro ou as colunas selecionadas
- Acesso negado → o usuário não tem acesso àquela tabela/domínio; orientar solicitação via
  [px-data-access](https://github.com/px-center/px-data-access)

### Passo 6b — Execução no Postgres `px` (exceção)

Usar **somente** quando o dado vive exclusivamente no monolito transacional (não modelado no
BigQuery). Caso contrário, ficar no Passo 6 (BigQuery).

Usar `mcp__cortex__superset__execute_sql`:
- `database_id`: **sempre `2`** (base "PX DB" — Postgres monolítico da plataforma Motorista PX).
  Nenhum outro `database_id` é permitido por esta skill.
- `schema`: schema da tabela no Postgres (ex: `public`)
- `sql`: a query gerada — **somente leitura** (`SELECT`/`WITH`); sempre com `LIMIT` e apenas as
  colunas necessárias

> ⚠️ Essa conexão usa **credencial de serviço compartilhada** (não a identidade do usuário) e não
> passa pelo controle de acesso por domínio do px-data-access. Trate o acesso como sensível:
> minimize o escopo da query e não extraia mais dados do que a pergunta exige.

Se falhar:
- `database_id` ≠ 2 → corrigir para `2`; se o dado é analítico, ele provavelmente está no BigQuery (Passo 6)
- Tabela inexistente no Postgres → confirmar schema (`public.<tabela>`) ou reavaliar se o dado está no BigQuery

### Passo 7 — Resultado

Incluir na resposta:
- Tabelas utilizadas (nome, camada, FQN)
- Colunas chave e o que representam
- Query executada (formatada e comentada)
- Suposições feitas
