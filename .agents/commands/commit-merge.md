---
description: Faz pull, gera commit semântico, merge na main e push
---

# commit-merge

Execute o fluxo completo de commit e merge na branch main:

## Passos

### 1. Verificar estado atual
- Execute `git status` e `git branch --show-current` para entender o estado do repositório
- Anote a branch atual — será usada após o merge
- Se já estiver na `main`, pule os passos 4 e 6 (não há merge nem volta de branch) e execute apenas commit + push

### 2. Pull da branch atual
- Execute `git pull` na branch atual para sincronizar com o remoto
- Se houver conflitos, reporte ao usuário e interrompa

### 3. Gerar commit semântico
- Execute `git diff --staged` e `git status` para ver o que está pendente
- Se não houver mudanças staged, execute `git diff` para ver mudanças não staged
- Se não houver nenhuma mudança, informe o usuário e pule para o passo 4
- Analise as mudanças e gere um commit seguindo Conventional Commits:
  - Formato: `<type>(<scope>): <description>`
  - Types: `feat`, `fix`, `refactor`, `style`, `docs`, `test`, `chore`, `perf`
  - Scope: nome do módulo/arquivo principal afetado (opcional)
  - Description: imperativo, sem ponto final, em inglês ou português conforme o projeto
  - Se houver mudanças não staged, execute `git add` nos arquivos relevantes antes
- Execute o commit com a mensagem gerada
- Se o commit falhar (ex: pre-commit hook), corrija o problema e tente novamente

### 4. Merge na main
- Execute `git checkout main`
- Execute `git pull origin main` para garantir que main está atualizada
- Execute `git merge <branch-original> --no-ff -m "merge: <branch-original> into main"`
- Se houver conflitos, reporte detalhadamente ao usuário e interrompa

### 5. Push
- Execute `git push origin main`
- Se o push for rejeitado, verifique o motivo e reporte ao usuário

### 6. Voltar à branch original
- Execute `git checkout <branch-original>`
- Informe o usuário que o fluxo foi concluído com sucesso

## Regras
- Nunca use `--force` ou `--no-verify` sem permissão explícita do usuário
- Sempre reporte cada passo antes de executá-lo
- Em caso de erro em qualquer passo, pare e explique o que aconteceu
