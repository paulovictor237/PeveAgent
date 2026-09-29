import os
import re

from .config import DEFAULTS, JOBS_DIR, REPO_ROOT
from .schedule import Schedule


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
        raise LookupError(f"job not found: {name}")
    return load_job(job_dir)


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
