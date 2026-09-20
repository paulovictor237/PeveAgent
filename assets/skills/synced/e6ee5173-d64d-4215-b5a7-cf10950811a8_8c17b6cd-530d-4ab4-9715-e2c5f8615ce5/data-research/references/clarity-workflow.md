# Clarity Workflow — Comportamento UX e Sessões

Usar quando a pergunta envolve como usuários interagem com a interface: cliques, scroll,
sessões, rage clicks, dead clicks, heatmaps, ou métricas de engajamento com UI.

## Quando usar Clarity vs PostHog

| Clarity | PostHog |
|---|---|
| "Onde os motoristas mais clicam?" | "Quantos motoristas clicaram em X?" |
| "Qual a profundidade de scroll na tela de cadastro?" | "Qual a taxa de conclusão do cadastro?" |
| "Há rage clicks na tela de pagamento?" | "Funil da tela de pagamento" |
| "Qual o tempo médio em sessão?" | "Usuários ativos diários" |
| "Quais dispositivos/browsers os usuários usam?" | "Breakdown por propriedade de evento" |

## Duas instâncias do Clarity

| Instância | Ferramenta | Plataforma |
|---|---|---|
| App (motorista) | `mcp__cortex__clarity-app__query-analytics-dashboard` | App mobile/web do motorista |
| Painel (gestores) | `mcp__cortex__clarity-painel__query-analytics-dashboard` | Painel administrativo/gestores |

Se a pergunta não especificar, perguntar ao usuário qual plataforma antes de executar.

## Workflow

### Passo 1 — Identificar a plataforma

Determinar se a pergunta é sobre:
- App do motorista → usar `clarity-app`
- Painel dos gestores → usar `clarity-painel`
- Ambos → executar nas duas instâncias

### Passo 2 — Formular a query

A query é em linguagem natural, mas deve ser:
- **Específica**: focar em uma métrica por vez
- **Com período de tempo explícito**: sempre incluir o range de datas
- **Objetiva**: descrever exatamente o que buscar

**Exemplos de boas queries:**
- `"Top pages by scroll depth last 7 days"`
- `"Rage clicks rate on payment screen last 30 days"`
- `"Average session duration by device type last week"`
- `"Most clicked elements on onboarding screen last 14 days"`
- `"Dead click rate by browser last month"`
- `"Top referrers last 7 days"`

**Exemplos ruins (muito vagos):**
- `"Como os usuários se comportam"` → refinar para uma métrica específica
- `"Dados do app"` → especificar qual dado

### Passo 3 — Execução

Usar a ferramenta correspondente com a `query` formulada no passo anterior.

Se o período não foi especificado pelo usuário, **perguntar antes de executar**.

### Passo 4 — Documentação do Clarity

Para perguntas sobre como configurar ou entender features do Clarity (heatmaps, recordings,
filtros, integrações), usar `mcp__cortex__clarity-app__query-documentation-resources`.

## Comportamento em caso de erro

- Sem dados no período → tentar um período mais amplo e avisar o usuário
- Query muito vaga → reformular com mais especificidade
- Plataforma não identificada → perguntar ao usuário (app do motorista ou painel?)
