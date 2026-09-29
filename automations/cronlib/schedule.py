import datetime as dt
import re

UNITS = {"m": 1, "h": 60, "d": 1440}
DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}


def parse_datetime(raw):
    return dt.datetime.fromisoformat(raw.strip().replace("T", " ")).replace(second=0, microsecond=0)


def parse_delay(raw):
    match = re.fullmatch(r"(\d+)\s*([mhd])", raw.strip())
    if not match:
        raise ValueError(f"invalid interval: {raw} (use 30m, 2h, 1d)")
    return dt.timedelta(minutes=int(match.group(1)) * UNITS[match.group(2)])


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
            raise ValueError(f"cron field out of range: {expr}")
        values.update(range(start, end + 1, step))
    return values


class Cron:
    def __init__(self, expr):
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError(f"invalid cron: {expr}")
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
            self.label = f"once {self.at:%m/%d %H:%M}"
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
                raise ValueError(f"invalid schedule: {raw}")
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
