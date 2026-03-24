#!/usr/bin/env python3
"""
DB Operator - Safe PostgreSQL query executor for Claude Code

Enforces safety rules for PostgreSQL:
- WHERE clause validation for UPDATE/DELETE
- Dry run preview showing affected rows
- Explicit confirmation before write operations
- Auto-detects Docker when psql not in PATH
- Compact output: table format (≤12 cols) or key:value (>12 cols, nulls skipped)
"""

import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path



# ── Config ────────────────────────────────────────────────────────────────────

def find_config():
    session_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if session_dir:
        for candidate in [
            Path(session_dir) / ".claude" / "db-settings.json",
            Path(session_dir) / ".db-operator" / "settings.json",
        ]:
            if candidate.exists():
                return candidate
    for parent in [Path.cwd(), *Path.cwd().parents]:
        for candidate in [parent / ".claude" / "db-settings.json", parent / ".db-operator" / "settings.json"]:
            if candidate.exists():
                return candidate
    fallback = Path.home() / ".claude" / "skills" / "db-executor" / "settings.json"
    return fallback if fallback.exists() else None


def get_db(config, name=None):
    bases = config.get("bases", [])
    if not bases:
        raise ValueError("No databases in settings.json")
    if name:
        match = next((b for b in bases if b["name"] == name), None)
        if not match:
            raise ValueError(f"DB '{name}' not found in settings.json")
        return match
    return bases[0]


# ── Runner detection ──────────────────────────────────────────────────────────

def detect_runner(db_config):
    """Returns ("native", None) | ("docker", container_name) | (None, None)"""
    explicit = db_config.get("docker_container")
    if explicit:
        return "docker", explicit

    if shutil.which("psql"):
        return "native", None

    # Fallback: find a running postgres Docker container
    try:
        r = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                name, _, image = line.partition("\t")
                if "postgres" in image.lower() or "pgsql" in name.lower():
                    return "docker", name
    except Exception:
        pass

    return None, None


# ── Command builder ───────────────────────────────────────────────────────────

def build_args(db_config, runner, container, extra_flags=(), query=None):
    cfg = db_config.get("config", {})
    env = os.environ.copy()

    if runner == "docker":
        pwd = str(cfg.get("password", ""))
        args = ["docker", "exec"]
        if pwd:
            args += ["-e", f"PGPASSWORD={pwd}"]
        args += [container, "psql"]
        if "user" in cfg:
            args += ["-U", str(cfg["user"])]
        if "database" in cfg:
            args += ["-d", str(cfg["database"])]
    else:
        if "password" in cfg:
            env["PGPASSWORD"] = str(cfg["password"])
        args = ["psql"]
        for flag, key in [("-h", "host"), ("-p", "port"), ("-U", "user"), ("-d", "database")]:
            if key in cfg:
                args += [flag, str(cfg[key])]
        args += ["--connect-timeout", "10"]

    args += list(extra_flags)
    if query:
        args += ["-c", query]
    return args, env


