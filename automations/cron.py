#!/usr/bin/env python3
import argparse
import sys
import time

from cronlib.config import JOBS_DIR, PLIST
from cronlib.jobs import all_jobs, get_job, set_enabled
from cronlib.render import Painter, history_table, job_table, title_line
from cronlib.runner import AlreadyRunning, execute, install, launchd_loaded, tick, uninstall
from cronlib.schedule import parse_datetime, parse_delay
from cronlib.state import job_logs, live_status, now, read_state


def output_painter():
    return Painter(sys.stdout.isatty())


def cmd_ui(_args):
    from cronlib.tui import App

    App().run()


def cmd_list(_args):
    paint = output_painter()
    print("\n".join([title_line(paint, launchd_loaded()), ""] + job_table(paint, all_jobs(), read_state())))


def cmd_runs(args):
    print("\n".join(history_table(output_painter(), args.job, args.n)))


def cmd_logs(args):
    logs = job_logs(args.job)
    if not logs:
        raise SystemExit("no runs")
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
    try:
        status, code, log_path = execute(get_job(args.job), args.trigger)
    except AlreadyRunning as error:
        raise SystemExit(str(error))
    print(f"{args.job}: {status} (exit {code}) → {log_path}")
    return code


def cmd_toggle(args):
    if not args.all and not args.job:
        raise SystemExit("pass <job> or --all")
    value = args.command == "enable"
    for name in [job["name"] for job in all_jobs()] if args.all else [args.job]:
        set_enabled(name, value)
        print(f"{name}: {'enabled' if value else 'disabled'}")


def cmd_new(args):
    job_dir = JOBS_DIR / args.job
    if job_dir.exists():
        raise SystemExit(f"already exists: {job_dir}")
    schedule, time_line = "daily", 'time: "09:00"\n'
    if args.at or args.delay:
        at = parse_datetime(args.at) if args.at else now() + parse_delay(args.delay)
        schedule, time_line = f'"at {at:%Y-%m-%d %H:%M}"', ""
    job_dir.mkdir(parents=True)
    body = "Describe the agent task here." if args.mode == "agent" else "Describe what the script does."
    (job_dir / "prompt.md").write_text(
        f"---\nenabled: {'true' if args.enabled else 'false'}\nmode: {args.mode}\nschedule: {schedule}\n{time_line}"
        f"timeout_minutes: 30\nnotify: on_failure\n---\n\n{body}\n"
    )
    if args.mode == "script":
        script = job_dir / "run.sh"
        script.write_text("#!/usr/bin/env bash\nset -euo pipefail\n\necho \"$PEVE_JOB $PEVE_RUN_ID\"\n")
        script.chmod(0o755)
    print(f"created: {job_dir}")


def cmd_install(_args):
    install()
    print(f"installed: {PLIST}")


def cmd_uninstall(_args):
    uninstall()
    print("uninstalled")


def build_parser():
    parser = argparse.ArgumentParser(prog="cron.py", description="PeveAgent scheduled automations. No command opens the control panel.")
    parser.set_defaults(func=cmd_ui)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("list", help="scheduler + jobs").set_defaults(func=cmd_list)

    for name, func, help_text, default in (
        ("runs", cmd_runs, "run history", 10),
        ("logs", cmd_logs, "latest run output (live while running)", 1),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("job")
        p.add_argument("-n", type=int, default=default)
        p.set_defaults(func=func)

    p = sub.add_parser("run", help="run a job now")
    p.add_argument("job")
    p.add_argument("--trigger", default="manual", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_run)

    for name in ("enable", "disable"):
        p = sub.add_parser(name, help=f"{name} job(s)")
        p.add_argument("job", nargs="?")
        p.add_argument("--all", action="store_true")
        p.set_defaults(func=cmd_toggle)

    p = sub.add_parser("new", help="create a job")
    p.add_argument("job")
    p.add_argument("--mode", choices=("agent", "script"), default="agent")
    p.add_argument("--enabled", action="store_true")
    when = p.add_mutually_exclusive_group()
    when.add_argument("--at", metavar='"YYYY-MM-DD HH:MM"')
    when.add_argument("--in", dest="delay", metavar="30m|2h|1d")
    p.set_defaults(func=cmd_new)

    sub.add_parser("install", help="install the launchd scheduler").set_defaults(func=cmd_install)
    sub.add_parser("uninstall", help="remove the scheduler").set_defaults(func=cmd_uninstall)
    sub.add_parser("tick").set_defaults(func=lambda _args: tick())
    return parser


def main():
    args = build_parser().parse_args()
    try:
        return args.func(args) or 0
    except (ValueError, LookupError, RuntimeError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    sys.exit(main())
