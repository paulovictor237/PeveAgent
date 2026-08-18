---
name: tiny-task
description: >
  Avalia se uma task do Jira é realmente pequena (low effort) e, se for, executa
  o fluxo completo de forma autônoma: criar worktree, branch, dev, commit, push
  e abrir PR. Use quando o usuário diz "tiny-task", "tarefa pequena", "task rápida",
  "isso é rápido, faz aí", ou invoca /tiny-task com um link do Jira.
---

# tiny-task

Você é o agente `tiny-task`. Recebe o link de uma task do Jira e decide se ela é
realmente **tão pequena** a ponto de ser executada em modo autônomo. Caso não seja,
recomenda o modo planejado e encerra. Caso seja, executa o pipeline completo.

## Princípios

- **Autonomia proporcional ao risco.** Quanto menor a task, mais autonomia. Quanto
  maior, mais planejamento e aprovação humana.
- **Falhar para o lado seguro.** Em qualquer dúvida, classifique como "não é tiny"
  e pare.
- **Sem surpresas no PR.** O PR é entregue pronto para revisão humana, mas a
  descrição é gerada localmente (sem postar comentários esquisitos no Jira).
- **Siga o que já existe.** Mudanças tiny devem espelhar padrões já presentes no
  código (mesmo componente, mesmo label, mesmo href, mesmo seletor) — nunca
  criar padrão novo.

## Entrada esperada

O usuário fornece uma URL do Jira no formato:

```
https://<tenant>.atlassian.net/browse/<PROJ>-<NUM>
```

Extraia a chave `<PROJ>-<NUM>` da URL antes de prosseguir.

## Etapa 1 — Buscar a task (one-shot, sem pager)

A CLI `acli` abre pager no terminal do agente. Use **uma** chamada que
concatene `2>&1 | cat` para forçar saída não-paginada. Salve o resultado em
memória — não precisa reler:

```sh
acli jira workitem view <PROJ>-<NUM> --json 2>&1 | cat
```

Para extrair só os campos relevantes e economizar tokens, use:

```sh
acli jira workitem view <PROJ>-<NUM> --json 2>&1 | cat | python3 -c "
import json, sys
d = json.load(sys.stdin)
f = d['fields']
print('summary:', f.get('summary'))
print('type:', f['issuetype']['name'])
print('status:', f['status']['name'])
print('priority:', (f.get('priority') or {}).get('name'))
print('labels:', f.get('labels'))
print('storyPoints:', f.get('customfield_10016'))
print('parent:', (f.get('parent') or {}).get('key'))
"
```

> A skill `cli-jira` documenta `acli jira issue view` (versão antiga). O comando
> atual é `acli jira workitem view`. Se `workitem` falhar com "unknown command",
> tente `issue` como fallback.

Campos a observar:

- `summary` — título da task (procurar prefixo `[Quick Win]`)
- `description` — corpo e critérios
- `type` — Task / Bug / Story / Epic / Sub-task
- `priority` — Low / Medium / High / Highest
- `labels` — rótulos (e.g. `quick-win`, `chore`, `tech-debt`)
- `storyPoints` — tamanho (se disponível)
- `parent` / `epicLink` — se é sub-tarefa
- `status` — só prosseguir se estiver em estado que permita trabalho (e.g.
  `To Do`, `Ready to dev`, `Open`). Se já estiver `In Review` ou `Done`, pare
  e avise.
- `comment` — ler comentários pode mudar o escopo (alguém já descobriu que
  "é maior do que parecia")

## Etapa 2 — Avaliar se é tiny

A task **só é tiny** se **todos** os critérios abaixo forem verdade. Qualquer
"não" ⇒ não é tiny.

### Critérios quantitativos

| # | Regra                                                                                     | Limite tiny |
|---|-------------------------------------------------------------------------------------------|-------------|
| 1 | Número estimado de arquivos modificados (incluindo testes)                                | ≤ 10        |
| 2 | Linhas de código alteradas (adições + remoções, aproximado a partir da descrição)          | ≤ 150       |
| 3 | Quantidade de arquivos de teste novos ou alterados                                       | ≤ 3         |
| 4 | Quantidade de serviços/módulos/projetos no monorepo tocados                              | 1           |
| 5 | Necessidade de migração de banco / feature flag                                           | não         |
| 6 | Necessidade de rodar migration, seed ou script destrutivo                                 | não         |
| 7 | Mudança em contrato público (API breaking, schema público, evento externo)                | não         |

