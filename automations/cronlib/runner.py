import datetime as dt
import fcntl
import json
import os
import plistlib
import shlex
import shutil
import signal
import subprocess
import sys
import uuid

from .config import ARCHIVE_DIR, ENTRY, KEEP_LOGS, LABEL, PLIST, PROBLEMS, REPO_ROOT, RUNS_DIR, STATE_DIR
from .jobs import all_jobs, set_enabled
from .state import append_history, last_slot_of, now, read_state, stamp, update_state


class AlreadyRunning(Exception):
    pass


def notify(title, message):
    script = f"display notification {json.dumps(message, ensure_ascii=False)} with title {json.dumps(title, ensure_ascii=False)}"
    subprocess.run(["osascript", "-e", script], capture_output=True)


def prune_logs(job_runs):
    for old in sorted(job_runs.glob("*.log"))[:-KEEP_LOGS]:
        old.unlink()


def build_command(job):
    if job["mode"] == "script":
        script = job["dir"] / job["script"]
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
        raise ValueError(f"{name}: {job['error']}")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    job_lock = open(STATE_DIR / f"{name}.lock", "w")
    try:
        fcntl.flock(job_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise AlreadyRunning(f"{name}: already running")
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
        suffix = f" ({streak}x in a row)" if streak > 1 else ""
        notify(f"cron: {name}", f"{status}{suffix}")
    if job["schedule_obj"].at and trigger == "schedule":
        finish_once(job, status, run_id)
    return status, code, log_path


def finish_once(job, status, run_id):
    name = job["name"]
    if status in ("ok", "skipped"):
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        archive = ARCHIVE_DIR / f"{name}-{run_id}"
        shutil.move(str(job["dir"]), str(archive))
        update_state(name, archived=str(archive))
        return
    set_enabled(name, False)
    notify(f"cron: {name}", f"one-shot run {status}; job disabled")


def spawn_run(name, trigger):
    subprocess.Popen(
        [sys.executable, str(ENTRY), "run", name, "--trigger", trigger],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def tick():
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
            schedule = job["schedule_obj"]
            if not schedule.at and info.get("schedule_sig") != schedule.label:
                update_state(job["name"], schedule_sig=schedule.label, last_slot=moment.isoformat(timespec="minutes"))
                continue
            grace = int(job["missed_run_grace_minutes"])
            slot, missed = schedule.due(moment, last_slot_of(info), grace, "missed_run_grace_minutes" in job["explicit"])
            if slot is None:
                continue
            update_state(job["name"], last_slot=slot.isoformat(timespec="minutes"))
            if missed:
                update_state(job["name"], status="missed", missed_slot=slot.isoformat(timespec="minutes"))
                if schedule.at:
                    set_enabled(job["name"], False)
                    notify(f"cron: {job['name']}", "one-shot run missed; job disabled")
                continue
            spawn_run(job["name"], "schedule")


def launchd_loaded():
    return subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"], capture_output=True).returncode == 0


def install():
    python = shutil.which("python3", path="/usr/bin") or sys.executable
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [python, str(ENTRY), "tick"],
        "StartInterval": 60,
        "RunAtLoad": True,
        "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.path.expanduser("~")},
        "StandardOutPath": str(STATE_DIR / "launchd.log"),
        "StandardErrorPath": str(STATE_DIR / "launchd.log"),
    }
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(plistlib.dumps(plist))
    result = subprocess.run(["launchctl", "bootstrap", domain, str(PLIST)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def uninstall():
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    if PLIST.exists():
        PLIST.unlink()
