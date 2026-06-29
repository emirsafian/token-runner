"""The half-block pixel canvas: a buffer rendered as truecolor upper-half blocks
(two stacked pixels per character cell), plus a stdlib PNG writer for checking
frames offline.
"""
import math
from .render import pack, ESC


class Canvas:
    """A pixel buffer rendered as truecolor half-blocks (2 px per character row)."""

    def __init__(self, w, h):
        self.w = w
        self.h = h if h % 2 == 0 else h - 1
        self.buf = [0] * (self.w * self.h)
        self._sgr = {}

    def fill_template(self, tpl):
        self.buf = tpl[:]

    def px(self, x, y, c):
        x = int(x); y = int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.buf[y * self.w + x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.px(x, y, c)

    def disc(self, cx, cy, r, c):
        r = max(0.5, r); rr = r * r
        for dy in range(int(-r), int(r) + 1):
            for dx in range(int(-r), int(r) + 1):
                if dx * dx + dy * dy <= rr:
                    self.px(cx + dx, cy + dy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        rx = max(0.5, rx); ry = max(0.5, ry)
        for dy in range(int(-ry), int(ry) + 1):
            xx = rx * math.sqrt(max(0.0, 1 - (dy / ry) ** 2))
            for dx in range(int(-xx), int(xx) + 1):
                self.px(cx + dx, cy + dy, c)

    def thick(self, x0, y0, x1, y1, t, c):
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        r = max(0, t // 2)
        for i in range(n + 1):
            f = i / n
            self.disc(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, r, c)

    def shadow_ground(self, x, y, rx, ry):
        rx = max(0.5, rx); ry = max(0.5, ry)
        for dy in range(int(-ry), int(ry) + 1):
            xx = rx * math.sqrt(max(0.0, 1 - (dy / ry) ** 2))
            yy = int(y + dy)
            for dx in range(int(-xx), int(xx) + 1):
                xi = int(x + dx)
                if 0 <= xi < self.w and 0 <= yy < self.h:
                    i = yy * self.w + xi
                    p = self.buf[i]
                    self.buf[i] = pack(((p >> 16) & 255) * 0.55, ((p >> 8) & 255) * 0.55, (p & 255) * 0.55)

    def _pref(self, top, bot):
        k = (top, bot)
        s = self._sgr.get(k)
        if s is None:
            s = f"{ESC}[38;2;{(top>>16)&255};{(top>>8)&255};{top&255};48;2;{(bot>>16)&255};{(bot>>8)&255};{bot&255}m"
            self._sgr[k] = s
        return s

    def render_rows(self):
        rows = []
        W, buf = self.w, self.buf
        for cy in range(self.h // 2):
            i0 = (2 * cy) * W
            i1 = (2 * cy + 1) * W
            out = []
            prev = None
            cnt = 0
            for x in range(W):
                pair = (buf[i0 + x], buf[i1 + x])
                if pair == prev:
                    cnt += 1
                else:
                    if prev is not None:
                        out.append(self._pref(prev[0], prev[1])); out.append("▀" * cnt)
                    prev = pair; cnt = 1
            out.append(self._pref(prev[0], prev[1])); out.append("▀" * cnt); out.append(ESC + "[0m")
            rows.append("".join(out))
        return rows


def write_png(path, w, h, buf, scale=5):
    """Dump the pixel buffer to an RGB PNG (pure stdlib) so I can see frames."""
    import zlib
    import struct
    raw = bytearray()
    for y in range(h):
        base = y * w
        line = bytearray()
        for x in range(w):
            c = buf[base + x]
            line += bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255)) * scale
        for _ in range(scale):
            raw.append(0)
            raw += line
    comp = zlib.compress(bytes(raw), 6)

    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", w * scale, h * scale, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