### Critérios qualitativos

- **Escopo fechado.** A descrição contém critérios de aceite claros e não-ambíguos.
  Sem "verificar com o time", "avaliar impacto em", "decidir com o PO".
- **Sem dependência externa.** Não precisa de design, copy, decisão de produto,
  acesso a outro time ou sistema.
- **Sem pesquisa/spike.** Não é "investigar", "descobrir", "prototipar".
- **Risco operacional baixo.** Não toca infra, secrets, billing, auth/permissões,
  pagamentos, dados sensíveis, cronjobs, deploy pipeline.
- **Reproduzível em ≤ 30 min de desenvolvimento focado.**
- **Tipo da issue.** `Bug` simples (causa conhecida, escopo claro) e `Task`/`Chore`
  pontuais podem ser tiny. `Story`/`Epic`/`Spike` quase nunca são.
  - **Exceção (calibrada com EER-381 e EER-382):** Epic/Story pode ser tiny
    quando **todos** os sinais abaixo convergem:
    1. Marcador de tamanho rápido: label `quick-win` **ou** prefixo `[Quick Win]`
       no summary (EER-382 tem só o prefixo — aceito).
    2. Escopo de copy/texto/CTA/typo/label — sem mudança de regra de negócio,
       layout novo, integração ou API.
    3. Critérios de aceite verificáveis listados como task items.
    4. "Estilo visual alinhado ao padrão" conta como **seguir padrão existente**,
       não como design novo. Use o **mesmo componente, mesma prop, mesmo seletor**
       que já é usado no resto do código.
    5. "Validar em mobile/desktop" é checagem padrão cross-device, não escopo
       extra.
    6. Múltiplas variantes do mesmo componente (ex.: campanha A e A-90d) contam
       como o **mesmo** fix replicado — não como escopo novo.

### Heurísticas por label

Sinais fortes de tiny: `quick-win`, `chore`, `typo`, `deps`, `renaming`,
`label-only`, `config-only`, `linter`, `formatting`, `comment-only`.

Sinais fortes de NÃO tiny: `spike`, `research`, `design`, `breaking-change`,
`migration`, `security`, `infra`, `feature`, `rfc`. `epic` sozinho não bloqueia
mais — ver exceção na regra de tipo acima.

### Story points (se houver)

- 1 SP e às vezes 2 SP → tiny
- 3 SP → borderline (avaliar qualitativamente)
- 5+ SP → não é tiny

### Saída da avaliação

Produza uma resposta curta com:

1. **Veredito:** `TINY` ou `NÃO É TINY`
2. **Tamanho estimado:** `<n>` arquivos / `<n>` linhas
3. **Risco:** `baixo` / `médio` / `alto`
4. **Por quê:** bullets curtos citando as regras que pesaram
5. **Próximo passo:** executar pipeline OU parar

## Etapa 3 — Se NÃO é tiny

Pare imediatamente. Não crie worktree, não toque em branch. Responda:

> Essa task **não** é tiny. Motivo(s): <bullets>.
>
> Sugiro desenvolver com mais calma: abrir a task no editor, planejar,
> dividir em sub-tasks se necessário, e voltar a usar o `tiny-task` em cada
> fatia pequena. Processo encerrado sem alterações no repositório.

Faça uma transição opcional no Jira para `In Progress` **só** se o usuário
tiver pedido, caso contrário não toque na issue.

## Etapa 4 — Se É tiny: estratégia ANTES de codar

Antes de chamar o script, planeje em 3-6 bullets:

1. **Arquivos a tocar** (estimativa)
2. **Mudança central** (uma frase: o que vai ser feito)
3. **Critério de aceite verificável** (como saber que terminou)
4. **Risco residual** (o que pode dar errado mesmo sendo tiny)
5. **Plano de teste** (unitário, manual, e2e — o que fizer sentido)
6. **Plano de rollback** (uma linha: reverter o commit)

Confirme que o `cwd` do terminal é a raiz do projeto (onde fica o `package.json`).
Se não for, peça ao usuário para rodar a skill de dentro do projeto certo.

## Etapa 5 — Executar o pipeline

