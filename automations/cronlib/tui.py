import os
import select
import shlex
import shutil
import subprocess
import sys
import termios
import time
import tty

from .jobs import all_jobs, set_enabled
from .render import Painter, SPINNER, fit, history_table, job_status, job_table, rank_jobs, running_lines, title_line
from .runner import install, launchd_loaded, spawn_run, uninstall
from .state import clear_history, latest_log, live_status, read_state

GUI_EDITORS = {"zed", "code", "cursor", "subl", "open"}
ARROWS = {"\x1b[A": "up", "\x1b[B": "down", "\x1bOA": "up", "\x1bOB": "down"}
FLASH_SECONDS = 4


def read_keys():
    data = os.read(sys.stdin.fileno(), 64).decode(errors="ignore")
    keys = []
    while data:
        if data.startswith("\x1b"):
            sequence = data[:3]
            if sequence in ARROWS:
                keys.append(ARROWS[sequence])
                data = data[3:]
                continue
            keys.append("esc")
            data = data[1:]
            continue
        keys.append({"\r": "enter", "\n": "enter", " ": "space"}.get(data[0], data[0].lower()))
        data = data[1:]
    return keys


def editor_command():
    configured = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if configured:
        return shlex.split(configured)
    return ["zed"] if shutil.which("zed") else ["open"]