def run_sql(db_config, runner, container, query, csv_mode=False, timeout_ms=60000):
    if runner is None:
        return (
            "",
            "psql not found and no Docker postgres container detected.\n"
            "Install psql: brew install libpq\n"
            "Or ensure a postgres Docker container is running.",
            1,
        )
    extra = ("--csv",) if csv_mode else ()
    args, env = build_args(db_config, runner, container, extra_flags=extra, query=query)
    try:
        r = subprocess.run(
            args, env=env, capture_output=True, text=True,
            timeout=(timeout_ms / 1000) + 10,
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "Query timed out", 1
    except FileNotFoundError as e:
        return "", f"Command not found: {e}", 1


# ── Output formatting (token-efficient) ───────────────────────────────────────

def fmt_csv(csv_text):
    """Return CSV output directly — minimal tokens, fully readable by AI."""
    if not csv_text.strip():
        return "(no rows)"

    rows = list(csv.reader(io.StringIO(csv_text.strip())))
    if len(rows) <= 1:
        return "(0 rows)"

    n = len(rows) - 1  # exclude header row
    return csv_text.strip() + f"\n({n} row{'s' if n != 1 else ''})"


# ── Safety ────────────────────────────────────────────────────────────────────

def is_write(query):
    return bool(re.match(r"^\s*(UPDATE|DELETE)\s+", query, re.IGNORECASE))


def has_where(query):
    clean = re.sub(r"'[^']*'", "''", query)
    clean = re.sub(r'"[^"]*"', '""', clean)
    return bool(re.search(r"\bWHERE\b", clean, re.IGNORECASE))


def extract_table_where(query):
    q = query.strip().rstrip(";")
    m = re.match(r"UPDATE\s+(\S+)\s+SET\s+.+?\s+WHERE\s+(.+)$", q, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"DELETE\s+FROM\s+(\S+)\s+WHERE\s+(.+)$", q, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    return None, None


# ── Special SQL queries (replaces psql meta-commands) ────────────────────────

LIST_TABLES_SQL = (
    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
)


def inspect_sql(table):
    t = table.replace("'", "''")
    return (
        f"SELECT column_name, data_type, character_maximum_length AS max_len,"
        f" is_nullable, column_default"
        f" FROM information_schema.columns"
        f" WHERE table_schema='public' AND table_name='{t}'"
        f" ORDER BY ordinal_position;"
    )


def search_table_sql(pattern):
    p = pattern.replace("'", "''")
    return (
        f"SELECT tablename FROM pg_tables"
        f" WHERE schemaname='public' AND tablename ILIKE '%{p}%'"
        f" ORDER BY tablename;"
    )


def suggest_similar_tables(db_config, runner, container, table_name):
    """Try to find similarly-named tables when relation doesn't exist."""
    out, _, rc = run_sql(db_config, runner, container, search_table_sql(table_name), csv_mode=True)
    if rc == 0 and out.strip():
        rows = list(csv.reader(io.StringIO(out.strip())))
        names = [r[0] for r in rows[1:] if r]
        if names:
            print(f"\nDid you mean one of these tables?", file=sys.stderr)
            for name in names:
                print(f"  {name}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse

    p = argparse.ArgumentParser(description="DB Operator - Safe PostgreSQL executor")
    p.add_argument("query", nargs="?", help="SQL query to execute")
    p.add_argument("--db", help="Database name from settings.json")
    p.add_argument("--config", help="Path to settings.json")
    p.add_argument("--config-path", action="store_true", help="Print resolved config path and exit")
    p.add_argument("--yes", "-y", action="store_true", help="Auto-confirm writes")
    p.add_argument("--list-tables", action="store_true", help="List all tables")
    p.add_argument("--inspect", metavar="TABLE", help="Show schema for TABLE")
    p.add_argument("--search-table", metavar="PATTERN", help="Search tables matching PATTERN")
    args = p.parse_args()

    # Resolve config
    config_path = Path(args.config) if args.config else find_config()
    if not config_path or not config_path.exists():
        print(
            "ERROR: db-settings.json not found.\n"
            "Create .claude/db-settings.json no diretório onde iniciou a sessão ($CLAUDE_PROJECT_DIR).\n"
            "See ~/.claude/skills/db-executor/settings.example.json for format.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.config_path:
        print(str(config_path.resolve()))
        sys.exit(0)

    config = json.loads(config_path.read_text())
    db = get_db(config, args.db)
    settings = config.get("settings", {})
    timeout_ms = settings.get("transaction_timeout_ms", 60000)
    max_rows = settings.get("max_rows_preview", 10)

    runner, container = detect_runner(db)
    mode_label = f"docker:{container}" if runner == "docker" else "native"

    # ── Inspection commands ──────────────────────────────────────────────────

    if args.list_tables:
        out, err, rc = run_sql(db, runner, container, LIST_TABLES_SQL, csv_mode=True)
        print(fmt_csv(out) if rc == 0 else err, file=sys.stderr if rc != 0 else sys.stdout)
        sys.exit(rc)

    if args.search_table:
        out, err, rc = run_sql(db, runner, container, search_table_sql(args.search_table), csv_mode=True)
        print(fmt_csv(out) if rc == 0 else err, file=sys.stderr if rc != 0 else sys.stdout)
        sys.exit(rc)

    if args.inspect:
        out, err, rc = run_sql(db, runner, container, inspect_sql(args.inspect), csv_mode=True)
        print(fmt_csv(out) if rc == 0 else err, file=sys.stderr if rc != 0 else sys.stdout)
        sys.exit(rc)

    # ── Query ────────────────────────────────────────────────────────────────

    query = args.query or sys.stdin.read().strip()
    if not query:
        print("ERROR: No query provided.", file=sys.stderr)
        sys.exit(1)

    # Write safety gate
    if is_write(query):
        if db.get("read_only"):
            print(f"ERROR: DB '{db['name']}' is read-only.", file=sys.stderr)
            sys.exit(1)

        if not has_where(query):
            print(
                "SAFETY BLOCK: UPDATE/DELETE without WHERE is not allowed.\n"
                "Use WHERE 1=1 if you truly want to affect all rows.",
                file=sys.stderr,
            )
            sys.exit(2)

        print(f"[db-operator] db={db['name']} runner={mode_label}")
        print(f"[db-operator] op={query[:120]}{'...' if len(query) > 120 else ''}\n")
        print("Dry run preview:")

        table, where = extract_table_where(query)
        if table:
            cnt_out, cnt_err, cnt_rc = run_sql(
                db, runner, container,
                f"SELECT COUNT(*) AS affected FROM {table} WHERE {where};",
                csv_mode=True,
            )
            prv_out, _, _ = run_sql(
                db, runner, container,
                f"SELECT * FROM {table} WHERE {where} LIMIT {max_rows};",
                csv_mode=True,
            )
            if cnt_rc == 0:
                print(fmt_csv(cnt_out))
                print(fmt_csv(prv_out))
            else:
                print(f"Dry run failed: {cnt_err}", file=sys.stderr)

        if not args.yes:
            print("\nPara confirmar, digite exatamente 'yes': ", end="", flush=True)
            try:
                if input().strip() != "yes":
                    print("Cancelado. Você deve digitar 'yes' por extenso para confirmar.")
                    sys.exit(0)
            except (EOFError, KeyboardInterrupt):
                print("\nCancelado.")
                sys.exit(0)

    # Execute
    use_csv = not is_write(query)
    out, err, rc = run_sql(db, runner, container, query, csv_mode=use_csv, timeout_ms=timeout_ms)

    if rc == 0:
        print(fmt_csv(out) if use_csv else out)
    else:
        print(err, file=sys.stderr)
        # Auto-suggest similar tables on "relation does not exist"
        m = re.search(r'relation "([^"]+)" does not exist', err)
        if m:
            suggest_similar_tables(db, runner, container, m.group(1))

    sys.exit(rc)


if __name__ == "__main__":
    main()
