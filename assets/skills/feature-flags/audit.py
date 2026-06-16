#!/usr/bin/env python3
import argparse
import csv
import datetime
import fnmatch
import io
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field


def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

SCAN_DIRS = [
    "app",
    "resources/js",
    "src",
    "px-painel/app",
    "px-painel/src",
    "px-mobile-motorista/src",
]
SCAN_EXTENSIONS = ["*.php", "*.ts", "*.tsx"]
TYPE_DEF_FILES = {"useFeatureFlag.ts", "useBackendFeatureFlag.ts"}


@dataclass
class FlagRow:
    name: str
    entity_count: int
    max_pct: int
    min_pct: int
    any_enabled: bool
    all_enabled: bool
    max_expires: str
    first_created: str
    squad: str
    types: list[str]

    @property
    def has_kill_switch(self):
        return "kill_switch" in self.types

    @property
    def mixed(self):
        return self.min_pct != self.max_pct or self.any_enabled != self.all_enabled


def format_date(date_str, now=None):
    if not date_str:
        return "\u2014"
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str)
    if match:
        year, month, day = match.groups()
        formatted = f"{day}/{month}/{year}"
        if now:
            try:
                dt = datetime.date(int(year), int(month), int(day))
                diff = (now.date() - dt).days
                if diff > 0:
                    formatted += f" ({chr(0x2212)}{diff}d)"
                elif diff < 0:
                    formatted += f" (+{-diff}d)"
                else:
                    formatted += " (now)"
            except (ValueError, OverflowError):
                pass
        return formatted
    return date_str


_BAD_DATES = set()


def format_date_warn(date_str, now=None):
    result = format_date(date_str, now)
    if result == date_str and date_str and date_str != "\u2014" and date_str not in _BAD_DATES:
        _BAD_DATES.add(date_str)
        print(f"WARNING: unparseable date '{date_str}', using raw value", file=sys.stderr)
    return result


def parse_expiry(expires_str, now):
    if not expires_str:
        return False
    try:
        dt = datetime.datetime.fromisoformat(expires_str)
    except (ValueError, TypeError):
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt < now.astimezone(datetime.timezone.utc)


class DatabaseClient:
    SQL = """
        SELECT
            name,
            COUNT(*)                                  AS entity_count,
            MAX(percentage)                           AS max_pct,
            MIN(percentage)                           AS min_pct,
            bool_or(is_enabled)::text                 AS any_enabled,
            bool_and(is_enabled)::text                AS all_enabled,
            COALESCE(MAX(expires_at)::text, '')       AS max_expires,
            MIN(created_at)::date::text               AS first_created,
            COALESCE(MAX(squad), '')                  AS squad,
            STRING_AGG(DISTINCT type, '\x1f' ORDER BY type) AS types
        FROM feature_flags
        GROUP BY name
        ORDER BY first_created, name
    """

    def __init__(self, port, user, dbname=None):
        self.port = port
        self.user = user
        self.dbname = dbname or os.environ.get("FF_DB_NAME", "postgres")

    def fetch(self):
        result = subprocess.run(
            [
                "psql",
                "-h", "localhost",
                "-p", str(self.port),
                "-U", self.user,
                "-d", self.dbname,
                "--no-password",
                "--csv",
                "-t",
                "-c", self.SQL,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"DB error: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        reader = csv.DictReader(io.StringIO(result.stdout), fieldnames=[
            "name", "entity_count", "max_pct", "min_pct",
            "any_enabled", "all_enabled", "max_expires",
            "first_created", "squad", "types",
        ])
        rows = []
        for row in reader:
            if not row["name"]:
                continue
            try:
                entity_count = int(row["entity_count"])
                max_pct = int(row["max_pct"]) if row["max_pct"] else 0
                min_pct = int(row["min_pct"]) if row["min_pct"] else 0
            except (ValueError, TypeError):
                print(f"WARNING: bad row for '{row['name']}', skipping", file=sys.stderr)
                continue

            if entity_count < 0:
                print(f"WARNING: negative entity_count for '{row['name']}', skipping", file=sys.stderr)
                continue
            if not (0 <= max_pct <= 100) or not (0 <= min_pct <= 100):
                print(f"WARNING: percentage out of range for '{row['name']}', skipping", file=sys.stderr)
                continue

            types_raw = row.get("types", "")
            parsed_types = []
            if types_raw:
                parsed_types = [t.strip() for t in types_raw.split("\x1f") if t.strip()]

            rows.append(FlagRow(
                name=row["name"],
                entity_count=entity_count,
                max_pct=max_pct,
                min_pct=min_pct,
                any_enabled=row["any_enabled"] == "true",
                all_enabled=row["all_enabled"] == "true",
                max_expires=row.get("max_expires", ""),
                first_created=row.get("first_created", ""),
                squad=row.get("squad", "") or "(no squad)",
                types=parsed_types,
            ))
        return rows