class App:
    def __init__(self, interval=1.0):
        self.interval = interval
        self.paint = Painter("NO_COLOR" not in os.environ)
        self.interactive = sys.stdin.isatty()
        self.saved_tty = None
        self.view = "dashboard"
        self.frame = 0
        self.jobs = []
        self.state = {}
        self.selected = None
        self.pending = set()
        self.confirm = None
        self.scheduler_active = False
        self.flash = None
        self.log_offset = 0

    def run(self):
        self.enter_screen()
        try:
            while True:
                self.draw()
                if not self.wait_for_key():
                    return
        except KeyboardInterrupt:
            return
        finally:
            self.leave_screen()

    def enter_screen(self):
        if self.interactive:
            self.saved_tty = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        sys.stdout.write("\033[?1049h\033[?25l")
        sys.stdout.flush()

    def leave_screen(self):
        if self.saved_tty:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.saved_tty)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()

    def wait_for_key(self):
        deadline = time.time() + self.interval
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return True
            if not self.interactive:
                time.sleep(remaining)
                continue
            if select.select([sys.stdin], [], [], remaining)[0]:
                return all(self.handle(key) for key in read_keys())

    def refresh(self):
        self.state = read_state()
        self.scheduler_active = launchd_loaded()
        self.jobs = rank_jobs(all_jobs(), self.state)
        names = [job["name"] for job in self.jobs]
        self.pending &= set(names)
        if self.selected not in names:
            self.selected = names[0] if names else None
        self.frame += 1

    def selected_job(self):
        return next((job for job in self.jobs if job["name"] == self.selected), None)

    def draw(self):
        self.refresh()
        size = shutil.get_terminal_size()
        columns, rows = size.columns or 100, size.lines or 40
        lines = self.log_view(rows) if self.view == "log" else self.dashboard()
        lines = [fit(line, columns) for line in lines[:rows]]
        sys.stdout.write("\033[H" + "\033[K\n".join(lines) + "\033[K\033[J")
        sys.stdout.flush()

    def dashboard(self):
        paint = self.paint
        return (
            [title_line(paint, self.scheduler_active), ""]
            + [paint("JOBS", "bold")]
            + job_table(paint, self.jobs, self.state, self.selected, self.pending, numbered=True)
            + ["", paint("RUNNING", "bold")]
            + running_lines(paint, self.state, self.frame)
            + ["", paint("RECENT RUNS", "bold")]
            + history_table(paint)
            + ["", paint("COMMANDS", "bold")]
            + self.hint_lines()
            + ["", self.flash_line()]
        )

    def log_view(self, rows):
        paint = self.paint
        name = self.selected
        info = self.state.get(name, {})
        path = info.get("last_log") or latest_log(name)
        status = live_status(info) if info else "-"
        badge = paint(f"{SPINNER[self.frame % len(SPINNER)]} running", "cyan") if status == "running" else paint(status, "dim")
        header = [f"{paint('LOG', 'bold')}  {paint(name or '-', 'bold')}  {badge}  {paint(str(path or ''), 'dim')}", ""]
        footer = ["", self.keybar([("↑↓", "scroll"), ("g", "end"), ("x", "run"), ("e", "edit"), ("esc", "back")], "log")]
        height = max(1, rows - len(header) - len(footer))
        try:
            content = open(path, errors="replace").read().splitlines() if path else []
        except OSError:
            content = []
        if not content:
            return header + [paint("no runs", "dim")] + footer
        self.log_offset = min(self.log_offset, max(0, len(content) - height))
        end = len(content) - self.log_offset
        body = content[max(0, end - height):end]
        if self.log_offset:
            footer[-1] = self.keybar([("↑↓", f"scroll (-{self.log_offset})"), ("g", "end"), ("x", "run"), ("e", "edit"), ("esc", "back")], "log")
        return header + body + [""] * (height - len(body)) + footer

    def flash_line(self):
        if self.flash and time.time() < self.flash[2]:
            return self.paint(self.flash[0], self.flash[1])
        return ""

    def keybar(self, keys, label="", branch=""):
        paint = self.paint
        badges = "  ".join(f"{paint(f'[{key}]', 'cyan', 'bold')} {paint(text, 'dim')}" for key, text in keys)
        prefix = [paint(part, "dim") for part in (branch, label.ljust(4) if label else "") if part]
        return " " + " ".join(prefix + [badges])

    def branch_line(self, text, branch="├"):
        return f" {self.paint(branch, 'dim')} {self.paint(text, 'yellow', 'bold')}"

    def hint_lines(self):
        if self.confirm:
            return [
                self.branch_line(self.confirm[0]),
                self.keybar([("enter", "confirm"), ("esc", "cancel")], branch="└"),
            ]
        if self.pending:
            count = len(self.pending)
            summary = f"{count} pending change" if count == 1 else f"{count} pending changes"
            return [
                self.branch_line(summary),
                self.keybar([("enter", "apply"), ("esc", "cancel"), ("␣", "mark/unmark")], branch="└"),
            ]
        return [
            self.keybar([("x", "run"), ("l", "log"), ("e", "edit"), ("␣", "toggle"), ("↑↓", "navigate")], "job", "├"),
            self.keybar([("a", "scheduler"), ("c", "clear runs"), ("q", "quit")], "app", "└"),
        ]

    def say(self, text, style="green"):
        self.flash = (text, style, time.time() + FLASH_SECONDS)

    def handle(self, key):
        if self.confirm:
            if key == "enter":
                action = self.confirm[1]
                self.confirm = None
                action()
            elif key == "esc":
                self.confirm = None
            return True
        if self.view == "log":
            return self.handle_log(key)
        return self.handle_dashboard(key)

    def handle_dashboard(self, key):
        if key == "q" or (key == "esc" and not self.pending):
            return False
        if key == "esc":
            self.pending.clear()
        elif key in ("up", "k", "down", "j"):
            self.move(-1 if key in ("up", "k") else 1)
        elif key == "space" and self.selected:
            self.pending ^= {self.selected}
        elif key == "enter":
            self.apply_pending()
        elif key == "x":
            self.ask_run()
        elif key == "l" and self.selected:
            self.view, self.log_offset = "log", 0
        elif key == "e":
            self.edit_selected()
        elif key == "c":
            clear_history()
            self.say("run history cleared")
        elif key == "a":
            self.ask_scheduler()
        return True

    def handle_log(self, key):
        if key in ("esc", "q", "l"):
            self.view = "dashboard"
        elif key in ("up", "k"):
            self.log_offset += 1
        elif key in ("down", "j"):
            self.log_offset = max(0, self.log_offset - 1)
        elif key == "g":
            self.log_offset = 0
        elif key == "x":
            self.ask_run()
        elif key == "e":
            self.edit_selected()
        return True

    def move(self, step):
        names = [job["name"] for job in self.jobs]
        if not names:
            return
        index = names.index(self.selected) if self.selected in names else 0
        self.selected = names[(index + step) % len(names)]

    def apply_pending(self):
        if not self.pending:
            return
        enabled = {job["name"]: job["enabled"] for job in self.jobs}
        changes = []
        for name in sorted(self.pending):
            set_enabled(name, not enabled[name])
            changes.append(f"{name} {'disabled' if enabled[name] else 'enabled'}")
        self.pending.clear()
        self.say(" · ".join(changes))

    def ask_run(self):
        job = self.selected_job()
        if not job:
            return
        if job["error"]:
            self.say(f"{job['name']}: {job['error']}", "red")
        elif job_status(job, self.state) == "running":
            self.say(f"{job['name']} is already running", "yellow")
        else:
            name = job["name"]
            self.confirm = (f"run {name} now?", lambda: self.run_job(name))

    def run_job(self, name):
        spawn_run(name, "panel")
        self.say(f"▶ {name} started")
        time.sleep(0.3)

    def ask_scheduler(self):
        if self.scheduler_active:
            self.confirm = ("REMOVE the scheduler? no job will run on its own", self.toggle_scheduler)
        else:
            self.confirm = ("install the scheduler?", self.toggle_scheduler)

    def toggle_scheduler(self):
        try:
            if self.scheduler_active:
                uninstall()
                self.say("scheduler removed · jobs only run manually", "yellow")
            else:
                install()
                self.say("scheduler installed · jobs run on schedule again")
        except RuntimeError as error:
            self.say(f"scheduler error: {error}", "red")

    def edit_selected(self):
        job = self.selected_job()
        if not job:
            return
        path = str(job["dir"] / "prompt.md")
        command = editor_command()
        if os.path.basename(command[0]) in GUI_EDITORS:
            subprocess.Popen(command + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.say(f"opening {job['name']}/prompt.md in {os.path.basename(command[0])}")
            return
        self.leave_screen()
        try:
            subprocess.run(command + [path])
        finally:
            self.enter_screen()
