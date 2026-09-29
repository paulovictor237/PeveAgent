#!/usr/bin/env python3
import argparse
import datetime as dt
import fcntl
import json
import os
import plistlib
import re
import select
import shlex
import shutil
import signal
import subprocess
import sys
import termios
import time
import tty
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
JOBS_DIR = ROOT / "jobs"
STATE_DIR = ROOT / ".state"
RUNS_DIR = STATE_DIR / "runs"
ARCHIVE_DIR = STATE_DIR / "archive"
STATE_FILE = STATE_DIR / "state.json"
HISTORY_FILE = STATE_DIR / "history.jsonl"
LABEL = "com.peveagent.automations"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
KEEP_LOGS = 30
KEEP_HISTORY = 1000
UNITS = {"m": 1, "h": 60, "d": 1440}
DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}
WEEKDAYS_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
PROBLEMS = {"failed", "timeout", "died", "missed", "invalid"}
DEFAULTS = {
    "enabled": False,
    "mode": "agent",
    "schedule": "daily",
    "time": "09:00",
    "day": "mon",
    "script": "run.sh",
    "precheck": "",
    "workdir": "",
    "timeout_minutes": 30,
    "missed_run_grace_minutes": 60,
    "notify": "on_failure",
    "agent_cmd": "claude -p",
}


def now():
    return dt.datetime.now().replace(second=0, microsecond=0)


def stamp(moment=None):
    return (moment or dt.datetime.now()).isoformat(timespec="seconds")


def parse_datetime(raw):
    return dt.datetime.fromisoformat(raw.strip().replace("T", " ")).replace(second=0, microsecond=0)


def parse_delay(raw):
    match = re.fullmatch(r"(\d+)\s*([mhd])", raw.strip())
    if not match:
        raise ValueError(f"intervalo inválido: {raw} (use 30m, 2h, 1d)")
    return dt.timedelta(minutes=int(match.group(1)) * UNITS[match.group(2)])


def humanize(delta):
    seconds = max(0, int(delta.total_seconds()))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours:02d}h"


def short_time(moment):
    if moment.date() == dt.date.today():
        return f"hoje {moment:%H:%M}"
    if moment.date() == dt.date.today() + dt.timedelta(days=1):
        return f"amanhã {moment:%H:%M}"
    return f"{WEEKDAYS_PT[moment.weekday()]} {moment:%d/%m %H:%M}"


def parse_field(expr, lo, hi):
    values = set()
    for part in expr.split(","):
        step = 1
        if "/" in part:
            part, step_raw = part.split("/")
            step = int(step_raw)
        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            start, end = (int(x) for x in part.split("-"))
        else:
            start = end = int(part)
        if start < lo or end > hi or step < 1:
            raise ValueError(f"campo cron fora do intervalo: {expr}")
        values.update(range(start, end + 1, step))
    return values


class Cron:
    def __init__(self, expr):
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError(f"cron inválido: {expr}")
        minute, hour, dom, month, dow = parts
        self.minutes = parse_field(minute, 0, 59)
        self.hours = parse_field(hour, 0, 23)
        self.doms = parse_field(dom, 1, 31)
        self.months = parse_field(month, 1, 12)
        self.dows = {d % 7 for d in parse_field(dow, 0, 7)}
        self.day_or = dom != "*" and dow != "*"

    def day_matches(self, moment):
        dom_ok = moment.day in self.doms
        dow_ok = (moment.weekday() + 1) % 7 in self.dows
        return (dom_ok or dow_ok) if self.day_or else (dom_ok and dow_ok)

    def matches(self, moment):
        return (
            moment.minute in self.minutes
            and moment.hour in self.hours
            and moment.month in self.months
            and self.day_matches(moment)
        )

    def next_after(self, moment, limit_days=366):
        candidate = moment + dt.timedelta(minutes=1)
        end = moment + dt.timedelta(days=limit_days)
        while candidate <= end:
            if candidate.month not in self.months or not self.day_matches(candidate):
                candidate = (candidate + dt.timedelta(days=1)).replace(hour=0, minute=0)
            elif candidate.hour not in self.hours:
                candidate = (candidate + dt.timedelta(hours=1)).replace(minute=0)
            elif candidate.minute not in self.minutes:
                candidate += dt.timedelta(minutes=1)
            else:
                return candidate
        return None

    def latest(self, moment, lookback_minutes):
        for offset in range(lookback_minutes + 1):
            candidate = moment - dt.timedelta(minutes=offset)
            if self.matches(candidate):
                return candidate
        return None


