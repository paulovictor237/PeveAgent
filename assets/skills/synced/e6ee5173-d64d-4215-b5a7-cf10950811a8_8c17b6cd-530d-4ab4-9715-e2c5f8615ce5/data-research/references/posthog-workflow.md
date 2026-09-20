# PostHog Workflow — Eventos, Funis, Experimentos e Feature Flags

Usar quando a pergunta envolve comportamento de usuários no produto: eventos, funis de conversão,
usuários ativos, experimentos A/B, feature flags ou surveys.

## Quando usar PostHog vs SQL

| PostHog | SQL (BigQuery) |
|---|---|
| "Quantos usuários fizeram X?" | "Quantos motoristas foram agenciados?" |
| "Qual a conversão do funil de cadastro?" | "Qual a receita do mês passado?" |
| "O experimento ABC melhorou a conversão?" | "KPI de dias agenciados por empresa" |
| "Usuários ativos nos últimos 7 dias" | "Fretes completados por região" |
| "O feature flag X está ativo para quem?" | Joins complexos entre entidades |

## Workflow Geral

### Passo 1 — Identificar o tipo de pergunta

| Tipo | Ferramentas PostHog |
|---|---|
| Contagem/volume de eventos | `query-run` (TrendsQuery) |
| Funil de conversão | `query-run` (FunnelsQuery) |
| SQL sobre eventos (flexible) | `query-run` (HogQL) |
| Dashboard existente | `dashboards-get-all` → `dashboard-get` |
| Insight existente | `insight-get` → `insight-query` |
| Experimento A/B | `experiment-get-all` → `experiment-results-get` |
| Feature flags | `feature-flag-get-all` |
| Surveys/NPS | `surveys-global-stats` ou `survey-stats` |

### Passo 2 — Descobrir eventos e propriedades

Antes de montar uma query, verificar quais eventos existem:

1. Usar `mcp__cortex__posthog__event-definitions-list` para listar eventos
   - Se houver muitos eventos, filtrar com `q: "termo"` (ex: `q: "onboarding"`)
2. Para propriedades de um evento específico, usar `mcp__cortex__posthog__properties-list`
   com `type: "event"` e `eventName: "nome_do_evento"`
3. Para propriedades de persons (usuários), usar `properties-list` com `type: "person"`

### Passo 3A — Query de Trends (volume/contagem)

Usar `mcp__cortex__posthog__query-run` com `kind: "InsightVizNode"` e `source.kind: "TrendsQuery"`.

Exemplo — usuários únicos que fizeram `user_signed_up` nos últimos 30 dias por dia:
```json
{
  "kind": "InsightVizNode",
  "source": {
    "kind": "TrendsQuery",
    "series": [
      {
        "kind": "EventsNode",
        "event": "user_signed_up",
        "custom_name": "Cadastros",
        "math": "dau"
      }
    ],
    "dateRange": { "date_from": "-30d" },
    "interval": "day",
    "trendsFilter": { "display": "ActionsLineGraph" }
  }
}
```

**Opções de `math`:** `total`, `dau`, `weekly_active`, `monthly_active`, `unique_session`,
`first_time_for_user`, `avg`, `sum`, `min`, `max`

**Opções de `interval`:** `hour`, `day`, `week`, `month`

### Passo 3B — Query de Funnel (conversão)

Usar `kind: "FunnelsQuery"` com pelo menos 2 eventos em `series`.

Exemplo — funil de cadastro (mínimo 2 steps):
```json
{
  "kind": "InsightVizNode",
  "source": {
    "kind": "FunnelsQuery",
    "series": [
      { "kind": "EventsNode", "event": "onboarding_started", "custom_name": "Início" },
      { "kind": "EventsNode", "event": "document_uploaded", "custom_name": "Doc enviado" },
      { "kind": "EventsNode", "event": "onboarding_completed", "custom_name": "Concluído" }
    ],
    "dateRange": { "date_from": "-30d" },
    "funnelsFilter": {
      "funnelOrderType": "ordered",
      "funnelWindowInterval": 14,
      "funnelWindowIntervalUnit": "day"
    }
  }
}
```

### Passo 3C — HogQL (SQL sobre eventos)

Usar `kind: "DataVisualizationNode"` com `source.kind: "HogQLQuery"` para queries flexíveis.

Exemplo — top 10 empresas por cadastros:
```json
{
  "kind": "DataVisualizationNode",
  "source": {
    "kind": "HogQLQuery",
    "query": "SELECT properties.company_name, count() as cadastros FROM events WHERE event = 'user_signed_up' AND timestamp > now() - interval 30 day GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
  }
}
```

**Nota:** Usar HogQL apenas quando Trends/Funnel não atenderem ou quando a query HogQL for
conhecida (ex: vinda de um insight anterior).

### Passo 4 — Experimentos A/B

1. Listar experimentos: `mcp__cortex__posthog__experiment-get-all`
2. Identificar o experimento relevante pela descrição/nome
3. Buscar resultados: `mcp__cortex__posthog__experiment-results-get` com `refresh: false`
   (usar `refresh: true` apenas se os dados parecerem desatualizados)

O resultado inclui métricas primárias e secundárias, exposição por variante e significância estatística.

### Passo 5 — Feature Flags

Usar `mcp__cortex__posthog__feature-flag-get-all` para listar todas as flags.
Filtrar pelo nome/key relevante na resposta.

### Passo 6 — Surveys

- Todas as surveys: `mcp__cortex__posthog__surveys-global-stats`
- Survey específica: precisa do `survey_id` — descobrir via `surveys-global-stats` primeiro,
  depois usar `mcp__cortex__posthog__survey-stats` com o ID

Suporta filtros de data (`date_from`, `date_to`) em formato ISO 8601.

### Passo 7 — Dashboards e Insights existentes

Se a pergunta provavelmente já tem um dashboard ou insight criado:
1. `mcp__cortex__posthog__dashboards-get-all` — buscar por nome relevante
2. `mcp__cortex__posthog__dashboard-get` com o `dashboardId` para ver os insights do dashboard
3. `mcp__cortex__posthog__insight-get` com `insightId` para ver a definição
4. `mcp__cortex__posthog__insight-query` com `insightId` para executar e obter dados atuais

## Comportamento em caso de erro

- Evento não encontrado → listar eventos disponíveis e pedir confirmação ao usuário
- Query retorna vazio → verificar se o evento tem dados no período, ajustar `dateRange`
- Propriedade não encontrada → usar `properties-list` para descobrir propriedades disponíveis
