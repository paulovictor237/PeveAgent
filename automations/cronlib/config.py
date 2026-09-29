from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
ENTRY = ROOT / "cron.py"
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
