# automations

Local job scheduler (launchd + `cron.py`). Concepts borrowed from Hermes Agent (cron jobs) and Orca (automations).

## Job

`jobs/<name>/prompt.md`: frontmatter = config, body = prompt (`agent` mode).

| field | default | description |
|---|---|---|
| `enabled` | `false` | test with `run` before enabling |
| `mode` | `agent` | `agent` (runs `agent_cmd` with the prompt) · `script` (runs `script`, zero tokens) |
| `schedule` | `daily` | `hourly` · `daily` · `weekdays` · `weekly` · `"every 30m"` · cron `"0 22 * * *"` · `"at 2026-10-01 14:00"` (one-shot) |
| `time` / `day` | `09:00` / `mon` | used by presets |
| `script` | `run.sh` | relative to the job folder; honors shebang when executable |
| `precheck` | — | shell command; exit ≠ 0 → run `skipped` |
| `workdir` | repo root | run cwd; relative to repo root |
| `timeout_minutes` | `30` | kills the process and its children |
| `missed_run_grace_minutes` | `60` | max accepted delay (Mac asleep); beyond it → `missed` |
| `notify` | `on_failure` | `never` · `always` · `on_failure` (macOS notification) |
| `agent_cmd` | `claude -p` | agent CLI |

One-shot (`at ...`): runs once the time passes (late runs accepted unless `missed_run_grace_minutes` is set). Success → folder moved to `.state/archive/`. Failure or missed → job disabled + notification.

Changing a job's schedule never triggers a catch-up run; the next slot is used.

Env vars on every run: `PEVE_JOB`, `PEVE_RUN_ID`, `PEVE_RUN_LOG`, `PEVE_JOB_DIR`, `PEVE_REPO_ROOT`, `PEVE_TRIGGER`.

## Control panel

`automations/cron.py` with no arguments opens the control panel. Every confirmation: `enter` confirms, `esc` cancels.

| key | action |
|---|---|
| `↑↓` / `jk` | navigate jobs |
| `space` → `enter` | mark and apply enable/disable |
| `x` | run selected job now |
| `l` | latest run log (live while running; `↑↓` scrolls, `g` end, `esc` back) |
| `e` | edit `prompt.md` (`$VISUAL`/`$EDITOR`, else `zed`) |
| `c` | clear recent runs |
| `a` | install/remove the scheduler |
| `q` | quit |

## CLI

```bash
automations/cron.py new <job> [--mode agent|script] [--enabled] [--at "YYYY-MM-DD HH:MM" | --in 30m]
automations/cron.py run <job>
automations/cron.py enable|disable <job>|--all
automations/cron.py list
automations/cron.py logs <job> [-n N]
automations/cron.py runs <job> [-n N]
automations/cron.py install | uninstall
```

Code: `cron.py` (entry point) + `cronlib/` (`schedule`, `jobs`, `state`, `runner`, `render`, `tui`).

State, history (`history.jsonl`) and logs (last 30 per job) live in `.state/` (gitignored).
