"""Personal best, daily streak, milestones, and the live "ghost of yesterday"
gap. Persisted to ~/.tokenrun.json; all derived from the local transcripts.
"""
import os
import json
import time
import datetime


RECORDS_PATH = os.path.join(os.path.expanduser("~"), ".tokenrun.json")
MILESTONES = [100_000, 250_000, 500_000, 1_000_000, 2_500_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000]


def _ordinal(ts):
    lt = time.localtime(ts)
    return datetime.date(lt.tm_year, lt.tm_mon, lt.tm_mday).toordinal()


class Records:
    """Personal best + daily streak (persisted), plus the live 'ghost of
    yesterday' gap, all derived from the local transcripts; nothing leaves the box."""

    def __init__(self, path=RECORDS_PATH):
        self.path = path
        self.pb_rate = 0.0
        self.streak = 0
        self.longest = 0
        self.last_day = 0
        self.dirty = False
        self.ghost_gap = 0.0          # today's output minus same-time-yesterday's
        self.has_yesterday = False
        self._last_pb = 0.0
        self._fired = set()           # milestones already toasted this block
        self._last_dist = 0.0
        self._load()

    def _load(self):
        try:
            with open(self.path) as fh:
                d = json.load(fh)
            self.pb_rate = float(d.get("pb_rate", 0.0))
            self.streak = int(d.get("streak", 0))
            self.longest = int(d.get("longest", 0))
            self.last_day = int(d.get("last_day", 0))
        except Exception:
            pass

    def save(self, force=False):
        if not (self.dirty or force):
            return
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as fh:
                json.dump({"pb_rate": round(self.pb_rate, 2), "streak": self.streak,
                           "longest": self.longest, "last_day": self.last_day}, fh)
            os.replace(tmp, self.path)
            self.dirty = False
        except Exception:
            pass

    def refresh(self, eng, now):
        """Recompute streak + ghost gap from the engine's 7-day history. Returns
        the new streak count if a fresh day just extended the streak, else None."""
        today = _ordinal(now)
        active = set()
        for t, out, *_ in eng.msgs:
            if out > 0:
                active.add(_ordinal(t))

        def consec(end):
            n = 0
            while (end - n) in active:
                n += 1
            return n

        bumped = None
        if today in active:
            if self.last_day == today:
                pass
            elif self.last_day == today - 1:
                self.streak += 1; self.last_day = today; self.dirty = True; bumped = self.streak
            else:
                self.streak = consec(today); self.last_day = today; self.dirty = True; bumped = self.streak
            if self.streak > self.longest:
                self.longest = self.streak; self.dirty = True
        elif self.last_day == 0:                 # first run, nothing today yet → show y'day's run
            self.streak = consec(today - 1)

        # ghost of yesterday: cumulative output since local midnight vs same time y'day
        lt = time.localtime(now)
        midnight = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
        elapsed = now - midnight
        ymid = midnight - 86400
        today_cum = ycum = 0
        yhad = False
        for t, out, *_ in eng.msgs:
            if t >= midnight:
                today_cum += out
            elif ymid <= t < ymid + 86400:
                yhad = yhad or out > 0
                if t <= ymid + elapsed:
                    ycum += out
        self.ghost_gap = float(today_cum - ycum)
        self.has_yesterday = yhad
        return bumped

    def tick_rate(self, rate, now):
        """Update the all-time PB; return True once when it's genuinely beaten."""
        beat = False
        if rate > self.pb_rate:
            if self.pb_rate > 0 and rate > self.pb_rate + 1.0 and rate > 5 and now - self._last_pb > 6:
                beat = True; self._last_pb = now
            self.pb_rate = rate; self.dirty = True
        return beat

    def check_milestone(self, dist):
        """Return a milestone token-count when `dist` first crosses one (per block)."""
        if dist < self._last_dist - 1000:        # block reset → fresh goals
            self._fired.clear()
        self._last_dist = dist
        hit = None
        for m in MILESTONES:
            if dist >= m and m not in self._fired:
                self._fired.add(m); hit = m
        return hit