class Schedule:
    def __init__(self, job):
        raw = str(job["schedule"]).strip()
        self.at = self.every = self.cron = None
        once = re.fullmatch(r"at\s+(.+)", raw)
        every = re.fullmatch(r"every\s+(.+)", raw)
        if once:
            self.at = parse_datetime(once.group(1))
            self.label = f"uma vez {self.at:%d/%m %H:%M}"
        elif every:
            self.every = parse_delay(every.group(1))
            self.label = raw
        elif len(raw.split()) == 5:
            self.cron = Cron(raw)
            self.label = f"cron {raw}"
        else:
            hour, minute = (int(x) for x in str(job["time"]).split(":"))
            day = str(job["day"]).lower()[:3]
            presets = {
                "hourly": (f"{minute} * * * *", f"hourly :{minute:02d}"),
                "daily": (f"{minute} {hour} * * *", f"daily {hour:02d}:{minute:02d}"),
                "weekdays": (f"{minute} {hour} * * 1-5", f"weekdays {hour:02d}:{minute:02d}"),
                "weekly": (f"{minute} {hour} * * {DAYS.get(day, 1)}", f"weekly {day} {hour:02d}:{minute:02d}"),
            }
            if raw not in presets:
                raise ValueError(f"schedule inválido: {raw}")
            expr, self.label = presets[raw]
            self.cron = Cron(expr)

    def next_run(self, moment, last_slot):
        if self.at:
            return None if last_slot else self.at
        if self.every:
            return (last_slot + self.every) if last_slot else moment
        return self.cron.next_after(moment)

    def due(self, moment, last_slot, grace, grace_explicit):
        if self.at:
            if last_slot or self.at > moment:
                return None, False
            late = (moment - self.at).total_seconds() / 60
            return self.at, grace_explicit and late > grace
        if self.every:
            if last_slot is None or moment - last_slot >= self.every:
                return moment, False
            return None, False
        slot = self.cron.latest(moment, grace)
        if slot and (last_slot is None or slot > last_slot):
            return slot, False
        if last_slot:
            missed = self.cron.latest(moment, 60 * 24 * 7)
            if missed and missed > last_slot:
                return missed, True
        return None, False


def parse_scalar(raw):
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.lower() in ("true", "yes", "on"):
        return True
    if value.lower() in ("false", "no", "off"):
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def load_job(job_dir):
    text = (job_dir / "prompt.md").read_text()
    meta, body = {}, text
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if match:
        body = match.group(2)
        for line in match.group(1).splitlines():
            if ":" in line and not line.lstrip().startswith("#"):
                key, raw = line.split(":", 1)
                meta[key.strip()] = parse_scalar(raw)
    job = dict(DEFAULTS, **meta)
    job.update(
        name=job_dir.name,
        dir=job_dir,
        prompt=body.strip(),
        explicit=set(meta),
        workdir=str((REPO_ROOT / os.path.expanduser(str(job["workdir"]))).resolve()) if job["workdir"] else str(REPO_ROOT),
        schedule_obj=None,
        error=None,
    )
    try:
        job["schedule_obj"] = Schedule(job)
    except ValueError as error:
        job["error"] = str(error)
    return job


def all_jobs():
    if not JOBS_DIR.exists():
        return []
    return [load_job(d) for d in sorted(JOBS_DIR.iterdir()) if (d / "prompt.md").exists()]


def get_job(name):
    job_dir = JOBS_DIR / name
    if not (job_dir / "prompt.md").exists():
        raise SystemExit(f"job não encontrado: {name}")
    return load_job(job_dir)


