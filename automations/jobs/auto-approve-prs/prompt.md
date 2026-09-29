---
enabled: true
mode: script
schedule: "*/30 8-17 * * 1-5"
timeout_minutes: 5
notify: on_failure
---

Approves open PRs in px-center/{px-mobile-painel, px-mobile-motorista, px-painel} via gh CLI. Approves without reviewing the code (includes dependabot, [HOTFIX] and [RELEASE]).

Rules:
- Skips my own PRs, drafts and PRs created before CUTOFF_DATE
- Skips PRs I already approved at the current commit
- Re-approves when a new commit lands after my approval

Overridable env: OWNER, REPOS, CUTOFF_DATE, CUTOFF_TIME_UTC, VERBOSE, SKIP_DRAFTS, SKIP_OWN_PRS, DRY_RUN.
Dry run: `DRY_RUN=true automations/cron.py run auto-approve-prs`

Log: APPR approved · REAPPR re-approved · SKIP skipped · DRY simulated · ERROR failure · CYCLE summary.
