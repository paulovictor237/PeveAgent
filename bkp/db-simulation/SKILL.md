---
name: db-simulation
description: >
  Transforma um spec de brainstorming em artefatos de teste de banco de dados prontos para uso.
  Gera um arquivo SQL estruturado com cenários de simulação (INSERT/UPDATE direto no banco) e,
  opcionalmente, um script Python que executa os SQLs e valida o comportamento esperado nas APIs.
  Use esta skill sempre que o usuário quiser: criar cenários de teste para uma feature, simular
  estados de banco para validar lógica de negócio, gerar script de simulação, testar comportamento
  de API após mutações no banco, ou qualquer variação de "cria simulação", "gera cenários de teste",
  "simula cenários do spec", "quero testar os cenários do brainstorming". Acionar com /sim.
---

# db-simulation

Você transforma specs de brainstorming em artefatos de teste concretos: um `.sql` com cenários de
simulação de banco e, se o usuário quiser, um script Python que valida o comportamento das APIs
após cada mutação.

A ideia central é que testar lógica de negócio complexa muitas vezes é mais rápido simulando
estados diretamente no banco do que acionando toda a camada de negócio. O `.sql` captura esses
estados de forma reproduzível, e o Python fecha o loop validando que as APIs respondem corretamente.

## Caminhos

Todos os artefatos ficam em `.claude/simulations/` relativo ao cwd (diretório onde o Claude Code foi iniciado).

- Artefatos: `.claude/simulations/YYYY-MM-DD-<nome-cenario>/`
- Config do banco: `.claude/db-settings.json`

## Passo 1 — Escolher o spec / plano

**Se um arquivo foi passado como argumento** (ex: `@docs/superpowers/plans/arquivo.md`), use-o diretamente como base — pule a listagem de specs.

Caso contrário, liste todos os arquivos em `docs/superpowers/specs/` e apresente ao usuário.

Ao ler o arquivo base, se ele for grande (>200 linhas), leia em partes usando `offset` e `limit`.

Do arquivo selecionado, extraia:
- Entidade principal (tabela/model afetado)
- Campos relevantes e seus estados possíveis
- Regras de negócio e comportamentos esperados
- Ticket/issue de referência (se presente)

O `<nome-cenario>` para nomear os artefatos é derivado do nome do arquivo removendo o prefixo
de data e sufixos como `-design.md` ou `-reopen.md`. Ex:
- `2026-03-23-vehicle-review-design.md` → `vehicle-review`
- `2026-03-23-single-daily-review-reopen.md` → `single-daily-review-reopen`

## Passo 2 — Gerar o arquivo SQL

Gere `.claude/simulations/YYYY-MM-DD-<nome-cenario>/scenarios.sql` seguindo esta estrutura:

```sql
-- ==========================================================================
-- <TICKET> — <Descrição do cenário>
-- Contexto: <entidade>, <campos relevantes>
--
-- COMPORTAMENTO ESPERADO:
--   <regra 1 extraída do spec>
--   <regra 2 extraída do spec>
-- ==========================================================================
-- ORDEM DE EXECUÇÃO:
--   0. LIMPEZA TOTAL (opcional)
--   1. PRÉ-CONFIGURAÇÃO
--   2. Escolha um cenário: execute [BEGIN SCENARIO N] até [END SCENARIO N]
-- ==========================================================================

-- ====== LIMPEZA TOTAL ======
DELETE FROM <tabela_dependente> WHERE <condição>;
DELETE FROM <tabela_principal> WHERE <condição>;
SELECT 'Limpeza concluída.' AS status;

-- ====== PRÉ-CONFIGURAÇÃO ======
-- Garante estado base necessário para os cenários
UPDATE <tabela> SET <campo> = <valor> WHERE <condição>;

-- [BEGIN SCENARIO 1: <nome-descritivo>]
-- Objetivo: <campo> = '<valor_esperado>'
SELECT id, <campos_que_serão_alterados>
FROM <tabela>
WHERE <condição>;

-- <campo>: '<valor1>', '<valor2>', '<valor3>'
UPDATE <tabela> SET <campo> = '<novo_valor>' WHERE <condição>;

SELECT id, <campos_alterados>
FROM <tabela>
WHERE <condição>;
-- Esperado:
--   GET /api/v3/<endpoint>
--   → { "<campo>": "<valor>" }
--   → { "<campo_nulo>": null }
-- [END SCENARIO 1]
```

**Formatação db-queries dentro de cada cenário:** cada mutação segue a convenção de sempre ter um
SELECT com as colunas afetadas (incluindo `id`) antes do UPDATE/DELETE, usando o mesmo WHERE. O
comentário `-- <campo>: 'val1', 'val2'` antes do UPDATE documenta os valores possíveis do enum —
infira-os do schema/migration/model do projeto. Nunca gere UPDATE ou DELETE sem cláusula WHERE.

**Sobre os delimitadores `[BEGIN SCENARIO N]` / `[END SCENARIO N]`:** eles existem para que o script
Python possa particionar automaticamente o arquivo. A LIMPEZA e PRÉ-CONFIGURAÇÃO ficam fora deles e
são executadas uma única vez antes do loop.

**Sobre o bloco `-- Esperado:`:** cada linha `→ { "chave": "valor" }` é um campo a validar
independentemente na resposta da API. Use notação de ponto para campos aninhados
(`"objeto.subcampo": "valor"`). Valores `null` ficam sem aspas: `→ { "campo": null }`.

Após gerar o `.sql`, pergunte ao usuário se deseja: **(a)** gerar o script Python de validação,
**(b)** executar os cenários diretamente no banco via db-executor, ou **(c)** só o `.sql` por ora.

## Passo 3 — Execução direta via db-executor (opcional)