def read_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def locked(name):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(STATE_DIR / name, "w")
    fcntl.flock(handle, fcntl.LOCK_EX)
    return handle


def update_state(name, **fields):
    with locked("state.lock"):
        state = read_state()
        state.setdefault(name, {}).update(fields)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False))
        tmp.replace(STATE_FILE)
        return state[name]


def last_slot_of(info):
    raw = info.get("last_slot")
    return dt.datetime.fromisoformat(raw) if raw else None


def append_history(record):
    with locked("history.lock"):
        lines = HISTORY_FILE.read_text().splitlines() if HISTORY_FILE.exists() else []
        lines.append(json.dumps(record, ensure_ascii=False))
        HISTORY_FILE.write_text("\n".join(lines[-KEEP_HISTORY:]) + "\n")


def read_history(job=None, limit=10):
    if not HISTORY_FILE.exists():
        return []
    records = []
    for line in reversed(HISTORY_FILE.read_text().splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if job is None or record.get("job") == job:
            records.append(record)
            if len(records) >= limit:
                break
    return records


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def live_status(info):
    status = info.get("status", "-")
    if status == "running" and not pid_alive(info.get("pid")):
        return "died"
    return status


def running_jobs(state):
    return {name: info for name, info in sorted(state.items()) if live_status(info) == "running"}


def notify(title, message):
    script = f"display notification {json.dumps(message, ensure_ascii=False)} with title {json.dumps(title, ensure_ascii=False)}"
    subprocess.run(["osascript", "-e", script], capture_output=True)


def prune_logs(job_runs):
    for old in sorted(job_runs.glob("*.log"))[:-KEEP_LOGS]:
        old.unlink()


def build_command(job):
    if job["mode"] == "script":
        script = Path(job["dir"]) / job["script"]
        return [str(script)] if os.access(script, os.X_OK) else ["bash", str(script)]
    return shlex.split(str(job["agent_cmd"])) + [job["prompt"]]


def run_process(command, cwd, env, log, timeout_seconds):
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as error:
        log.write(f"\n{error}\n")
        return "failed", 127
    try:
        code = proc.wait(timeout=timeout_seconds)
        return ("ok" if code == 0 else "failed"), code
    except subprocess.TimeoutExpired:
        for sig, grace in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
            try:
                os.killpg(proc.pid, sig)
                proc.wait(timeout=grace)
                break
            except (ProcessLookupError, subprocess.TimeoutExpired):
                continue
        return "timeout", 124


def execute(job, trigger):
    name = job["name"]
    if job["error"]:
        raise SystemExit(f"{name}: {job['error']}")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    job_lock = open(STATE_DIR / f"{name}.lock", "w")
    try:
        fcntl.flock(job_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"{name}: já está rodando")
        return 1
    job_runs = RUNS_DIR / name
    job_runs.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now()
    run_id = f"{started:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    log_path = job_runs / f"{run_id}.log"
    env = dict(
        os.environ,
        PEVE_JOB=name,
        PEVE_RUN_ID=run_id,
        PEVE_RUN_LOG=str(log_path),
        PEVE_JOB_DIR=str(job["dir"]),
        PEVE_REPO_ROOT=str(REPO_ROOT),
        PEVE_TRIGGER=trigger,
    )
    update_state(name, status="running", run_id=run_id, pid=os.getpid(), trigger=trigger, started_at=stamp(started), last_log=str(log_path))
    with open(log_path, "w") as log:
        log.write(f"# {name} {run_id} trigger={trigger} started={stamp(started)}\n")
        log.flush()
        status, code = "ok", 0
        if job["precheck"]:
            check = subprocess.run(job["precheck"], shell=True, cwd=job["workdir"], env=env, stdout=log, stderr=log)
            if check.returncode != 0:
                status = "skipped"
        if status != "skipped":
            status, code = run_process(build_command(job), job["workdir"], env, log, int(job["timeout_minutes"]) * 60)
        duration = int((dt.datetime.now() - started).total_seconds())
        log.write(f"\n# status={status} exit={code} duration={duration}s\n")
    streak = 0 if status in ("ok", "skipped") else read_state().get(name, {}).get("failure_streak", 0) + 1
    update_state(name, status=status, exit_code=code, finished_at=stamp(), failure_streak=streak)
    append_history(dict(job=name, run_id=run_id, trigger=trigger, status=status, exit=code, started=stamp(started), duration=duration, log=str(log_path)))
    prune_logs(job_runs)
    if job["notify"] == "always" or (job["notify"] == "on_failure" and status in PROBLEMS):
        suffix = f" ({streak}x seguidas)" if streak > 1 else ""
        notify(f"peve-auto: {name}", f"{status}{suffix}")
    print(f"{name}: {status} (exit {code}) → {log_path}")
    if job["schedule_obj"].at and trigger == "schedule":
        finish_once(job, status, run_id)
    return code


def finish_once(job, status, run_id):
    name = job["name"]
    if status in ("ok", "skipped"):
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        archive = ARCHIVE_DIR / f"{name}-{run_id}"
        shutil.move(str(job["dir"]), str(archive))
        update_state(name, archived=str(archive))
        return
    set_enabled(name, False)
    notify(f"peve-auto: {name}", f"execução única {status}; job desativado")


def set_enabled(name, value):
    path = get_job(name)["dir"] / "prompt.md"
    text = path.read_text()
    flag = "true" if value else "false"
    if re.search(r"^enabled:.*$", text, re.M):
        text = re.sub(r"^enabled:.*$", f"enabled: {flag}", text, count=1, flags=re.M)
    elif text.startswith("---\n"):
        text = text.replace("---\n", f"---\nenabled: {flag}\n", 1)
    else:
        text = f"---\nenabled: {flag}\n---\n{text}"
    path.write_text(text)
    print(f"{name}: {'ligado' if value else 'desligado'}")


def launchd_loaded():
    return subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"], capture_output=True).returncode == 0


STYLES = {"bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33", "blue": "34", "magenta": "35", "cyan": "36"}
STATUS_STYLE = {
    "ok": "green",
    "running": "cyan",
    "skipped": "dim",
    "missed": "yellow",
    "invalid": "red",
    "failed": "red",
    "timeout": "red",
    "died": "red",
}
STATUS_ORDER = ["running", "died", "failed", "timeout", "invalid", "missed", "ok", "skipped", "-"]
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
ANSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


class Painter:
    def __init__(self, enabled):
        self.enabled = enabled

    def __call__(self, text, *styles):
        codes = ";".join(STYLES[s] for s in styles if s)
        if not self.enabled or not codes:
            return text
        return f"\033[{codes}m{text}\033[0m"


def visible_len(text):
    return len(ANSI.sub("", text))


def table(paint, headers, rows):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], visible_len(cell))
    lines = ["  ".join(paint(h.ljust(w), "dim", "bold") for h, w in zip(headers, widths)).rstrip()]
    for row in rows:
        lines.append("  ".join(cell + " " * (w - visible_len(cell)) for cell, w in zip(row, widths)).rstrip())
    return lines


