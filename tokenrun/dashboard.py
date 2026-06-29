"""The speedometer dashboard (flip to it with TAB): the big tok/s number, the
needle, sparklines, and your 5-hour / 7-day totals.
"""
from datetime import datetime
from .render import ESC, fg, grad
from .fmt import human, rate_str, dur
from .engine import WEEK, BLOCK, HOUR

# dashboard palette
BORDER = (66, 74, 92)
LABEL = (138, 148, 166)
MUTE = (96, 104, 122)
WHITE = (226, 230, 240)
THINK = (150, 140, 235)      # in-flight "thinking" accent
SPIN = "◐◓◑◒"


DIGITS = {
    "0": ["███", "█ █", "█ █", "█ █", "███"],
    "1": ["  █", "  █", "  █", "  █", "  █"],
    "2": ["███", "  █", "███", "█  ", "███"],
    "3": ["███", "  █", "███", "  █", "███"],
    "4": ["█ █", "█ █", "███", "  █", "  █"],
    "5": ["███", "█  ", "███", "  █", "███"],
    "6": ["███", "█  ", "███", "█ █", "███"],
    "7": ["███", "  █", "  █", "  █", "  █"],
    "8": ["███", "█ █", "███", "█ █", "███"],
    "9": ["███", "█ █", "███", "  █", "███"],
    ".": ["   ", "   ", "   ", "   ", " █ "],
    "k": ["   ", "█ █", "██ ", "█ █", "█ █"],
    "M": ["   ", "█ █", "███", "█ █", "█ █"],
    " ": ["   ", "   ", "   ", "   ", "   "],
}


def big_rows(text, scale=1):
    """Return 5 equal-width strings rendering `text` in big block glyphs."""
    rows = ["", "", "", "", ""]
    gap = " " * scale
    for ch in text:
        g = DIGITS.get(ch, DIGITS[" "])
        for r in range(5):
            cell = "".join(c * scale for c in g[r]) if scale > 1 else g[r]
            rows[r] += cell + gap
    return [r[:-scale] for r in rows]   # drop trailing gap, keep rows equal


SPARK = "▁▂▃▄▅▆▇█"


def sparkline(vals, redline):
    """Return list of (char, rgb), auto-scaled height, speed-coloured."""
    if not vals:
        return []
    peak = max(vals)
    out = []
    for v in vals:
        if peak <= 0 or v <= 0:
            out.append(("▁", MUTE))
            continue
        lvl = int(round(v / peak * (len(SPARK) - 1)))
        ct = (min(v, redline) / redline) ** 0.6
        out.append((SPARK[lvl], grad(ct)))
    return out


