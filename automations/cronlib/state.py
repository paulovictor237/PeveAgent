import datetime as dt
import fcntl
import json
import os

from .config import HISTORY_FILE, KEEP_HISTORY, RUNS_DIR, STATE_DIR, STATE_FILE


def now():
    return dt.datetime.now().replace(second=0, microsecond=0)


def stamp(moment=None):
    return (moment or dt.datetime.now()).isoformat(timespec="seconds")


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


def clear_history():
    with locked("history.lock"):
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()


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


def job_logs(name):
    return sorted((RUNS_DIR / name).glob("*.log"))


def latest_log(name):
    logs = job_logs(name)
    return logs[-1] if logs else None
