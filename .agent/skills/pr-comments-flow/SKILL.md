---
name: pr-comments-flow
description: "Revisão interativa de comentários de PR — percorre cada sugestão de revisão uma por uma, decide com o usuário como proceder, marca como resolvido no GitHub e aprende padrões para o CLAUDE.md. Use esta skill sempre que o usuário quiser revisar comentários de PR, responder sugestões de code review, resolver threads de PR, ou dizer: 'bora revisar os comentários do PR', 'vamos ver os comentários do PR', 'tem comentários no PR pra resolver', 'me mostra o que o revisor pediu', 'vamos caminhando pelos comentários', '/pr-comments-flow', ou qualquer variação de querer trabalhar em cima de feedback de code review."
---

# Skill: Revisão Interativa de Comentários de PR

## Scripts disponíveis

Todos os scripts estão em `~/.claude/skills/pr-comments-flow/scripts/` e devem ser chamados via Bash tool.

| Script | Uso | Descrição |
|--------|-----|-----------|
| `pr-fetch.sh <PR>` | Passo 2 | Busca, deduplica e salva comentários em `/tmp/pr-{N}-comments.json` |
| `pr-next-comment.sh [PR]` | Passo 4 | Retorna próximo comentário pendente como JSON |
| `pr-excerpt.sh <file> <line> [ctx=15]` | Passo 4 | Extrai trecho do arquivo ao redor de uma linha |
| `pr-reply.sh <comment_id> <body>` | Passo 5 | Posta resposta no thread do comentário |
| `pr-resolve.sh <thread_id>` | Passo 5 | Marca thread como resolvido no GitHub |
| `pr-update-progress.sh <PR> <id> <status>` | Passo 5 | Atualiza arquivo de progresso (`applied`/`skipped`) |
| `pr-progress.sh [PR]` | Qualquer momento | Exibe resumo do progresso atual |

**Arquivos de estado em `/tmp/`:**
- `/tmp/pr-{N}-comments.json` — comentários pré-processados e deduplicados
- `/tmp/pr-{N}-progress.json` — rastreamento de progresso da sessão

---

## Passo 1 — Identificar o PR

```bash
gh pr view --json number,title,url 2>/dev/null
```

Se encontrar, confirme com o usuário:

```
Encontrei o PR aberto nesta branch:

  #123 — Título do PR
  https://github.com/org/repo/pull/123

É este PR que vamos revisar? [S/n]
```

Se negar ou falhar, peça o número: `Qual o número do PR? #`

---

## Passo 2 — Pré-processar comentários

Sempre re-fetche do GitHub para garantir dados atualizados:

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-fetch.sh {PR_NUMBER}
```

Se existir progresso anterior (`/tmp/pr-{N}-progress.json`), após o fetch pergunte:
```
Encontrei progresso de uma sessão anterior:
  Aplicados: X | Pulados: Y

Deseja manter este progresso (não revisitar comentários já tratados)? [S/n]
```

Se "N", delete o arquivo de progresso:
```bash
rm /tmp/pr-{PR_NUMBER}-progress.json
```

Se não houver comentários pendentes, informe: `Nenhum comentário de review aberto encontrado neste PR.`

---

## Passo 3 — Apresentar o resumo

Leia o arquivo de comentários e mostre o resumo organizado por arquivo. **Leia apenas os campos necessários para o resumo:**

```bash
jq -r '.files[] | "  📄 \(.path) (\(.comments | length) comentário(s))"' /tmp/pr-{N}-comments.json
```

```
Encontrei X comentários em Y arquivo(s):

  📄 src/services/PaymentService.ts (2 comentários)
  📄 src/Models/Contract.ts (1 comentário)

Vamos começar. [Enter para continuar]
```

---

## Passo 4 — Revisar comentário por comentário

### 4a. Obter próximo comentário

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-next-comment.sh {PR_NUMBER}
```

Isso retorna um JSON com: `id`, `path`, `line`, `body`, `thread_id`, `diff_hunk`, `duplicate_count`.

Se `duplicate_count > 0`, adicione nota: `⚠️ Este comentário apareceu {N+1}x de revisores diferentes.`

### 4b. Obter contexto do arquivo (lazy — só as linhas relevantes)

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-excerpt.sh "{path}" {line}
```

**Não use o Read tool para ler o arquivo inteiro.** Use `pr-excerpt.sh` que retorna ±15 linhas ao redor da linha comentada. Só use Read se precisar de contexto muito mais amplo e isso for claramente necessário.

### 4c. Exibir e propor

Mostre sempre neste formato:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 src/services/PaymentService.ts — linha 42
[X/TOTAL]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 Revisor:
"Esse método pode lançar uma exceção não tratada se $amount for negativo."

📌 Diff:
  (últimas linhas do diff_hunk)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Analise o comentário + contexto do arquivo, então **proponha o que pretende fazer**:

```
💡 O que pretendo fazer:
Adicionar validação no início do método para lançar InvalidArgumentException
quando $amount <= 0, antes da chamada ao gateway.

Como quer prosseguir?
  [1] Aplicar esta mudança
  [2] Pular (não aplicar)
  [3] Discutir / quero sugerir algo diferente