_AUTHOR_RE = re.compile(r"^.* <.*>$")

class CodebaseScanner:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self._git_root_cache = {}
        self._author_cache = {}
        self._authors_built = False
        self._tracked_files = set()

    @property
    def scan_dirs(self):
        return [
            os.path.join(self.root, d)
            for d in SCAN_DIRS
            if os.path.isdir(os.path.join(self.root, d))
        ]

    def _walk_files(self, extensions):
        for d in self.scan_dirs:
            for r, _, files in os.walk(d, followlinks=True):
                for fname in files:
                    if any(fnmatch.fnmatch(fname, ext) for ext in extensions):
                        yield os.path.join(r, fname)

    def _read_file(self, path):
        try:
            with open(path, "r", errors="ignore") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            print(f"WARNING: cannot read '{path}', skipping", file=sys.stderr)
            return ""

    def extract_type_def_names(self):
        names = set()
        for filepath in self._walk_files(SCAN_EXTENSIONS):
            if os.path.basename(filepath) not in TYPE_DEF_FILES:
                continue
            content = self._read_file(filepath)
            for match in re.finditer(r"^\s*\|\s*['\"]([a-zA-Z0-9_-]+)['\"]", content, re.MULTILINE):
                names.add(match.group(1))
        return names

    def build_references(self, flag_names):
        self._tracked_files = set()
        index = defaultdict(list)
        pattern_cache = {}
        for name in flag_names:
            pattern_cache[name] = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)")

        for filepath in self._walk_files(SCAN_EXTENSIONS):
            self._tracked_files.add(os.path.realpath(filepath))
            content = self._read_file(filepath)
            if not content:
                continue
            for name, pattern in pattern_cache.items():
                if pattern.search(content):
                    index[name].append(filepath)
        return dict(index)

    def _git_root(self, file_path):
        d = os.path.dirname(os.path.abspath(file_path))
        if d in self._git_root_cache:
            return self._git_root_cache[d]
        result = subprocess.run(
            ["git", "-C", d, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
        )
        root = result.stdout.strip() if result.returncode == 0 else None
        self._git_root_cache[d] = root
        return root

    def _build_authors(self):
        self._author_cache = defaultdict(lambda: defaultdict(int))
        files_by_root = defaultdict(list)
        for abs_f in self._tracked_files:
            repo_root = self._git_root(abs_f)
            if not repo_root:
                continue
            try:
                rel_f = os.path.relpath(abs_f, repo_root)
            except ValueError:
                continue
            files_by_root[repo_root].append(rel_f)

        for repo_root, rel_files in files_by_root.items():
            result = subprocess.run(
                ["git", "-C", repo_root, "log", "--format=%an <%ae>",
                 "--name-only", "--diff-filter=AM", "--"] + rel_files,
                capture_output=True, text=True,
            )
            current_author = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if _AUTHOR_RE.match(line):
                    current_author = line
                elif current_author:
                    abs_f = os.path.realpath(os.path.join(repo_root, line))
                    self._author_cache[abs_f][current_author] += 1
        self._authors_built = True

    def file_authors(self, abs_f):
        if not self._authors_built:
            self._build_authors()
        abs_f = os.path.realpath(abs_f)
        return self._author_cache.get(abs_f, {})

    def top_owner(self, files):
        counts = defaultdict(int)
        for f in files:
            for author, n in self.file_authors(os.path.abspath(f)).items():
                counts[author] += n
        if not counts:
            return "\u2014"
        return max(counts, key=counts.get)

    def file_list(self, files):
        if not files:
            return "\u2014"
        shown = files[:5]
        rest = len(files) - 5
        result = ", ".join(os.path.relpath(f, self.root) for f in shown)
        if rest > 0:
            result += f", +{rest} more"
        return result


def categorize(rows, code_scan_results, now, mode):
    cats = {
        "expired": [],
        "stealth": [],
        "rolling_out": [],
        "needs_cleanup": [],
        "safe_to_delete": [],
        "disabled_in_code": [],
        "disabled_gone": [],
    }
    code_known = mode == "full"

    for row in rows:
        files = code_scan_results.get(row.name, [])
        expires = row.max_expires
        if parse_expiry(expires, now):
            cats["expired"].append((row, files))
            continue

        enabled = row.any_enabled
        pct = row.max_pct
        in_code = bool(files)

        if enabled and pct == 0 and row.has_kill_switch:
            cats["rolling_out"].append((row, files))
        elif enabled and pct == 0:
            cats["stealth"].append((row, files))
        elif enabled and 0 < pct < 100:
            cats["rolling_out"].append((row, files))
        elif enabled and pct == 100 and code_known and in_code:
            cats["needs_cleanup"].append((row, files))
        elif enabled and pct == 100:
            cats["safe_to_delete"].append((row, files))
        elif not enabled and code_known and in_code:
            cats["disabled_in_code"].append((row, files))
        elif not enabled:
            cats["disabled_gone"].append((row, files))

    cats["expired"].sort(key=lambda rf: rf[0].max_expires)
    cats["stealth"].sort(key=lambda rf: rf[0].first_created)
    cats["rolling_out"].sort(key=lambda rf: -rf[0].max_pct)
    cats["needs_cleanup"].sort(key=lambda rf: rf[0].first_created)
    cats["safe_to_delete"].sort(key=lambda rf: rf[0].first_created)
    cats["disabled_in_code"].sort(key=lambda rf: rf[0].first_created)
    cats["disabled_gone"].sort(key=lambda rf: rf[0].first_created)

    return cats


class ReportRenderer:
    def __init__(self, scanner, port, generated_at, now, mode):
        self.scanner = scanner
        self.port = port
        self.generated_at = generated_at
        self.now = now
        self.mode = mode

    def render(self, cats, ghosts):
        full = self.mode == "full"
        total = sum(len(v) for v in cats.values()) + len(ghosts)

        delete_title = "\U0001f534 Not in This Project" if full else "\U0001f534 Fully Rolled Out (100%)"
        gone_title = "\U0001f480 Disabled \u2014 Not Here" if full else "\U0001f480 Disabled"

        summary_rows = [
            ["\u23f0 Expired", len(cats["expired"])],
            ["\U0001f6a8 Stealth (0%, enabled)", len(cats["stealth"])],
            ["\U0001f7e2 Rolling Out", len(cats["rolling_out"])],
        ]
        if full:
            summary_rows.append(["\U0001f7e1 Needs Code Cleanup", len(cats["needs_cleanup"])])
        summary_rows.append([delete_title, len(cats["safe_to_delete"])])
        if full:
            summary_rows.append(["\u26ab Disabled \u2014 In Code", len(cats["disabled_in_code"])])
        summary_rows.append([gone_title, len(cats["disabled_gone"])])
        if full:
            summary_rows.append(["\u26a0\ufe0f Ghost (in code, not in DB)", len(ghosts)])
        summary_rows.append(["**Total**", f"**{total}**"])

        out = [
            f"# Feature Flags Audit \u2014 {self.now.strftime('%d/%m/%Y')}",
            "",
            f"Generated: {self.generated_at}  ",
            f"Database: px @ localhost:{self.port}  ",
            f"Mode: {'Full (DB + code scan)' if full else 'DB only'}",
        ]
        if not full:
            out += [
                "",
                "\u26a0\ufe0f **DB-only run \u2014 code references NOT verified.** "
                "\U0001f534 and \U0001f480 rows are *deletion candidates*, not confirmed-safe. "
                "A flag here may still be referenced in code. "
                "Re-run with `--mode full` before deleting anything.",
            ]
        out += ["", "## Summary", "", self._table(["Category", "Count"], summary_rows)]

        CATEGORY_DESC = self._category_descriptions()

        def section(title, rows_data, headers, row_fn):
            desc = CATEGORY_DESC.get(title, "")
            out.extend(["", f"## {title}", ""])
            if desc:
                out.extend(desc.splitlines() + [""])
            if rows_data:
                out.append(self._table(headers, [row_fn(r, f) for r, f in rows_data]))
            else:
                out.append("_None_")

        def enabled_cell(row):
            return "yes" if row.any_enabled else "no"

        def pct_cell(row):
            if row.min_pct != row.max_pct:
                return f"{row.min_pct}\u2013{row.max_pct}% \u26a0\ufe0f"
            return f"{row.max_pct}%"

        def mixed_note(row):
            return "\u26a0\ufe0f inspect" if row.mixed else ""

        if full:
            section(
                "\u23f0 Expired", cats["expired"],
                ["name", "squad", "enabled", "pct", "expires_at", "files_referencing", "owner", "first_created"],
                lambda r, f: [
                    r.name, r.squad, enabled_cell(r), pct_cell(r),
                    format_date_warn(r.max_expires, self.now), self.scanner.file_list(f),
                    self.scanner.top_owner(f) if f else "\u2014",
                    format_date_warn(r.first_created, self.now),
                ],
            )
        else:
            section(
                "\u23f0 Expired", cats["expired"],
                ["name", "squad", "enabled", "pct", "expires_at", "first_created"],
                lambda r, f: [
                    r.name, r.squad, enabled_cell(r), pct_cell(r),
                    format_date_warn(r.max_expires, self.now), format_date_warn(r.first_created, self.now),
                ],
            )

        section(
            "\U0001f6a8 Stealth (0%, enabled)", cats["stealth"],
            ["name", "squad", "entity_count", "type", "first_created"],
            lambda r, f: [
                r.name, r.squad, r.entity_count,
                ", ".join(r.types) if r.types else "\u2014",
                format_date_warn(r.first_created, self.now),
            ],
        )

        if full:
            section(
                "\U0001f7e2 Rolling Out", cats["rolling_out"],
                ["name", "squad", "percentage", "entity_count", "expires_at",
                 "first_created", "files_referencing", "owner"],
                lambda r, f: [
                    r.name, r.squad, pct_cell(r), r.entity_count,
                    format_date_warn(r.max_expires, self.now), format_date_warn(r.first_created, self.now),
                    self.scanner.file_list(f),
                    self.scanner.top_owner(f) if f else "\u2014",
                ],
            )
            section(
                "\U0001f7e1 Needs Code Cleanup", cats["needs_cleanup"],
                ["name", "squad", "entity_count", "files_referencing", "owner", "first_created"],
                lambda r, f: [
                    r.name, r.squad, r.entity_count,
                    self.scanner.file_list(f),
                    self.scanner.top_owner(f),
                    format_date_warn(r.first_created, self.now),
                ],
            )
        else:
            section(
                "\U0001f7e2 Rolling Out", cats["rolling_out"],
                ["name", "squad", "percentage", "entity_count", "expires_at", "first_created"],
                lambda r, f: [
                    r.name, r.squad, pct_cell(r), r.entity_count,
                    format_date_warn(r.max_expires, self.now), format_date_warn(r.first_created, self.now),
                ],
            )

        section(
            delete_title, cats["safe_to_delete"],
            ["name", "squad", "entity_count", "type", "note", "first_created"],
            lambda r, f: [
                r.name, r.squad, r.entity_count,
                ", ".join(r.types) if r.types else "\u2014",
                mixed_note(r),
                format_date_warn(r.first_created, self.now),
            ],
        )

        if full:
            section(
                "\u26ab Disabled \u2014 In Code", cats["disabled_in_code"],
                ["name", "squad", "percentage", "files_referencing", "owner", "first_created"],
                lambda r, f: [
                    r.name, r.squad, pct_cell(r),
                    self.scanner.file_list(f),
                    self.scanner.top_owner(f),
                    format_date_warn(r.first_created, self.now),
                ],
            )

        section(
            gone_title, cats["disabled_gone"],
            ["name", "squad", "percentage", "note", "first_created"],
            lambda r, f: [
                r.name, r.squad, pct_cell(r),
                mixed_note(r),
                format_date_warn(r.first_created, self.now),
            ],
        )

        if full:
            ghost_title = "\u26a0\ufe0f Ghost (in code, not in DB)"
            out.extend(["", f"## {ghost_title}", "", CATEGORY_DESC[ghost_title], ""])
            if ghosts:
                out.append(
                    self._table(
                        ["name", "files_referencing", "owner"],
                        [
                            [name, self.scanner.file_list(files), self.scanner.top_owner(files)]
                            for name, files in sorted(ghosts.items())
                        ],
                    )
                )
            else:
                out.append("_None_")

        squad_counts = self._build_squad_counts(cats)
        out.extend(["", "## \U0001f4ca By Squad", ""])
        if squad_counts:
            squad_rows = []
            for squad in sorted(squad_counts.keys()):
                c = squad_counts[squad]
                total_sq = sum(c.values())
                squad_rows.append([
                    squad,
                    c["rolling_out"], c["needs_cleanup"], c["safe_to_delete"],
                    c["disabled_in_code"], c["disabled_gone"],
                    c["expired"], c["stealth"], total_sq,
                ])
            out.append(
                self._table(
                    ["squad", "\U0001f7e2", "\U0001f7e1", "\U0001f534", "\u26ab", "\U0001f480", "\u23f0", "\U0001f6a8", "total"],
                    squad_rows,
                )
            )

        return "\n".join(out)

    def _category_descriptions(self):
        return {
            "\u23f0 Expired": "- expires at: past\n- files referencing: shown\n- owner: top git author across referencing files\n- sorted by: expiry date \u2191",
            "\U0001f6a8 Stealth (0%, enabled)": "- enabled: yes\n- rollout: 0%\n- type: not kill switch\n- sorted by: created date \u2191",
            "\U0001f7e2 Rolling Out": "- enabled: yes\n- rollout: 1\u201399% (or kill switch at 0%)\n- files referencing: shown\n- owner: top git author across referencing files\n- sorted by: rollout % \u2193",
            "\U0001f7e1 Needs Code Cleanup": "- enabled: yes\n- rollout: 100%\n- in code: yes\n- sorted by: created date \u2191",
            "\U0001f534 Not in This Project": "- enabled: yes\n- rollout: 100%\n- in code: no\n- sorted by: created date \u2191",
            "\U0001f534 Fully Rolled Out (100%)": "- enabled: yes\n- rollout: 100%\n- in code: unverified (db-only run)\n- sorted by: created date \u2191",
            "\u26ab Disabled \u2014 In Code": "- enabled: no\n- in code: yes\n- sorted by: created date \u2191",
            "\U0001f480 Disabled \u2014 Not Here": "- enabled: no\n- in code: no\n- sorted by: created date \u2191",
            "\U0001f480 Disabled": "- enabled: no\n- in code: unverified (db-only run)\n- sorted by: created date \u2191",
            "\u26a0\ufe0f Ghost (in code, not in DB)": "- in code: yes\n- in database: no\n- sorted by: name \u2191",
        }

    def _build_squad_counts(self, cats):
        squad_counts = defaultdict(lambda: defaultdict(int))
        for cat in ["rolling_out", "needs_cleanup", "safe_to_delete",
                     "disabled_in_code", "disabled_gone", "expired", "stealth"]:
            for row, _files in cats[cat]:
                squad_counts[row.squad][cat] += 1
        return squad_counts

    def _table(self, headers, rows_data):
        lines = [
            "| " + " | ".join(str(h) for h in headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows_data:
            lines.append("| " + " | ".join(str(v) for v in row) + " |")
        return "\n".join(lines)


def validate_inputs(args):
    errors = []
    if not (1 <= args.port <= 65535):
        errors.append(f"--port {args.port} out of valid range (1-65535)")
    if not os.path.isdir(args.root):
        errors.append(f"--root '{args.root}' does not exist or is not a directory")
    if shutil.which("psql") is None:
        errors.append("'psql' not found on PATH")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    _load_env()

    parser = argparse.ArgumentParser(description="Feature flags audit report")
    parser.add_argument("--port", type=int, default=int(os.environ.get("FF_DB_PORT", 63514)))
    parser.add_argument("--user", default=os.environ.get("FF_DB_USER", "paulovictor237"))
    parser.add_argument("--root", default=".")
    parser.add_argument("--mode", choices=["full", "db"], default=None,
                        help="full=DB+code scan, db=DB only (required)")
    parser.add_argument("--out", default=None,
                        help="output path (default: /tmp/ff-report-<timestamp>.md)")
    parser.add_argument("--validate", action="store_true",
                        help="dry-run: run all queries and scans, print stats to stderr, no report file")
    args = parser.parse_args()

    validate_inputs(args)

    if not args.mode:
        print("ERROR: --mode is required (full or db)", file=sys.stderr)
        sys.exit(1)
    mode = args.mode

    root = os.path.abspath(args.root)
    now = datetime.datetime.now()
    generated_at = now.isoformat(timespec="seconds")

    print("Querying database...", file=sys.stderr)
    db = DatabaseClient(args.port, args.user)
    rows = db.fetch()

    if not rows:
        print("WARNING: zero rows returned from database", file=sys.stderr)
    else:
        print(f"  Got {len(rows)} flag rows from DB", file=sys.stderr)

    scanner = CodebaseScanner(root)

    if mode == "full":
        print("Extracting feature flag names from codebase...", file=sys.stderr)
        code_ff_names = scanner.extract_type_def_names()
        print(f"  Found {len(code_ff_names)} flag names in type definitions", file=sys.stderr)

        all_tracked_names = {r.name for r in rows}.union(code_ff_names)
        print(f"Scanning codebase for references to {len(all_tracked_names)} flags...", file=sys.stderr)
        references_index = scanner.build_references(all_tracked_names)
        print(f"  Indexed {sum(len(v) for v in references_index.values())} total references", file=sys.stderr)

        code_scan_results = {r.name: references_index.get(r.name, []) for r in rows}

        print("Detecting ghosts...", file=sys.stderr)
        ghost_names = code_ff_names - {r.name for r in rows}
        ghosts = {name: references_index.get(name, []) for name in ghost_names}
        ghosts = {n: f for n, f in ghosts.items() if f}
        print(f"  Found {len(ghosts)} ghosts (in code but not in DB)", file=sys.stderr)
    else:
        code_scan_results = {r.name: [] for r in rows}
        ghosts = {}

    print("Categorizing...", file=sys.stderr)
    cats = categorize(rows, code_scan_results, now, mode)
    for label, items in cats.items():
        if items:
            print(f"  {label}: {len(items)}", file=sys.stderr)

    if args.validate:
        print("--validate: dry-run complete, no report written", file=sys.stderr)
        return

    print("Rendering report...", file=sys.stderr)
    renderer = ReportRenderer(scanner, args.port, generated_at, now, mode)
    report = renderer.render(cats, ghosts)

    out_path = args.out or f"/tmp/ff-report-{now.strftime('%Y-%m-%dT%H%M%S')}.md"
    with open(out_path, "w") as f:
        f.write(report)

    print(out_path)


if __name__ == "__main__":
    main()
