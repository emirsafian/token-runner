"""The game HUD: the two-line stat bar worn over the running view, plus the
achievement toasts and the dashboard footer.
"""
from .render import ESC, fg, grad, speedT, shade, clampi
from .fmt import human, rate_str, dur
from .biomes import BIOMES, gait_of
from .engine import HOUR, DAY

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
            ("   ", None), ("b", KEYC), (" scene", MUTE), ("   ", None), ("u", KEYC), (" usage", MUTE),
            ("   ", None), ("h", KEYC), (" hi-res", MUTE), ("   ", None), ("q", KEYC), (" quit", MUTE)]
    line_b = _fit_row(W, chunks, ctrl, ("   ·   ", BORDERC))
    return [line_a, line_b]


def banner_line(W, text, col):
    """A full-width achievement toast bar (centered bold text on a dark-accent band)."""
    inner = text[:max(0, W - 2)]
    pad = max(0, (W - len(inner)) // 2)
    band = " " * pad + inner + " " * max(0, W - pad - len(inner))
    bg = shade(col, 0.3)
    return (f"{ESC}[48;2;{bg[0]};{bg[1]};{bg[2]}m{ESC}[1m{ESC}[38;2;245;248;255m" + band + ESC + "[0m")


# -- the two vertical usage gauges, worn bottom-left over the running scene ----
# They aren't a widget stamped on top: the bars are alpha-blended straight into
# the pixel canvas (like the blaze glow / god rays), so the runner and the world
# keep moving *behind* them, and the little labels sit on the scene's own colour
# with nothing opaque added. Each bar fills *progressively* with what you've
# actually used this window, drawn in the top speed bar's heatmap gradient — cool
# and low when you're light, climbing warm as the window fills. There's no
# locally knowable hard quota, so "full" is scaled to your own heaviest recent
# usage (see the README), not a billing limit.
G_SLOT = 6                            # character columns budgeted per gauge (bar + its labels)
G_GAP = 2                             # gap between the two gauges
G_MARG = 1                            # left margin
G_BARW = 4                            # bar width in columns (centred in the slot)
G_TRACK = (150, 162, 186)            # the faint empty "tube" above the fill
G_FILL_A = 0.78                       # fill opacity (scene still bleeds through)
G_TRACK_A = 0.14                       # empty-track opacity (barely there)


def _g_center(text, slot):
    text = text[:slot]
    return (slot - len(text)) // 2


def draw_usage_gauges(cv, sess, week):
    """Composite the two translucent usage gauges into the canvas, bottom-left:
    SESSION (the 5h block) and WEEK (the trailing 7 days). Each argument is a
    ``(frac, reset_s, active, label)`` tuple — ``frac`` in [0,1] fills the bar
    bottom-up in the speed-bar heatmap gradient, ``label`` is the line under it
    (a real "3%" from the live limits, or the token total from the local
    estimate). The source doesn't matter here. Returns the text metadata (title /
    reset countdown / label, per gauge) for `gauge_overlay` to lay on top, or
    None if the canvas is too small to wear them cleanly."""
    W, H = cv.w, cv.h
    CH = H // 2
    if W < 64 or CH < 16:
        return None

    gauge_h = clampi(int(round(CH * 0.30)), 9, CH - 1)   # compact: ~a third of the scene height
    bar_rows = gauge_h - 3                              # 3 label rows: title, reset, total
    if bar_rows < 5:
        return None
    title_row = CH - 3 - bar_rows
    reset_row = CH - 2 - bar_rows
    total_row = CH - 1
    if title_row < 0:
        return None
    y_bot = 2 * (CH - 2) + 1                            # bottom pixel of the bar (= H - 3)
    y_top = 2 * (CH - 1 - bar_rows)                     # top pixel of the bar
    bar_px = y_bot - y_top + 1

    gauges = [
        ("SESS", sess, HOUR, G_MARG),
        ("WEEK", week, DAY, G_MARG + G_SLOT + G_GAP),
    ]
    items = []
    for name, (frac, reset, active, label), soon_below, slot_col in gauges:
        bx0 = slot_col + (G_SLOT - G_BARW) // 2
        fill_px = int(round(clampi(frac, 0.0, 1.0) * bar_px))
        if frac > 0 and fill_px == 0:                  # keep a visible sliver for small-but-nonzero use
            fill_px = 1
        for i in range(bar_px):                        # i = 0 at the bottom
            y = y_bot - i
            if i < fill_px:
                col, a = grad(i / max(1, bar_px - 1)), G_FILL_A
            else:
                col, a = G_TRACK, G_TRACK_A
            for x in range(bx0, bx0 + G_BARW):
                cv.shade_px(x, y, col, a)

        soon = active and reset < soon_below
        reset_txt = dur(reset) if active else "idle"
        items.append((title_row, slot_col, name, LABEL))
        items.append((reset_row, slot_col, reset_txt, (255, 206, 112) if soon else WHITE))
        items.append((total_row, slot_col, label, WHITE))
    return {"items": items, "width": G_MARG + G_SLOT * 2 + G_GAP}


def gauge_overlay(cv, meta, hud_h):
    """Absolute-positioned ANSI overlay for the gauge labels. Each glyph is
    backed by the scene colour behind it (lightly darkened just for legibility),
    so the text floats on the running world instead of on an opaque band. `hud_h`
    is the number of HUD lines above the scene image."""
    if not meta:
        return ""
    out = []
    for row, slot_col, text, fgc in meta["items"]:
        text = text[:G_SLOT]
        col0 = slot_col + _g_center(text, G_SLOT)
        abs_row = hud_h + 1 + row
        parts = [f"{ESC}[{abs_row};{col0 + 1}H"]
        last = None
        for i, ch in enumerate(text):
            sr, sg, sb = cv.cell_rgb(col0 + i, row)
            br, bg, bb = sr * 45 >> 7, sg * 45 >> 7, sb * 45 >> 7   # ~35% of the scene colour
            if (br, bg, bb) != last:
                parts.append(f"{ESC}[38;2;{fgc[0]};{fgc[1]};{fgc[2]};48;2;{br};{bg};{bb}m")
                last = (br, bg, bb)
            parts.append(ch)
        parts.append(ESC + "[0m")
        out.append("".join(parts))
    return "".join(out)


def dash_footer(W):
    """The footer shown while the dashboard is on screen."""
    return ("  " + fg(KEYC, "tab") + fg(MUTE, " ⇄ run") + fg(BORDERC, "   ·   ")
            + fg(KEYC, "q") + fg(MUTE, " quit") + fg(BORDERC, "   ·   ")
            + fg(MUTE, "live dashboard view"))