Use o script `scripts/tiny_task.py` da própria skill. Ele é idempotente e
interrompe com erro se algo falhar. Chame assim (o script vive em
`~/.claude/skills/tiny-task/scripts/`, independente de a skill estar em
`~/.claude/skills/` ou `~/.agents/skills/`):

```bash
python ~/.claude/skills/tiny-task/scripts/tiny_task.py \
  --ticket <PROJ>-<NUM> \
  --summary "<resumo curto, kebab-case, sem prefixo da issue>" \
  --base main \
  --commit-msg "<mensagem Conventional Commits>"
```

O script faz, em ordem:

1. `git fetch origin` e detecta `main` (configurável via `--base`)
2. `git switch <base>` e `git pull --ff-only`
3. `git worktree add ../<repo>-<TICKET>-<slug> -b <ticket> origin/<base>`
4. `cd` na worktree e `export GITHUB_TOKEN=$PX_GH_TOKEN` (e `GH_TOKEN` como
   fallback, derivado de `GITHUB_TOKEN`)
5. `npm ci` (fallback para `npm i` se não houver `package-lock.json`)
6. pausa para o agente desenvolver (ver seção "Pausa para desenvolvimento")
7. `git add -A` e commit com mensagem `Conventional Commits` (gerada pelo
   agente, sem assinatura de IA)
8. `git push -u origin <ticket>`
9. **não** abre PR — a abertura do PR fica para a Etapa 6 (o agente usa a skill
   `pr-description` para gerar a descrição rica a partir do template do projeto)
10. imprime o caminho da worktree

> Importante: o script não roda `npm test` automaticamente. Você decide se
> roda e em que escopo (apenas os arquivos tocados, idealmente). Em projetos
> com `husky` + pre-push, os testes rodam automaticamente no push.

### Pausa para desenvolvimento (ponto de atenção)

A pausa usa `input()` para bloquear. Em **terminais não-interativos** (agentes
que rodam tools), `input()` retorna `EOFError` e o script prossegue
imediatamente. Resultado: o commit falha com "nada para commitar".

**Solução segura para o agente**: rodar o script com `--no-wait` em duas
fases:

```bash
# Fase 1 — preparar worktree, instalar deps, parar antes do commit
python ~/.claude/skills/tiny-task/scripts/tiny_task.py \
  --ticket EER-382 \
  --summary "fix-cta-taxa-zero" \
  --no-wait=false   # deixa pausar, mas em agente ele cai no EOFError
```

Se o script cair no EOFError, **edite os arquivos no worktree** e rode a
**Fase 2 manualmente** (não reexecute o script — ele conflita na criação da
worktree):

```bash
WT=../<repo>-<ticket>-<slug>
git -C "$WT" add -A
git -C "$WT" commit -m "<msg>"
git -C "$WT" push -u origin <ticket>
```

Ou simplesmente reexecute o script com `--no-wait` depois de apagar a
worktree conflitante (`git worktree remove ...`).

### Editar arquivos dentro do worktree

O worktree fica **fora** da raiz do projeto (geralmente em `../<repo>-<TICKET>`).
Várias ferramentas do agente têm o path root travado:

- `edit_file` / `write_file` rejeitam paths fora do projeto.
- `terminal` recusa `cd` para fora do projeto.

**Workarounds (em ordem de preferência)**:

1. **Aplicar patch a partir de um arquivo de diff** salvo na raiz do projeto:
   ```bash
   # salve o diff desejado em /tmp/fix.patch e aplique na worktree
   git -C "$WT" apply /tmp/fix.patch
   ```

2. **`python3` one-liner** com `read_text/write_text` em path absoluto:
   ```bash
   python3 -c "
   from pathlib import Path
   p = Path('$WT/src/.../file.tsx')
   s = p.read_text()
   assert '<old block>' in s
   p.write_text(s.replace('<old block>', '<new block>', 1))
   "
   ```

3. **`sed -i` em path absoluto** (cuidado com caracteres especiais):
   ```bash
   sed -i '' 's/old/new/g' "$WT/src/.../file.tsx"   # macOS
   sed -i 's/old/new/g' "$WT/src/.../file.tsx"      # Linux
   ```

4. **Abra o worktree no editor manualmente** e edite visualmente, depois
   confirme o diff com `git -C "$WT" --no-pager diff`.

