# automations

Agendador local de jobs (launchd + `peve-auto.py`). Conceitos do Hermes Agent (cron jobs) e do Orca (automations).

## Job

`jobs/<nome>/prompt.md`: frontmatter = config, corpo = prompt (modo `agent`).

| campo | padrão | descrição |
|---|---|---|
| `enabled` | `false` | testar com `run` antes de ligar |
| `mode` | `agent` | `agent` (roda `agent_cmd` com o prompt) · `script` (roda `script`, zero tokens) |
| `schedule` | `daily` | `hourly` · `daily` · `weekdays` · `weekly` · `"every 30m"` · cron `"0 22 * * *"` · `"at 2026-10-01 14:00"` (única) |
| `time` / `day` | `09:00` / `mon` | usados pelos presets |
| `script` | `run.sh` | relativo à pasta do job; respeita shebang se executável |
| `precheck` | — | comando shell; exit ≠ 0 → run `skipped` |
| `workdir` | raiz do repo | cwd do run; relativo à raiz do repo |
| `timeout_minutes` | `30` | mata o processo e seus filhos |
| `missed_run_grace_minutes` | `60` | atraso máximo aceito (Mac dormindo); fora disso → `missed` |
| `notify` | `on_failure` | `never` · `always` · `on_failure` (notificação macOS) |
| `agent_cmd` | `claude -p` | CLI do agente |

Execução única (`at ...`): roda assim que o horário passar (atraso aceito, salvo `missed_run_grace_minutes` explícito). Sucesso → pasta movida para `.state/archive/`. Falha ou perdida → job desligado + notificação.

Env vars em todo run: `PEVE_JOB`, `PEVE_RUN_ID`, `PEVE_RUN_LOG`, `PEVE_JOB_DIR`, `PEVE_REPO_ROOT`, `PEVE_TRIGGER`.

## CLI

```bash
automations/peve-auto.py new <job> [--mode agent|script] [--enabled] [--at "YYYY-MM-DD HH:MM" | --in 30m]
automations/peve-auto.py run <job>
automations/peve-auto.py enable|disable <job>|--all
automations/peve-auto.py list
automations/peve-auto.py watch [-n segundos]     # painel ao vivo; q sai, r atualiza
automations/peve-auto.py logs <job> [-n N]       # acompanha ao vivo se estiver rodando
automations/peve-auto.py runs <job> [-n N]
automations/peve-auto.py install | uninstall
```

Estado, histórico (`history.jsonl`) e logs (últimos 30 por job) em `.state/` (gitignored).
