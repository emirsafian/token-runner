"""Low-level rendering helpers shared across the package: ANSI escapes, colour
math, the speed gradient, and terminal size."""
import os

ESC = "\x1b"
RESET = ESC + "[0m"
BOLD = ESC + "[1m"
DIM = ESC + "[2m"
ALT_ON = ESC + "[?1049h" + ESC + "[?25l"     # alt screen + hide cursor
ALT_OFF = ESC + "[?25h" + ESC + "[?1049l"    # show cursor + restore screen


def fg(rgb, text):
    r, g, b = rgb
    return f"{ESC}[38;2;{r};{g};{b}m{text}{RESET}"


def clampi(v, a, b):
    return a if v < a else b if v > b else v


def pack(r, g, b):
    return (clampi(int(r), 0, 255) << 16) | (clampi(int(g), 0, 255) << 8) | clampi(int(b), 0, 255)


def shade(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


def lerpc(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def speedT(rate, redline):
    return (min(rate, redline) / redline) ** 0.6


# speed -> colour gradient (idle slate -> mint -> sky -> amber -> orange -> rose)
STOPS = [
    (0.00, (96, 108, 130)),
    (0.16, (78, 222, 170)),
    (0.40, (96, 200, 255)),
    (0.62, (250, 210, 90)),
    (0.82, (255, 142, 60)),
    (1.00, (255, 78, 120)),
]


def grad(t):
    """Map t in [0,1] to an RGB colour along the speed gradient."""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    for i in range(len(STOPS) - 1):
        p0, c0 = STOPS[i]
        p1, c1 = STOPS[i + 1]
        if t <= p1:
            f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return tuple(round(c0[j] + (c1[j] - c0[j]) * f) for j in range(3))
    return STOPS[-1][1]


def get_size():
    try:
        sz = os.get_terminal_size()
        return sz.columns, sz.lines
    except OSError:
        return 80, 24