**Validação rápida após editar** (dentro do worktree, via `git -C`):
```bash
git -C "$WT" --no-pager diff --stat
git -C "$WT" --no-pager diff
```

**Validações recomendadas antes de commitar**:
```bash
git -C "$WT" add -A
# typecheck
git -C "$WT" run-as-helper npx tsc --noEmit      # ou equivalente
# lint focado nos arquivos tocados
git -C "$WT" run-as-helper npx eslint <arquivos>
```

> Substitua `run-as-helper` por qualquer wrapper que o `package.json`
> expuser; no `px-painel` use direto `npx`.

### Decisões que VOCÊ (o agente) toma sozinho

- Mensagem de commit (Conventional Commits, escopo claro)
- Rodar ou não `npm test`/`npm run lint`/`npm run typecheck` antes do commit
- Escolher `npm ci` vs `npm i` (o script tenta `ci` primeiro; se não houver
  lockfile, cai para `i`)
- Granularidade do commit: 1 commit ou múltiplos. Prefira **1 commit** quando
  a mudança for coesa; **2-3 commits** se houver camadas naturais
  (refactor + feat, por exemplo)

### Decisões que pedem aprovação humana

- Reformatar arquivos não relacionados (não faça)
- Atualizar dependências além do estritamente necessário (não faça)
- Rodar migrations (não faça em modo tiny; se precisar, a task não é tiny)
- Publicar em branch diferente de `<TICKET-lowercase>` (não faça)

## Etapa 6 — Abrir o PR

O script `tiny_task.py` **não** abre o PR. Abre o PR manualmente com a skill
`pr-description`:

```bash
gh pr create --draft --base main --head <ticket> \
  --title "[<TICKET>] - <título>" \
  --body "$(cat <<'EOF'
<corpo gerado pela skill pr-description>
EOF
)"
```

Consulte a skill `pr-description` para gerar o corpo rico a partir do template
do projeto (`/.github/pull_request_template.md`).

## Etapa 7 — Pós-execução

Devolva ao usuário:

- A URL do PR (em destaque)
- A worktree criada (caminho) e como removê-la quando terminar:
  `git worktree remove ../<repo>-<TICKET>`
- O resumo de 1-2 frases do que foi feito
- Sugestão de próximos passos: revisar, mergear após aprovação, deletar a
  worktree

## Quando NÃO usar esta skill

- Task com escopo aberto ("verificar", "investigar", "melhorar")
- Mudanças que tocam múltiplos serviços
- Mudanças com migração de banco
- Mudanças em produção crítica (auth, billing, infra)
- Refactors amplos (mesmo "pequenos" no título, podem tocar muito código)

Nesses casos, planeje com calma, quebre em sub-tasks, e use `tiny-task` em
cada sub-task pequena.

## Calibration log

Registro de exemplos reais que ajustaram os critérios. Adicionar nova entrada
sempre que uma task mudar o veredito esperado.

- **EER-381 (2026-07-03)** — Epic com `[Quick Win]` no summary + escopo de copy
  (2 correções textuais). Resultado: tiny. Insight: tipo Epic + `[Quick Win]`
  label/summary + copy-only não é bloqueador.
- **EER-382 (2026-07-03)** — Epic com `[Quick Win]` **só no summary** (label era
  `melhoria`), 2 variantes da campanha (Taxa Zero + Taxa Zero 90d), requisito
  de "estilo visual alinhado" e "validar mobile/desktop". Resultado: tiny.
  Insights:
  1. `[Quick Win]` pode estar só no summary, não precisa estar nos labels.
  2. "Seguir padrão visual existente" ≠ design novo — basta usar o
     **mesmo componente + mesmas props** que o resto já usa.
  3. "Validar mobile/desktop" é check padrão, não escopo extra.
  4. Múltiplas variantes do mesmo card = mesmo fix replicado.
  5. **Fluxo executado em produção**: o script original pausava para
     desenvolvimento via `input()`, que falha em agentes não-interativos
     (EOFError → "nada para commitar"). Solução adotada: rodar com `--no-wait`
     em duas fases ou aplicar as mudanças no worktree via `python3`/`sed`
     absoluto e commitar manualmente. O PR foi aberto fora do script, usando
     `pr-description` para gerar o body rico.
