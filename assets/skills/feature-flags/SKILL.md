---
name: feature-flags
description: Audits feature flags by querying the px database and optionally scanning the project codebase. Produces a markdown report categorized by status (expired, rolling out, needs cleanup, safe to delete, disabled, ghost). Use when user asks to audit feature flags, check feature flag status, or find flags to clean up.
allowed-tools:
  - Bash
  - AskUserQuestion
disable-model-invocation: true
---

# Feature Flags Audit

## Run

```bash
python3 ~/.claude/skills/feature-flags/audit.py [--port PORT] [--user USER] [--root PATH] [--mode full|db] [--out PATH]
```

- `--mode full` — DB + code scan (ghost detection, file references, local reference check)
- `--mode db` — DB only, faster, no codebase needed
- `--root` — project root for code scan (default: `.`)
- `--out` — output path (default: `/tmp/ff-report-<timestamp>.md`, no per-day collision)
- `--validate` — dry-run: runs queries and scans, prints stats, writes no report

**DB-only safety:** in `db` mode code references are NOT verified, so deletion categories are renamed to candidates (🔴 Fully Rolled Out, 💀 Disabled) and the report carries a warning banner. **Never delete based on a `db`-only run — confirm with `--mode full`.** Even in full mode, "not in this project" ≠ globally unused — flags may be referenced in other projects.

## Workflow

1. Ask the user which mode they want using `AskUserQuestion`:
   - **Full** — DB + code scan (detects ghost flags, shows file references per flag)
   - **DB only** — DB only, faster, no codebase required
2. Run the script with the chosen `--mode full` or `--mode db` (required, no interactive prompt)
3. Script prints the report path to stdout — **do not show the report to the user**; just confirm it was saved and tell them the path

## Categories

| Status                 | Condition (aggregated per flag name)                                         | Meaning                                                                                                     |
| ---------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| ⏰ Expired             | `max(expires_at)` < now                                                      | Past its intended lifetime. Still-enabled expired flags are the real danger — serving traffic silently      |
| 🚨 Stealth             | `any(is_enabled)=true` AND `max(percentage)=0` AND `type≠kill_switch`        | At least one entity enabled but nobody served. Kill switches excluded (0% = armed, not broken)              |
| 🟢 Rolling Out         | `any(is_enabled)=true` AND `0 < max(percentage) < 100`, or armed kill switch | Active rollout — expected state, monitor progress                                                           |
| 🟡 Needs Cleanup       | `any(is_enabled)=true` AND `max(percentage)=100` AND in this codebase        | Fully live for everyone but code still branches on it — remove the conditional                              |
| 🔴 Not in This Project | `any(is_enabled)=true` AND `max(percentage)=100` AND NOT in this codebase    | Fully live, no references here. May be used in other projects — cross-project check before deleting from DB |
| ⚫ Disabled — In Code  | `all(is_enabled)=false` AND in this codebase                                 | Off but code still branches on it — remove dead branch first, then delete from DB                           |
| 💀 Disabled — Not Here | `all(is_enabled)=false` AND NOT in this codebase                             | Off and no references here. May be used in other projects — cross-project check before deleting from DB     |
| ⚠️ Ghost               | in code AND NOT in DB                                                        | Flag checked in code but missing from DB — always evaluates to false, remove the check                      |

A `⚠️ inspect` note (and a `min–max%` percentage range) marks flags whose entities have mixed percentage/enabled values — the per-flag verdict aggregates over non-uniform rows, so verify manually before acting.

## Config

Copy `.env.example` to `.env` in the skill dir to override defaults:

```
FF_DB_PORT=63514
FF_DB_USER=YOUR_DB_USER
FF_DB_NAME=postgres
```

**DB auth:** script runs `psql --no-password` — relies on trusted local auth or a `~/.pgpass` entry (`localhost:PORT:DBNAME:USER:PASSWORD`). No prompt; if auth is absent the run fails fast with a psql connection error.
