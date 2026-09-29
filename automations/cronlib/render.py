import datetime as dt
import os
import re

from .state import last_slot_of, live_status, now, read_history, running_jobs

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
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
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


def table(paint, headers, rows):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], visible_len(cell))
    lines = ["  ".join(paint(h.ljust(w), "dim", "bold") for h, w in zip(headers, widths)).rstrip()]
    for row in rows:
        lines.append("  ".join(cell + " " * (w - visible_len(cell)) for cell, w in zip(row, widths)).rstrip())
    return lines


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
        return f"today {moment:%H:%M}"
    if moment.date() == dt.date.today() + dt.timedelta(days=1):
        return f"tomorrow {moment:%H:%M}"
    return f"{WEEKDAYS[moment.weekday()]} {moment:%d/%m %H:%M}"


def job_status(job, state):
    return "invalid" if job["error"] else live_status(state.get(job["name"], {}))


def rank_jobs(jobs, state):
    def rank(job):
        status = job_status(job, state)
        position = STATUS_ORDER.index(status) if status in STATUS_ORDER else len(STATUS_ORDER)
        return (position, not job["enabled"], job["name"])

    return sorted(jobs, key=rank)


def job_row(paint, job, state, moment, pending=False):
    info = state.get(job["name"], {})
    status = job_status(job, state)
    dot = paint("●", "green") if job["enabled"] else paint("○", "dim")
    name = paint(job["name"], "bold") if job["enabled"] else paint(job["name"], "dim")
    if pending:
        dot = paint("○" if job["enabled"] else "●", "yellow")
        name = f"{name} {paint('→ disable' if job['enabled'] else '→ enable', 'yellow')}"
    schedule = job["schedule_obj"]
    agenda = paint(job["error"], "red") if job["error"] else schedule.label
    if status == "running":
        last = paint(f"running {humanize(dt.datetime.now() - dt.datetime.fromisoformat(info['started_at']))}", "cyan")
    elif status in ("-", "invalid") and not info.get("finished_at"):
        last = paint("—", "dim")
    else:
        streak = info.get("failure_streak", 0)
        when = dt.datetime.fromisoformat(info.get("finished_at") or info.get("started_at"))
        text = f"{status}{f' ×{streak}' if streak > 1 else ''}"
        last = f"{paint(text, STATUS_STYLE.get(status, ''))} {paint(humanize(dt.datetime.now() - when) + ' ago', 'dim')}"
    upcoming = paint("—", "dim")
    if schedule:
        nxt = schedule.next_run(moment, last_slot_of(info))
        if nxt and job["enabled"]:
            upcoming = f"{short_time(nxt)} {paint('in ' + humanize(nxt - dt.datetime.now()), 'dim')}"
        elif nxt:
            upcoming = paint(short_time(nxt), "dim")
    mode = paint(job["mode"], "magenta" if job["mode"] == "agent" else "blue")
    return [f"{dot} {name}", mode, agenda, last, upcoming]


def job_table(paint, jobs, state, selected=None, pending=(), numbered=False):
    if not jobs:
        return [paint("nenhum job", "dim")]
    moment = now()
    headers = ["JOB", "MODE", "SCHEDULE", "LAST", "NEXT"]
    rows = []
    for index, job in enumerate(jobs, 1):
        row = job_row(paint, job, state, moment, job["name"] in pending)
        if numbered:
            marker = paint(f"› #{index}", "cyan", "bold") if job["name"] == selected else paint(f"  #{index}", "dim")
            row = [marker] + row
        rows.append(row)
    return table(paint, (["#"] if numbered else []) + headers, rows)


def last_log_line(path):
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - 4096))
            lines = [l for l in handle.read().decode(errors="replace").splitlines() if l.strip() and not l.startswith("# ")]
        return lines[-1].strip() if lines else ""
    except OSError:
        return ""


def running_lines(paint, state, frame=0):
    running = running_jobs(state)
    if not running:
        return [paint("nothing running", "dim")]
    lines = []
    for name, info in running.items():
        spin = paint(SPINNER[frame % len(SPINNER)], "cyan")
        took = humanize(dt.datetime.now() - dt.datetime.fromisoformat(info["started_at"]))
        lines.append(f"{spin} {paint(name, 'bold')}  {paint(took, 'cyan')}  {paint(info.get('trigger', ''), 'dim')}  pid {info.get('pid')}")
        tail = last_log_line(info.get("last_log", ""))
        if tail:
            lines.append(f"  {paint('└', 'dim')} {paint(tail, 'dim')}")
    return lines


def history_table(paint, job=None, limit=8):
    records = read_history(job, limit)
    if not records:
        return [paint("no runs", "dim")]
    rows = []
    for record in records:
        status = record["status"]
        rows.append([
            paint(short_time(dt.datetime.fromisoformat(record["started"])), "dim"),
            record["job"],
            paint(status, STATUS_STYLE.get(status, "")),
            paint(f"{record.get('duration', 0)}s", "dim"),
            paint(record.get("trigger", ""), "dim"),
        ])
    return table(paint, ["WHEN", "JOB", "STATUS", "DURATION", "TRIGGER"], rows)


def title_line(paint, scheduler_active):
    scheduler = paint("● scheduler active", "green") if scheduler_active else paint("○ scheduler inactive (a installs)", "yellow")
    return f"{paint('cron', 'bold')}  {paint(dt.datetime.now().strftime('%H:%M:%S'), 'dim')}  {scheduler}"
