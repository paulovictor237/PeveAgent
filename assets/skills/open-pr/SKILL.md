---
name: open-pr
description: "Opens an interactive Pull Request with the repository's template filled in automatically. Use when asked to open/create a PR."
user-invocable: true
allowed-tools: Bash
---

# Open Pull Request with filled-in template

## Usage

```
/open-pr
```

## 1. Base branch and Jira card

Ask for the base branch (main, develop, etc.) and the Jira card (e.g. "EDC-315").

## 2. Branch name

If the current branch doesn't follow the `feature/<CARD>-short-description` pattern with the card from step 1 (e.g. `feature/EDC-315-descricao-curta`), ask whether to rename it.

## 3. Push

If there are unpushed commits, push them before continuing — the PR is never created against a branch that's stale on the remote.

## 4. Analyze the changes

```bash
git diff <base>...HEAD
git log <base>..HEAD --oneline
```

Read the full diff before filling in the template — the step 5 summary only covers what was read here.

## 5. Fill in the template

Title: `[<CARD>] - <short description>`, in Brazilian Portuguese, under 72 characters. Example: `[QUAL-1234] - Descrição curta das mudanças`.

Body, in Brazilian Portuguese, following exactly these sections:

```markdown
## 🔖 Escopo

<!-- Descreva em detalhes o escopo das alterações, o problema que está sendo resolvido e como foi resolvido. Se aplicável, vincule o ticket relacionado. -->

## 🚩 Known issues

<!-- Liste quaisquer problemas conhecidos ou limitações introduzidas por esta alteração. Se não houver nenhum, escreva "N/A". -->

## 📁 Evidências

<!-- Prints, logs ou vídeos -->

## Roteiro de testes: Caminho feliz

<!-- Descreva brevemente o propósito e objetivo desse roteiro -->

### Critério(s) de aceitação

<!-- Liste todos os critérios que devem ser atingidos ao cumprir o roteiro de testes -->

## 💥 Pontos de impacto

<!-- Quais partes do sistema podem ter sido afetadas? -->
```

- **Escopo**: summary of the changes, based on the diff from step 4.
- **Known issues**: known problems, or "N/A".
- **Evidências**: placeholder for screenshots/videos.
- **Roteiro de testes**: test steps derived from the changes.
- **Pontos de impacto**: affected areas of the system.

Write the title and body in Brazilian Portuguese regardless of the language the user is writing in — the template sections above are the exact wording to reuse, not a translation source.

## 6. Confirmation

Show the title and body preview, and **ask the user to confirm before running `gh pr create`**.

## 7. Create the PR

Always as draft, no labels:

```bash
gh pr create --draft --base <branch> --title "..." --body "..." \
  --assignee @me \
  --reviewer matheusbusarellopx,AugustoBendlin,AbraoDaniel,lexdmm,tchiteu
```

## Report

Return the URL of the created PR.