def job_rows(paint, jobs, state, moment):
    rows = []
    for job in jobs:
        info = state.get(job["name"], {})
        status = "invalid" if job["error"] else live_status(info)
        dot = paint("●", "green") if job["enabled"] else paint("○", "dim")
        name = paint(job["name"], "bold") if job["enabled"] else paint(job["name"], "dim")
        sched = job["schedule_obj"]
        schedule = paint(job["error"], "red") if job["error"] else sched.label
        if status == "running":
            last = paint(f"running {humanize(dt.datetime.now() - dt.datetime.fromisoformat(info['started_at']))}", "cyan")
        elif status in ("-", "invalid") and not info.get("finished_at"):
            last = paint("—", "dim")
        else:
            streak = info.get("failure_streak", 0)
            when = dt.datetime.fromisoformat(info.get("finished_at") or info.get("started_at"))
            text = f"{status}{f' ×{streak}' if streak > 1 else ''}"
            last = f"{paint(text, STATUS_STYLE.get(status, ''))} {paint('há ' + humanize(dt.datetime.now() - when), 'dim')}"
        upcoming = paint("—", "dim")
        if sched and job["enabled"]:
            nxt = sched.next_run(moment, last_slot_of(info))
            if nxt:
                upcoming = f"{short_time(nxt)} {paint('em ' + humanize(nxt - dt.datetime.now()), 'dim')}"
        elif sched:
            nxt = sched.next_run(moment, last_slot_of(info))
            upcoming = paint(short_time(nxt) if nxt else "—", "dim")
        rows.append([f"{dot} {name}", paint(job["mode"], "magenta" if job["mode"] == "agent" else "blue"), schedule, last, upcoming])
    return rows