```

Aguarde resposta antes de qualquer ação.

### 4d. Respostas

- **[1] Aplicar** — implemente. Após implementar, confirme brevemente.
- **[2] Pular** — não altere nada. Passe para o próximo.
- **[3] Discutir** — ouça a sugestão, atualize a proposta, pergunte novamente.
- **[4] Responder no PR** — compor uma resposta para o thread do GitHub sem alterar código.

Quando o usuário escolher **[4]**, elabore a resposta e mostre para aprovação:

```
💬 Resposta proposta:
"[texto da resposta]"

Postar no thread? [S/n]
```

Só poste após confirmação:

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-reply.sh {COMMENT_ID} "{REPLY_BODY}"
```

---

## Passo 5 — Atualizar progresso e resolver thread

Após cada comentário (aplicado ou pulado conscientemente), execute **em paralelo**:

```bash
# Atualizar progresso local
~/.claude/skills/pr-comments-flow/scripts/pr-update-progress.sh {PR_NUMBER} {COMMENT_ID} {applied|skipped}

# Marcar thread como resolvido no GitHub
~/.claude/skills/pr-comments-flow/scripts/pr-resolve.sh {THREAD_ID}
```

Se `thread_id` for `null`, pule a resolução sem erro.

> Se o script de resolução falhar, avise e continue.

---

## Passo 6 — Propor aprendizado para o CLAUDE.md

Após resolver cada comentário **aplicado**, pergunte sempre:

```
Quer criar uma instrução para o CLAUDE.md do projeto com base neste comentário? [S/n]
```

**Se "S":** analise o padrão identificado e proponha uma regra concreta:

```
📚 Sugestão para o CLAUDE.md:

  "Antes de definir um novo tipo TypeScript, verifique se ele já existe no projeto —
   tipos costumam estar centralizados em types.ts dentro do feature folder."

Adiciono? [S/n]
```

Se confirmar, encontre o CLAUDE.md mais próximo do diretório atual e adicione à seção `## Regras derivadas de Code Review` (crie a seção se não existir):

```bash
# Encontra o CLAUDE.md mais próximo subindo a partir do CWD
dir=$(pwd)
while [[ "$dir" != "/" ]]; do
  [[ -f "$dir/CLAUDE.md" ]] && { echo "$dir/CLAUDE.md"; break; }
  dir=$(dirname "$dir")
done
```

Se nenhum arquivo for encontrado, crie `CLAUDE.md` no diretório atual.

> Use `CLAUDE.local.md` apenas se o usuário solicitar explicitamente (ex: "adiciona no local", "não quero versionar").

**Se "N":** siga para o próximo comentário sem nenhuma ação adicional.

---

## Passo 7 — Avançar para o próximo arquivo

Ao terminar todos os comentários de um arquivo:

```
✅ src/services/PaymentService.ts concluído (2/2 comentários tratados).

Próximo: 📄 src/Models/Contract.ts (1 comentário). [Enter para continuar]
```

Volte ao **Passo 4** com `pr-next-comment.sh` para o próximo comentário.

---

## Passo 8 — Commit das alterações (se houver)

Antes do resumo final, verifique se houve alterações aplicadas:

```bash
git diff --name-only
```

Se houver arquivos modificados, use a skill `atomic-commits` para gerar e fazer o commit semântico. O commit deve referenciar o PR e descrever as mudanças aplicadas (ex: `fix: aplicar sugestões de code review do PR #123`).

Só realize o commit se o usuário confirmar:

```
Há X arquivo(s) modificado(s) com as alterações aplicadas. Deseja fazer commit agora? [S/n]
```

Se "N", avise que as mudanças ficaram sem commit e prossiga para o resumo.

---

## Passo 9 — Resumo final

```bash
~/.claude/skills/pr-comments-flow/scripts/pr-progress.sh {PR_NUMBER}
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Revisão concluída — PR #123

  Aplicados:            3
  Pulados:              1
  Resolvidos no GitHub: 4

  Regras adicionadas ao CLAUDE.md: 1
  Commit realizado:     sim
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Princípios de condução

- **Sempre proponha antes de agir** — nunca altere sem confirmação.
- **Use os scripts, não a API inline** — nunca chame `gh api` diretamente quando há script disponível.
- **Contexto mínimo** — use `pr-excerpt.sh` em vez de Read para arquivos; use `pr-next-comment.sh` em vez de ler o JSON inteiro.
- **Sempre re-fetche** — nunca use cache de comentários; sempre rode `pr-fetch.sh` ao iniciar para garantir sincronização com o GitHub.
- **Não trave em erros de API** — se resolver o thread falhar, avise e continue.
- **Sempre pergunte sobre CLAUDE.md** — após cada comentário aplicado, pergunte se o usuário quer criar uma instrução. Só elabore a regra após confirmação. Use sempre o `CLAUDE.md` mais próximo do CWD (busca subindo a partir do diretório atual). Só use `CLAUDE.local.md` se o usuário solicitar explicitamente.
- **Commit ao finalizar** — ao terminar o fluxo, se houver arquivos modificados, proponha commit usando a skill `atomic-commits`. Nunca commite sem confirmação do usuário.
- **Linguagem**: responda sempre em português.
