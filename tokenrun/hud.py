"""The game HUD: the two-line stat bar worn over the running view, plus the
achievement toasts and the dashboard footer.
"""
from .render import ESC, fg, grad, speedT, shade, clampi
from .fmt import human, rate_str, dur
from .biomes import BIOMES, gait_of
from .engine import HOUR

# HUD palette
MUTE = (120, 130, 150)
LABEL = (170, 184, 205)
WHITE = (232, 236, 244)
BORDERC = (78, 88, 108)        # bar empties / separators
THINKC = (150, 140, 235)       # thinking accent
LIVEC = (118, 210, 150)        # live dot
KEYC = (150, 200, 255)         # key hints
SPIN = "◐◓◑◒"


def _seglen(segs):
    return sum(len(t) for t, _ in segs)


def _segstr(segs):
    return "".join(fg(c, t) if c else t for t, c in segs)


def _row(W, left, right):
    """One line: left group + right group, justified to width W."""
    gap = max(1, W - _seglen(left) - _seglen(right))
    return _segstr(left) + " " * gap + _segstr(right)


def _fit_row(W, chunks, right, sep):
    """Justified row that keeps `right`, then includes as many priority `chunks`
    (joined by `sep`) on the left as fit, so it degrades on narrow terminals."""
    rlen = _seglen(right)
    left = []
    used = 0
    for ch in chunks:
        add = _seglen(ch) + (_seglen([sep]) if left else 0)
        if used + add + rlen + 1 <= W:
            if left:
                left.append(sep)
            left += ch
            used += add
    return _row(W, left, right)


def _bar_segs(rate, redline, n, pb=0.0):
    """The speed bar, the same gradient 'needle' as the dashboard, with a
    bright marker at your personal best to chase."""
    n = max(1, n)
    fill = int(round(min(1.0, rate / redline) * n))
    segs = [("█", grad(i / max(1, n - 1))) if i < fill else ("░", BORDERC) for i in range(n)]
    if pb > 0:
        segs[clampi(int(round(min(1.0, pb / redline) * (n - 1))), 0, n - 1)] = ("┃", (255, 255, 255))
    return segs


def game_hud(W, rate, thinking, live, dist, blk, total7d, biome, redline, frame_n,
             streak=0, pb=0.0, ghost_gap=0.0, has_ghost=False):
    """Two-line game-style stat overlay: the speed 'health bar' on top of the
    live numbers + records, the same engine, worn like a game HUD."""
    b = BIOMES[biome]
    col = grad(speedT(rate, redline)) if rate > 0.5 else MUTE
    gait = gait_of(rate, thinking).upper()

    # line A, hero stat: live speed + gait + the gradient speed bar (PB marker) + status
    if thinking:
        status = [(SPIN[frame_n % 4] + " ", THINKC), ("THINKING", THINKC)]
    elif live:
        status = [("● ", LIVEC), ("LIVE", LABEL)]
    else:
        status = [("○ ", MUTE), ("IDLE", MUTE)]
    head = [(rate_str(rate), col), (" tok/s", MUTE),
            ("   ", None), (gait.ljust(5), col), ("  ", None)]
    barw = clampi(W - _seglen(head) - _seglen(status) - 2, 10, 96)
    line_a = _row(W, head + _bar_segs(rate, redline, barw, pb), status)

    # line B, numbers + records + the view toggle (drops trailing stats if narrow)
    total5h, reset, active = blk[3], blk[4], blk[5]
    reset_seg = ((f"◷ {dur(reset)}", grad(0.62) if (active and reset < HOUR) else LABEL)
                 if active else ("◷ idle", MUTE))
    chunks = [[("5H ", MUTE), (human(total5h), WHITE), ("  ", None), reset_seg]]
    if streak > 0:
        chunks.append([("STREAK ", MUTE), (f"{streak}d", (255, 184, 92))])
    chunks.append([("DIST ", MUTE), (human(dist), LABEL)])
    if has_ghost:
        gtext = ("+" + human(ghost_gap)) if ghost_gap >= 0 else ("-" + human(-ghost_gap))
        chunks.append([("vs Y'DAY ", MUTE), (gtext, LIVEC if ghost_gap >= 0 else (235, 120, 120))])
    chunks.append([(biome, b["accent"])])
    if pb > 0:
        chunks.append([("PB ", MUTE), (rate_str(pb), (180, 220, 255))])
    chunks.append([("7D ", MUTE), (human(total7d), LABEL)])
    ctrl = [("tab", KEYC), (" ⇄ dash", MUTE), ("   ", None), ("c", KEYC), (" companion", MUTE),
            ("   ", None), ("b", KEYC), (" scene", MUTE), ("   ", None), ("h", KEYC), (" hi-res", MUTE),
            ("   ", None), ("q", KEYC), (" quit", MUTE)]
    line_b = _fit_row(W, chunks, ctrl, ("   ·   ", BORDERC))
    return [line_a, line_b]


def banner_line(W, text, col):
    """A full-width achievement toast bar (centered bold text on a dark-accent band)."""
    inner = text[:max(0, W - 2)]
    pad = max(0, (W - len(inner)) // 2)
    band = " " * pad + inner + " " * max(0, W - pad - len(inner))
    bg = shade(col, 0.3)
    return (f"{ESC}[48;2;{bg[0]};{bg[1]};{bg[2]}m{ESC}[1m{ESC}[38;2;245;248;255m" + band + ESC + "[0m")


def dash_footer(W):
    """The footer shown while the dashboard is on screen."""
    return ("  " + fg(KEYC, "tab") + fg(MUTE, " ⇄ run") + fg(BORDERC, "   ·   ")
            + fg(KEYC, "q") + fg(MUTE, " quit") + fg(BORDERC, "   ·   ")
            + fg(MUTE, "live dashboard view"))