def status_rank(job, state):
    status = "invalid" if job["error"] else live_status(state.get(job["name"], {}))
    rank = STATUS_ORDER.index(status) if status in STATUS_ORDER else len(STATUS_ORDER)
    return (rank, not job["enabled"], job["name"])


def render_jobs(paint, ranked=False):
    jobs, state = all_jobs(), read_state()
    headers = ["JOB", "MODO", "AGENDA", "ÚLTIMA", "PRÓXIMA"]
    if ranked:
        jobs.sort(key=lambda job: status_rank(job, state))
    rows = job_rows(paint, jobs, state, now())
    if not rows:
        return [paint("nenhum job", "dim")]
    if ranked:
        headers = ["Nº"] + headers
        rows = [[paint(f"#{index}", "dim")] + row for index, row in enumerate(rows, 1)]
    return table(paint, headers, rows)


def last_log_line(path):
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 4096))
            lines = [l for l in handle.read().decode(errors="replace").splitlines() if l.strip() and not l.startswith("# ")]
        return lines[-1].strip() if lines else ""
    except OSError:
        return ""


def render_running(paint, frame=0):
    running = running_jobs(read_state())
    if not running:
        return [paint("nada rodando", "dim")]
    lines = []
    for name, info in running.items():
        spin = paint(SPINNER[frame % len(SPINNER)], "cyan")
        took = humanize(dt.datetime.now() - dt.datetime.fromisoformat(info["started_at"]))
        lines.append(f"{spin} {paint(name, 'bold')}  {paint(took, 'cyan')}  {paint(info.get('trigger', ''), 'dim')}  pid {info.get('pid')}")
        tail = last_log_line(info.get("last_log", ""))
        if tail:
            lines.append(f"  {paint('└', 'dim')} {paint(tail, 'dim')}")
    return lines


def render_history(paint, job=None, limit=8):
    records = read_history(job, limit)
    if not records:
        return [paint("sem execuções", "dim")]
    rows = []
    for record in records:
        started = dt.datetime.fromisoformat(record["started"])
        status = record["status"]
        rows.append([
            paint(short_time(started), "dim"),
            record["job"],
            paint(status, STATUS_STYLE.get(status, "")),
            paint(f"{record.get('duration', 0)}s", "dim"),
            paint(record.get("trigger", ""), "dim"),
        ])
    return table(paint, ["QUANDO", "JOB", "STATUS", "DURAÇÃO", "ORIGEM"], rows)


def render_title(paint):
    scheduler = paint("● agendador ativo", "green") if launchd_loaded() else paint("○ agendador inativo (install)", "yellow")
    return f"{paint('peve-auto', 'bold')}  {paint(dt.datetime.now().strftime('%H:%M:%S'), 'dim')}  {scheduler}"


def render_dashboard(paint, frame=0, interval=1):
    return (
        [render_title(paint), ""]
        + [paint("JOBS", "bold")]
        + render_jobs(paint, ranked=True)
        + ["", paint("RODANDO", "bold")]
        + render_running(paint, frame)
        + ["", paint("ÚLTIMAS EXECUÇÕES", "bold")]
        + render_history(paint)
        + ["", paint(f"q sair · r atualizar · atualiza a cada {interval}s", "dim")]
    )


