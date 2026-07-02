"""Reads Claude Code's local transcripts and tracks the last 7 days of usage.

Everything the views show (live tok/s, the 5-hour block, the 7-day window) is
derived here. It only reads local files; nothing leaves the machine.
"""
import os
import glob
import json
import math
import time
from datetime import datetime

HOME = os.path.expanduser("~")
DEFAULT_DIR = os.path.join(HOME, ".claude", "projects")

HOUR = 3600
DAY = 86400
WEEK = 7 * DAY
BLOCK = 5 * HOUR            # Claude's 5-hour session window


class Engine:
    """Tails Claude Code transcripts and keeps the last 7 days of usage."""

    def __init__(self, root):
        self.root = root
        self.offsets = {}        # path -> bytes consumed
        self.seen = set()        # (message.id, requestId) dedup keys
        self.msgs = []           # (ts, out, in, cache_create, cache_read), last 7d
        self.last_mtime = 0.0    # newest file mtime seen (activity detector)
        self.tail_role = {}      # path -> "user"/"assistant" of last message

    def _files(self):
        cutoff = time.time() - WEEK
        out = []
        try:
            paths = glob.glob(os.path.join(self.root, "**", "*.jsonl"),
                              recursive=True)
        except OSError:
            return out
        for p in paths:
            try:
                m = os.path.getmtime(p)
            except OSError:
                continue
            if m >= cutoff:
                out.append(p)
                if m > self.last_mtime:
                    self.last_mtime = m
        return out

    def _consume_line(self, line, path):
        # cheap pre-filter before the json parse
        if '"assistant"' not in line and '"type":"user"' not in line:
            return
        try:
            o = json.loads(line)
        except ValueError:
            return
        t = o.get("type")
        m = o.get("message")
        if t == "user":
            if isinstance(m, dict):
                self.tail_role[path] = "user"       # a turn is awaiting its reply
            return
        if t != "assistant":
            return
        if isinstance(m, dict):
            self.tail_role[path] = "assistant"      # reply landed → awaiting user
        u = (m or {}).get("usage")
        if not u or m.get("model") == "<synthetic>":
            return
        key = (m.get("id"), o.get("requestId"))
        if key in self.seen:
            return
        self.seen.add(key)
        ts = o.get("timestamp")
        if not ts:
            return
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return
        out = u.get("output_tokens", 0) or 0
        inp = u.get("input_tokens", 0) or 0
        cc = u.get("cache_creation_input_tokens", 0) or 0
        cr = u.get("cache_read_input_tokens", 0) or 0
        self.msgs.append((dt.timestamp(), out, inp, cc, cr))

    def poll(self):
        """Read any newly appended transcript data."""
        for path in self._files():
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            off = self.offsets.get(path, 0)
            if size < off:                  # file rotated/truncated
                off = 0
            if size == off:
                continue
            try:
                with open(path, "rb") as fh:
                    fh.seek(off)
                    chunk = fh.read(size - off)
            except OSError:
                continue
            nl = chunk.rfind(b"\n")         # only whole lines
            if nl == -1:
                continue
            self.offsets[path] = off + nl + 1
            text = chunk[:nl + 1].decode("utf-8", "replace")
            for line in text.splitlines():
                self._consume_line(line, path)
        # prune to last 7 days
        cutoff = time.time() - WEEK
        if self.msgs:
            self.msgs = [m for m in self.msgs if m[0] >= cutoff]

    def in_flight(self, now):
        """True if the active session has a user turn still awaiting its reply
        (Claude is thinking / generating, nothing is written until it lands)."""
        best, bm = None, -1.0
        for p in self.tail_role:
            try:
                mt = os.path.getmtime(p)
            except OSError:
                continue
            if mt > bm:
                bm, best = mt, p
        if best is None or now - bm > 900:          # idle/abandoned > 15 min
            return False
        return self.tail_role.get(best) == "user"

    # -- metrics --------------------------------------------------------------
    def ewma_rate(self, now, tau):
        """Exponentially-weighted output tokens/sec, the live speedometer."""
        horizon = now - 6 * tau
        acc = 0.0
        for t, out, *_ in self.msgs:
            if t < horizon or out == 0:
                continue
            acc += out * math.exp(-(now - t) / tau)
        return acc / tau

    def window(self, now, span):
        """(out, in, cache, total) summed over the trailing `span` seconds."""
        out = inp = cc = cr = 0
        lo = now - span
        for t, o, i, c, r in self.msgs:
            if t >= lo:
                out += o; inp += i; cc += c; cr += r
        return out, inp, cc + cr, out + inp + cc + cr

    def block(self, now):
        """Current 5h block: (out, in, cache, total, resets_in_s, active)."""
        if not self.msgs:
            return 0, 0, 0, 0, 0.0, False
        times = sorted(m[0] for m in self.msgs)
        start = last = times[0]
        for t in times:
            if t - last >= BLOCK or t - start >= BLOCK:
                start = last = t
            else:
                last = t
        end = start + BLOCK
        active = now < end
        out = inp = cc = cr = 0
        if active:
            for t, o, i, c, r in self.msgs:
                if t >= start:
                    out += o; inp += i; cc += c; cr += r
        return out, inp, cc + cr, out + inp + cc + cr, max(0.0, end - now), active

    def block_peak(self, now):
        """Largest 5h-block total (out+in+cache) across the trailing 7 days.
        The session gauge fills against this, so the bar shows *this* block's
        consumption as a fraction of your heaviest recent block — a real,
        self-calibrating scale, since there's no locally knowable hard quota.
        Blocks are anchored exactly like `block()` so the current one lines up."""
        if not self.msgs:
            return 0
        rows = sorted(self.msgs, key=lambda m: m[0])
        peak = acc = 0
        start = last = rows[0][0]
        for t, o, i, c, r in rows:
            if t - last >= BLOCK or t - start >= BLOCK:
                if acc > peak:
                    peak = acc
                start = last = t
                acc = 0
            last = t
            acc += o + i + c + r
        return acc if acc > peak else peak

    def day_peak(self, now):
        """Largest single local-day total across the trailing 7 days. The week
        gauge scales against 7x this — a 'full' week being roughly every day as
        heavy as your heaviest — so its bar sits progressively, not pinned."""
        tot = {}
        for t, o, i, c, r in self.msgs:
            lt = time.localtime(t)
            key = (lt.tm_year, lt.tm_yday)
            tot[key] = tot.get(key, 0) + o + i + c + r
        return max(tot.values()) if tot else 0

    def week_reset_in(self, now):
        """Seconds until the oldest usage inside the trailing 7-day window ages
        out. Unlike the 5h block, the week is a plain rolling sum with no
        session-style anchor, so its "reset" is the moment the total is next
        due to shrink, not a full drop to zero."""
        oldest = None
        lo = now - WEEK
        for t, *_ in self.msgs:
            if t >= lo and (oldest is None or t < oldest):
                oldest = t
        if oldest is None:
            return 0.0
        return max(0.0, oldest + WEEK - now)

    def buckets(self, now, span, n):
        """Per-bucket average output tok/s over the trailing `span` seconds."""
        if n <= 0:
            return []
        size = span / n
        acc = [0] * n
        lo = now - span
        for t, out, *_ in self.msgs:
            if t < lo or out == 0:
                continue
            i = int((t - lo) / size)
            if i >= n:
                i = n - 1
            if i < 0:
                i = 0
            acc[i] += out
        return [a / size for a in acc]