Se o usuário escolher executar no banco agora, use a skill `db-executor` para rodar os cenários
com segurança. O fluxo é:

1. Verifique se `.claude/db-settings.json` existe (se não, siga o setup do db-executor)
2. Execute a LIMPEZA e PRÉ-CONFIGURAÇÃO uma vez (elas ficam fora dos blocos de cenário)
3. Para cada `[BEGIN SCENARIO N]`:
   - Mostre o objetivo do cenário ao usuário
   - Execute o SELECT de conferência via `db_tool.py` (leitura sem risco)
   - Execute o UPDATE/INSERT via `db_tool.py` — o script aplica dry-run automático e pede `yes`
   - Execute o SELECT de verificação pós-mutação
   - Registre o resultado (passou/falhou comparando com `-- Esperado:` se não houver Python)
4. Ao final, pergunte se deseja fazer rollback manual ou manter as mutações

O db-executor garante dry-run + confirmação explícita para cada escrita — nunca execute um UPDATE
de cenário sem passar pelo fluxo de confirmação do `db_tool.py`.

## Passo 4 — Script Python (opcional)

Se o usuário confirmar:

### 4a — Descoberta de APIs

Derive o nome do model Laravel da tabela (singular PascalCase: `vehicle_reviews` → `VehicleReview`).
Busque referências a esse model em:
- `px-torre-core/routes/` — arquivos de rotas
- `px-torre-core/app/Http/Controllers/` — controllers

Apresente a lista de endpoints encontrados e peça ao usuário para confirmar, adicionar ou remover
antes de prosseguir.

### 4b — Token de autenticação

Antes de gerar o script, verifique se `.claude/CLAUDE.local.md` contém `driver_id` ou `user_id`
pré-configurado. Se sim, use-o diretamente. Caso contrário, pergunte ao usuário.

**Nunca consulte o banco manualmente para descobrir a tabela de tokens ou buscar IDs antes de
gerar o script.** O script faz essas descobertas em runtime via psycopg2.

### 4c — Geração do script

**Conexão com o banco:** O script usa `psycopg2` conectando diretamente via `host`/`port`/`database`/`user`/`password`
do `bd-settings.json` (`bases[0]`). O campo `docker_container` é ignorado pelo script — nunca use
`docker exec` para consultar o banco.

Gere `.claude/simulations/YYYY-MM-DD-<nome-cenario>/validator.py` que:

1. Lê a conexão do banco de `.claude/db-settings.json` (campo `bases[0]`)
2. Conecta via `psycopg2.connect(host=..., port=..., dbname=..., user=..., password=...)` — sem docker exec
3. Descobre a tabela de tokens em runtime: tenta `driver_tokens` → `personal_access_tokens` → `oauth_access_tokens` (verifica `information_schema.tables`), seleciona o token mais recente não expirado do `driver_id` configurado
4. Consulta o banco para obter o bearer token (ex: `SELECT token FROM driver_tokens WHERE driver_id = <driver_id> AND expired_at > NOW() ORDER BY expired_at DESC LIMIT 1`)
5. Parseia `scenarios.sql` da mesma pasta extraindo blocos entre `[BEGIN SCENARIO N]` e `[END SCENARIO N]`
6. Para a LIMPEZA e PRÉ-CONFIGURAÇÃO: executa uma vez fora das transações
7. Para cada cenário:
   - Inicia uma transação individual
   - Executa o SQL de mutação (UPDATE/INSERT do cenário)
   - Chama a API com `Authorization: Bearer <token>`
   - Parseia o bloco `-- Esperado:` com regex: `→ \{ "(.+?)": (.+?) \}`
     - Valor entre aspas → string; `null` literal → None
     - Chaves com ponto → acesso aninhado no JSON de resposta
   - Compara campos esperados com resposta
   - Faz rollback da transação
   - Registra resultado
8. **Se API retornar 401:** aborta imediatamente com mensagem `"token inválido ou expirado"` (não é falha de cenário)
9. **Passou:** SQL executou sem erro E todos os campos do `-- Esperado:` presentes com valores exatos
10. **Falhou:** qualquer campo divergente, ou 4xx/5xx (exceto 401), com status code registrado
11. Imprime resultado final no terminal: total / passou / falhou por cenário
12. Pergunta ao usuário se deseja salvar `results.md` na mesma pasta

Se confirmar, gera `results.md` com:

```markdown
# <nome-cenario> — YYYY-MM-DD
✓ N/M cenários passaram

| # | Cenário | Status | Detalhe |
|---|---------|--------|---------|
| 1 | <nome> | ✓ | |
| 2 | <nome> | ✗ | campo `x` esperado "a", recebido "b" |
```

## .gitignore

Verifique se existe `.gitignore` na raiz do monorepo. Se não existir, crie. Garanta que estas
entradas estejam presentes:

```
.claude/simulations/*/validator.py
```

`results.md` é commitável — serve como evidência de validação no histórico do projeto.

## Restrições

- O `.sql` gerado é apenas o artefato de referência — nunca o execute automaticamente. A execução é sempre opt-in (via db-executor no Passo 3 ou manualmente pelo usuário).
- O script Python nunca committa mutações: rollback por cenário, sempre.
- Sem comentários no código Python gerado.
- Opera exclusivamente em `.claude/simulations/` e `px-torre-core/` (para busca de routes).
- Cada simulação vive em sua própria pasta `YYYY-MM-DD-<nome-cenario>/` com `scenarios.sql` e opcionalmente `validator.py`.
- Nunca gere UPDATE ou DELETE sem cláusula WHERE nos cenários — mesma regra do db-queries.

## Referências

- Modelo SQL de referência: `.claude/simulations/YYYY-MM-DD-<nome-cenario>/scenarios.sql`