def fit(line, width):
    if visible_len(line) <= width:
        return line
    out, count = [], 0
    for token in re.split(r"(\033\[[0-9;?]*[A-Za-z])", line):
        if ANSI.fullmatch(token or "x"):
            out.append(token)
            continue
        room = width - 1 - count
        if room <= 0:
            break
        out.append(token[:room])
        count += len(token[:room])
    return "".join(out) + "…\033[0m"


def output_painter():
    return Painter(sys.stdout.isatty() and "NO_COLOR" not in os.environ)


def cmd_list(_args):
    paint = output_painter()
    print("\n".join([render_title(paint), ""] + render_jobs(paint)))


def cmd_watch(args):
    paint = Painter("NO_COLOR" not in os.environ)
    interactive = sys.stdin.isatty()
    saved = termios.tcgetattr(sys.stdin) if interactive else None
    sys.stdout.write("\033[?1049h\033[?25l")
    frame = 0
    try:
        if interactive:
            tty.setcbreak(sys.stdin.fileno())
        while True:
            size = shutil.get_terminal_size()
            columns, rows = size.columns or 100, size.lines or 40
            lines = [fit(l, columns) for l in render_dashboard(paint, frame, args.interval)[:rows]]
            sys.stdout.write("\033[H" + "\033[K\n".join(lines) + "\033[K\033[J")
            sys.stdout.flush()
            frame += 1
            deadline = time.time() + args.interval
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                if not interactive:
                    time.sleep(remaining)
                    continue
                if not select.select([sys.stdin], [], [], remaining)[0]:
                    continue
                key = sys.stdin.read(1)
                if key in ("q", "Q", "\x1b"):
                    return
                if key in ("r", "R"):
                    break
    except KeyboardInterrupt:
        return
    finally:
        if saved:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, saved)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


def cmd_runs(args):
    print("\n".join(render_history(output_painter(), args.job, args.n)))


def cmd_logs(args):
    logs = sorted((RUNS_DIR / args.job).glob("*.log"))
    if not logs:
        raise SystemExit("sem execuções")
    for log in logs[-args.n:-1]:
        print(log.read_text())
    info = read_state().get(args.job, {})
    try:
        with open(logs[-1]) as handle:
            sys.stdout.write(handle.read())
            while info.get("last_log") == str(logs[-1]) and live_status(read_state().get(args.job, {})) == "running":
                chunk = handle.read()
                if chunk:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                else:
                    time.sleep(0.3)
            sys.stdout.write(handle.read())
    except KeyboardInterrupt:
        pass


def cmd_run(args):
    return execute(get_job(args.job), args.trigger)


def cmd_toggle(args):
    names = [job["name"] for job in all_jobs()] if args.all else [args.job]
    if not args.all and not args.job:
        raise SystemExit("informe <job> ou --all")
    for name in names:
        set_enabled(name, args.command == "enable")


def cmd_new(args):
    job_dir = JOBS_DIR / args.job
    if job_dir.exists():
        raise SystemExit(f"já existe: {job_dir}")
    schedule, time_line = "daily", 'time: "09:00"\n'
    if args.at or args.delay:
        at = parse_datetime(args.at) if args.at else now() + parse_delay(args.delay)
        schedule, time_line = f'"at {at:%Y-%m-%d %H:%M}"', ""
    job_dir.mkdir(parents=True)
    body = "Descreva aqui a tarefa do agente." if args.mode == "agent" else "Descrição do que o script faz."
    (job_dir / "prompt.md").write_text(
        f"---\nenabled: {'true' if args.enabled else 'false'}\nmode: {args.mode}\nschedule: {schedule}\n{time_line}"
        f"timeout_minutes: 30\nnotify: on_failure\n---\n\n{body}\n"
    )
    if args.mode == "script":
        script = job_dir / "run.sh"
        script.write_text("#!/usr/bin/env bash\nset -euo pipefail\n\necho \"$PEVE_JOB $PEVE_RUN_ID\"\n")
        script.chmod(0o755)
    print(f"criado: {job_dir}")


