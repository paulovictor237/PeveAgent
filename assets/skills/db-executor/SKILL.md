---
name: db-executor
description: >
  Safe, context-aware PostgreSQL operator. Use whenever the user wants to query, inspect, update,
  delete, or insert data in a database — even if they phrase it as "check the DB", "run this SQL",
  "what's in the users table", "update this record", "remove these rows", or any request involving
  database data. This skill enforces a mandatory dry-run + confirmation flow for all write operations
  (UPDATE/DELETE), preventing accidental data loss. Always use this skill for DB interactions, even
  for seemingly simple queries — the safety workflow is non-negotiable.
---

# SQL Operator

You are operating as a safe, deliberate database operator. Your job is to help the user query and
modify PostgreSQL databases without ever causing accidental data loss.

## Setup (first time in a project)

Before running any query, check if `.claude/db-settings.json` exists in the project root.

If it doesn't exist:
1. Show the user the example format from `~/.claude/skills/db-executor/settings.example.json`
2. Ask them to create `.claude/db-settings.json` with their credentials
3. Remind them to add `.claude/db-settings.json` to `.gitignore` so passwords don't leak

Config search order:
- `$CLAUDE_PROJECT_DIR/.claude/db-settings.json` (session start dir — preferred)
- `.claude/db-settings.json` walking up from cwd (project fallback)
- `~/.claude/skills/db-executor/settings.json` (user-level fallback)

## The executor script

All database interaction goes through:
```
python ~/.claude/skills/db-executor/scripts/db_tool.py [OPTIONS] [QUERY]
```

**psql not required.** When `psql` is not installed, the script auto-detects a running Docker
postgres container and uses `docker exec` as a fallback. You can also set `"docker_container"`
in settings.json to force a specific container.

### Key flags

| Flag | Purpose |
|------|---------|
| `--db <name>` | Select database from settings.json (defaults to first) |
| `--list-tables` | List all tables in the public schema |
| `--search-table <pattern>` | Find tables matching a partial name (e.g. `freight`) |
| `--inspect <table>` | Show column names, types, and constraints for TABLE |
| `--yes` / `-y` | Skip confirmation prompt (scripted/safe contexts only) |
| `--config <path>` | Override path to settings.json |

## Workflow: before writing a query

Use `--search-table` when the exact table name is uncertain — it's faster than `--list-tables`:

```bash
python ~/.claude/skills/db-executor/scripts/db_tool.py --search-table freight
```

Inspect schema before writing queries with column names:

```bash
python ~/.claude/skills/db-executor/scripts/db_tool.py --inspect freights
```

## Running SELECT queries

```bash
python ~/.claude/skills/db-executor/scripts/db_tool.py "SELECT * FROM freights WHERE id = 123;"
```

**Output is CSV format for maximum token efficiency** — headers on first line, values comma-separated, row count appended.

If the query fails with `relation "X" does not exist`, the script automatically searches for
similar table names and prints suggestions — no manual `--list-tables` needed.

## Running UPDATE or DELETE (mandatory safety flow)

The script enforces this flow automatically:

**Step 1 — WHERE clause check**: Rejects any UPDATE/DELETE without WHERE.

**Step 2 — Dry run preview**: Runs a SELECT COUNT and SELECT preview to show how many rows
will be affected and what they look like (also formatted compactly).

**Step 3 — Explicit confirmation**: Asks the user to type `yes` in full to confirm. Any other response cancels the operation.

**Step 4 — Execution**: Only runs after confirmation.

```bash
python ~/.claude/skills/db-executor/scripts/db_tool.py \
  "UPDATE users SET active = false WHERE last_login < '2024-01-01';"
```

## Read-only databases

If a database has `"read_only": true` in settings.json, write operations are blocked entirely.

## Multiple databases

```bash
python ~/.claude/skills/db-executor/scripts/db_tool.py --db postgresql-prod "SELECT ..."
```

## Things to keep in mind

- Prefer `--search-table <partial>` over `--list-tables` when looking for a specific table.
- If the dry run shows more rows than expected, ask the user to refine the WHERE clause.
- Always add `LIMIT` to SELECT queries on large tables unless the user needs all rows.
- If the user asks for something destructive without clear intent, confirm before constructing the query.
