---
enabled: false
mode: script
schedule: "every 30m"
timeout_minutes: 5
notify: on_failure
---

Aprova PRs abertos de px-center/{px-mobile-painel, px-mobile-motorista, px-painel} via gh CLI. Aprova sem revisar o código (inclui dependabot, [HOTFIX] e [RELEASE]).

Regras:
- Ignora PRs próprios, drafts e criados antes de CUTOFF_DATE
- Ignora PRs já aprovados por mim no commit atual
- Reaprova se entrou commit novo depois da aprovação

Env sobrescrevíveis: OWNER, REPOS, CUTOFF_DATE, CUTOFF_TIME_UTC, VERBOSE, SKIP_DRAFTS, SKIP_OWN_PRS, DRY_RUN.
Simular: `DRY_RUN=true automations/peve-auto.py run auto-approve-prs`

Log: APPR aprovado · REAPPR reaprovado · SKIP ignorado · DRY simulado · ERRO falha · CICLO resumo.