def cmd_tick(_args):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "tick.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        moment = now()
        state = read_state()
        for job in all_jobs():
            if not job["enabled"]:
                continue
            if job["error"]:
                update_state(job["name"], status="invalid", error=job["error"])
                continue
            info = state.get(job["name"], {})
            signature = job["schedule_obj"].label
            if not job["schedule_obj"].at and info.get("schedule_sig") != signature:
                update_state(job["name"], schedule_sig=signature, last_slot=moment.isoformat(timespec="minutes"))
                continue
            grace = int(job["missed_run_grace_minutes"])
            slot, missed = job["schedule_obj"].due(moment, last_slot_of(info), grace, "missed_run_grace_minutes" in job["explicit"])
            if slot is None:
                continue
            update_state(job["name"], last_slot=slot.isoformat(timespec="minutes"))
            if missed:
                update_state(job["name"], status="missed", missed_slot=slot.isoformat(timespec="minutes"))
                if job["schedule_obj"].at:
                    set_enabled(job["name"], False)
                    notify(f"peve-auto: {job['name']}", "execução única perdida; job desativado")
                continue
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "run", job["name"], "--trigger", "schedule"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )


def cmd_install(_args):
    python = shutil.which("python3", path="/usr/bin") or sys.executable
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [python, str(Path(__file__).resolve()), "tick"],
        "StartInterval": 60,
        "RunAtLoad": True,
        "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(Path.home())},
        "StandardOutPath": str(STATE_DIR / "launchd.log"),
        "StandardErrorPath": str(STATE_DIR / "launchd.log"),
    }
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(plistlib.dumps(plist))
    result = subprocess.run(["launchctl", "bootstrap", domain, str(PLIST)], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip())
    print(f"instalado: {PLIST}")


def cmd_uninstall(_args):
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    if PLIST.exists():
        PLIST.unlink()
    print("desinstalado")


def build_parser():
    parser = argparse.ArgumentParser(prog="peve-auto.py", description="Automações agendadas do PeveAgent")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<comando>")

    sub.add_parser("list", help="agendador + jobs").set_defaults(func=cmd_list)

    p = sub.add_parser("watch", help="painel ao vivo")
    p.add_argument("-n", dest="interval", type=float, default=1, metavar="SEGUNDOS")
    p.set_defaults(func=cmd_watch)

    for name, func, help_text, default in (
        ("runs", cmd_runs, "histórico de execuções", 10),
        ("logs", cmd_logs, "saída da última execução (ao vivo se rodando)", 1),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("job")
        p.add_argument("-n", type=int, default=default)
        p.set_defaults(func=func)

    p = sub.add_parser("run", help="roda um job agora")
    p.add_argument("job")
    p.add_argument("--trigger", default="manual", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_run)

    for name in ("enable", "disable"):
        p = sub.add_parser(name, help=f"{'liga' if name == 'enable' else 'desliga'} job(s)")
        p.add_argument("job", nargs="?")
        p.add_argument("--all", action="store_true")
        p.set_defaults(func=cmd_toggle)

    p = sub.add_parser("new", help="cria um job")
    p.add_argument("job")
    p.add_argument("--mode", choices=("agent", "script"), default="agent")
    p.add_argument("--enabled", action="store_true")
    when = p.add_mutually_exclusive_group()
    when.add_argument("--at", metavar='"YYYY-MM-DD HH:MM"')
    when.add_argument("--in", dest="delay", metavar="30m|2h|1d")
    p.set_defaults(func=cmd_new)

    sub.add_parser("install", help="instala o agendador no launchd").set_defaults(func=cmd_install)
    sub.add_parser("uninstall", help="remove o agendador").set_defaults(func=cmd_uninstall)
    sub.add_parser("tick").set_defaults(func=cmd_tick)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        return args.func(args) or 0
    except ValueError as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    sys.exit(main())
