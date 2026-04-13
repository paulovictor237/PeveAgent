---
name: pr-description
description: 'Gera a descrição de Pull Request preenchendo o template do projeto com linguagem clara e não técnica, detecta automaticamente o branch base e abre o PR. Use esta skill sempre que o usuário pedir para: descrever um PR, escrever a descrição de PR, gerar o corpo do PR, preencher o template de PR, "descrever o que mudou no PR", "escrever o PR", "montar a descrição do pull request", "fill PR description", "write PR body", ou qualquer variação de escrever/preparar/montar a descrição de um pull request. Também acione quando o usuário diz "bora descrever o PR", "monta o PR", "descreve o PR pra mim", "preciso da descrição do PR", "preciso do body do PR", "abre o PR", "cria o PR".'
---

# Skill: Descrição e Abertura de Pull Request

Você vai gerar o texto completo da descrição de um Pull Request, preenchendo o template do projeto com linguagem acessível — focada no *o quê* e *por quê*, não nos detalhes técnicos de implementação — e em seguida **abrir o PR** apontando para o branch base correto.

## Passo 1 — Carregar o template

Leia o arquivo `/.github/pull_request_template.md` na **raiz do projeto atual** (working directory).

- Se o arquivo existir: use-o como estrutura base, mantendo todos os campos e seções.
- Se não existir: use a estrutura padrão abaixo.

```markdown
## 🔖 Escopo

## 🚩 Known issues

## 📁 Evidências

## Roteiro de testes: Caminho feliz

### Critério(s) de aceitação

## 💥 Pontos de impacto
```

## Passo 2 — Detectar o branch base

O script de detecção de branch base está na **pasta da própria skill**. Execute-o assim:

```bash
python ~/.claude/skills/pr-description/scripts/find_parent_branch.py
```

O script retorna até 3 candidatos ordenados por relevância (menor distância de commits). Apresente os candidatos ao usuário no formato:

```
Encontrei os seguintes branches de origem com commit em comum:

  #1 origin/main (recomendado)
  #2 origin/feature/outra-branch
  #3 origin/staging

Qual branch deve ser o destino do PR? [Enter para usar o #1]
```

Aguarde a resposta do usuário. Se o usuário pressionar Enter ou confirmar sem especificar, use o **#1 (primeiro candidato)** como branch base.

> **Se o script não existir**: use `git log --oneline -10` + `git branch -r` para inferir o branch base, ou pergunte ao usuário.

## Passo 3 — Coletar contexto

Com o branch base definido (`BASE_BRANCH`), colete informações para preencher o template:

1. **Diff das mudanças** — `git diff origin/BASE_BRANCH...HEAD` para ver o que foi alterado.
2. **Commits do branch** — `git log origin/BASE_BRANCH...HEAD --oneline` para entender a narrativa.
3. **Arquivos modificados** — `git diff origin/BASE_BRANCH...HEAD --name-only` para visão rápida do escopo.
4. **Ticket do Jira** — se o branch ou commits tiverem um ID de ticket (ex: `APX-1234`), **antes de consultar**, pergunte ao usuário:

```
Encontrei o ticket APX-1234 no branch. Deseja que eu busque mais informações no Jira para enriquecer a descrição? [S/n]
```

Se confirmar, execute: `acli jira issue view APX-1234`

Não peça ao usuário informações que você pode descobrir sozinho com essas ferramentas.
Fontes externas (Jira, etc.) devem ser consultadas **apenas com confirmação explícita do usuário**.

## Passo 4 — Preencher o template

Preencha cada seção do template seguindo estas diretrizes:

### 🔖 Escopo
Explique **o que foi feito e por que** em 2-5 frases. Foque no benefício ou problema resolvido, não nos arquivos modificados. Exemplos:

- ❌ "Adicionado método `calculateDiscount()` em `DiscountService` e atualizado o model `Contract`"
- ✅ "Corrige o cálculo de desconto que estava gerando valores negativos para contratos com antecipação"

Se houver um ticket Jira vinculado, mencione-o no final: *(APX-1234)*

### 🚩 Known issues
Liste limitações conhecidas ou decisões técnicas que ficaram para depois. Se não houver, escreva "N/A".

### 📁 Evidências
Não inclua prints reais (você não tem acesso). Deixe um placeholder claro:

```
<!-- Adicionar prints/logs/vídeos que comprovem o funcionamento -->
```

### Roteiro de testes: Caminho feliz
Descreva como alguém sem conhecimento do código pode verificar que a mudança funciona. Use passos simples e concretos:

- "Acesse a tela X"
- "Execute a ação Y"
- "Verifique que Z acontece"

### Critério(s) de aceitação
Liste 2-4 critérios observáveis (comportamento esperado), derivados dos passos de teste.

### 💥 Pontos de impacto
Identifique partes do sistema que podem ser afetadas. Prefira linguagem de negócio:

- ❌ "Model `Contract`, Service `PaymentService`, Job `ProcessPaymentJob`"
- ✅ "Cálculo de pagamentos de frete", "Tela de contratos no app do motorista"

### Campos com checkboxes (se existirem no template)
Deixe todos os checkboxes desmarcados — é responsabilidade do time preenchê-los.

## Passo 5 — Confirmar e abrir o PR

Após gerar a descrição, mostre o texto ao usuário e pergunte:

```
Descrição gerada. Deseja abrir o PR agora apontando para `BASE_BRANCH`? [S/n]
```

Se o usuário confirmar (Enter ou "S"), abra o PR com:

```bash
gh pr create \
  --base BASE_BRANCH \
  --title "TITULO_SUGERIDO" \
  --body "$(cat <<'EOF'
[DESCRICAO_GERADA]
EOF
)"
```

O título deve ser gerado automaticamente a partir do nome do branch e/ou ticket Jira, seguindo o padrão `[APX-1234] Descrição curta do que foi feito`. Se não houver ticket, use uma descrição concisa do que foi feito.

Retorne a URL do PR criado ao usuário.

## Linguagem

- Escreva em **português** (a não ser que o template esteja em outro idioma)
- Frases curtas e diretas
- Sem jargões técnicos desnecessários — imagine que o leitor é um QA ou PM, não o dev que escreveu o código
- Evite voz passiva excessiva