class Frame:
    """Builds the boxed dashboard lines."""

    def __init__(self, boxw):
        self.boxw = boxw
        self.cw = boxw - 4          # inner content width
        self.lines = []

    def _emit(self, parts):
        """parts: list of (text, rgb|None). Pads to inner width, adds border."""
        raw = "".join(p[0] for p in parts)
        if len(raw) > self.cw:                      # safety clip (uncoloured)
            self.lines.append(fg(BORDER, "│ ") + raw[:self.cw] + fg(BORDER, " │"))
            return
        body = "".join(fg(p[1], p[0]) if p[1] else p[0] for p in parts)
        pad = " " * (self.cw - len(raw))
        self.lines.append(fg(BORDER, "│ ") + body + pad + fg(BORDER, " │"))

    def rule(self, top=False, bottom=False):
        if top:
            self.lines.append(fg(BORDER, "╭" + "─" * (self.boxw - 2) + "╮"))
        elif bottom:
            self.lines.append(fg(BORDER, "╰" + "─" * (self.boxw - 2) + "╯"))
        else:
            self.lines.append(fg(BORDER, "├" + "─" * (self.boxw - 2) + "┤"))

    def blank(self):
        self._emit([("", None)])

    def center(self, parts):
        """Center the given parts within the inner width."""
        raw = sum(len(p[0]) for p in parts)
        pad = max(0, (self.cw - raw) // 2)
        self._emit([(" " * pad, None)] + parts)

    def kv_right(self, left_parts, right_parts):
        """Left-aligned parts, right-aligned parts, on one line."""
        lraw = sum(len(p[0]) for p in left_parts)
        rraw = sum(len(p[0]) for p in right_parts)
        gap = self.cw - lraw - rraw
        if gap < 1:
            gap = 1
        self._emit(left_parts + [(" " * gap, None)] + right_parts)

    def distribute(self, groups):
        """Spread groups of parts evenly across the full inner width."""
        widths = [sum(len(p[0]) for p in g) for g in groups]
        total = sum(widths)
        n = len(groups)
        parts = []
        if n <= 1 or total + 3 * (n - 1) >= self.cw:     # too tight: compact join
            for i, g in enumerate(groups):
                if i:
                    parts.append(("   ", None))
                parts += g
            self._emit(parts)
            return
        gap = (self.cw - total) // (n - 1)
        for i, g in enumerate(groups):
            if i:
                parts.append((" " * gap, None))
            parts += g
        self._emit(parts)


def build(engine, cfg, now, frame_n):
    cap = getattr(cfg, "max_width", 0) or 100000
    boxw = min(cap, max(46, cfg.width - 2))
    f = Frame(boxw)
    cw = f.cw

    rate = engine.ewma_rate(now, cfg.tau)
    color_t = (min(rate, cfg.redline) / cfg.redline) ** 0.6
    col = grad(color_t)

    # window metrics
    b_out, b_in, b_cache, b_tot, reset_in, b_active = engine.block(now)
    w_out, w_in, w_cache, w_tot = engine.window(now, WEEK)
    span5 = engine.buckets(now, BLOCK, cw)
    span7 = engine.buckets(now, WEEK, cw)
    peak5 = max(span5) if span5 else 0

    working = engine.in_flight(now)
    live = (now - engine.last_mtime) < 25
    clock = datetime.now().strftime("%H:%M:%S")

    # ---- header (one status light: thinking spinner / live ● / idle ○)
    f.rule(top=True)
    if working:
        dot = (SPIN[frame_n % 4] + " ", THINK)
    elif live:
        dot = ("● ", grad(0.2) if frame_n % 2 == 0 else grad(0.16))
    else:
        dot = ("○ ", MUTE)
    f.kv_right(
        [dot, ("CLAUDE CODE", WHITE), ("  ·  ", BORDER), ("token monitor", LABEL)],
        [(clock, LABEL)],
    )
    f.blank()

    # ---- big speed number (centered centerpiece, unit beside it)
    digits = big_rows(rate_str(rate), scale=2)
    blockw = len(digits[0])
    lead = max(0, (cw - blockw - 8) // 2)
    for r in range(5):
        parts = [(" " * lead, None), (digits[r], col)]
        if r == 2:
            parts.append(("  tok/s", LABEL))
        f._emit(parts)
    if working:
        sub = (SPIN[frame_n % 4] + " thinking…", THINK)
    elif rate > 0.5:
        sub = ("OUTPUT SPEED", MUTE)
    else:
        sub = ("IDLE", MUTE)
    f.center([sub])
    f.blank()

    # ---- needle bar (centered, width capped so it doesn't stretch absurdly)
    barw = min(cw - 16, 72)
    if barw < 8:
        barw = 8
    fill = int(round(min(1.0, rate / cfg.redline) * barw))
    bar = []
    for i in range(barw):
        if i < fill:
            bar.append(("█", grad(i / max(1, barw - 1))))
        else:
            bar.append(("░", BORDER))
    f.center(bar + [("  ", None), (f"{rate_str(rate):>4}", col), ("/s", MUTE)])
    f.blank()

    # ---- 5h speed sparkline
    f.kv_right([("speed", LABEL), (" · last 5h", MUTE)],
               [("peak ", MUTE), (f"{rate_str(peak5)}", grad((min(peak5, cfg.redline) / cfg.redline) ** 0.6)), ("/s", MUTE)])
    sl = sparkline(span5, cfg.redline)
    f._emit([("", None)] + sl)
    f.blank()

    # ---- windows
    f.rule()
    reset_txt = (f"resets in {dur(reset_in)}" if b_active else "idle · resets on next use")
    f.kv_right([("5-HOUR WINDOW", WHITE)],
               [(reset_txt, grad(0.62) if (b_active and reset_in < HOUR) else LABEL)])
    f.distribute([
        [(human(b_in), LABEL), (" in", MUTE)],
        [(human(b_cache), LABEL), (" cache", MUTE)],
        [(human(b_out), grad(0.4)), (" out", MUTE)],
        [(human(b_tot), WHITE), (" total", MUTE)],
    ])
    f.blank()

    f._emit([("LAST 7 DAYS", WHITE)])
    f.distribute([
        [(human(w_in), LABEL), (" in", MUTE)],
        [(human(w_cache), LABEL), (" cache", MUTE)],
        [(human(w_out), grad(0.4)), (" out", MUTE)],
        [(human(w_tot), WHITE), (" total", MUTE)],
    ])
    sl7 = sparkline(span7, cfg.redline)
    f._emit([("", None)] + sl7)
    f.rule(bottom=True)

    # footer hint (tokenrun embeds this view and overrides the hint via cfg.footer_hint)
    hint = getattr(cfg, "footer_hint", None)
    if hint is None:
        hint = (fg(MUTE, "  q quit") + fg(BORDER, "  ·  ")
                + fg(MUTE, f"refresh {cfg.interval:g}s")
                + fg(BORDER, "  ·  ") + fg(MUTE, f"τ {cfg.tau:g}s"))
    f.lines.append(hint)
    return f.lines
