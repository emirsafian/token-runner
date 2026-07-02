"""Small number and time formatters shared by the dashboard and the HUD."""


def human(n):
    n = float(n)
    if n < 1000:
        return str(int(n))
    if n < 1e6:
        return f"{n / 1e3:.1f}K"
    if n < 1e9:
        return f"{n / 1e6:.1f}M"
    return f"{n / 1e9:.1f}B"


def rate_str(r):
    return str(int(round(r))) if r < 1000 else f"{r / 1000:.1f}k"


def dur(s):
    s = int(s)
    if s <= 0:
        return "now"
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d{h:02d}h"
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m"
    return f"{s}s"
