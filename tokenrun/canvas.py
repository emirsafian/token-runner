"""The half-block pixel canvas: a buffer rendered as truecolor upper-half blocks
(two stacked pixels per character cell), plus a stdlib PNG writer for checking
frames offline.

The scene always draws in one square-pixel coordinate system (``w`` wide, ``h``
tall). ``xs`` is a horizontal supersample: with ``xs=2`` the backing buffer is
``2*w`` wide, so curves and edges are sampled at twice the horizontal resolution
and the frame is emitted with 2x2 quadrant glyphs (see ``render_rows_quad``).
Vertical resolution is unchanged — quadrants only buy horizontal detail, which is
the coarser axis under half-blocks. ``xs=1`` is the classic half-block path and
keeps the original renderer's exact output.
"""
import math
from .render import pack, ESC

# Quadrant block glyphs indexed by a 4-bit mask (bit0=TL, 1=TR, 2=BL, 3=BR);
# a set bit means that sub-cell shows the foreground colour, a clear bit the bg.
_QUAD_GLYPH = (
    " ", "▘", "▝", "▀", "▖", "▌", "▞", "▛",
    "▗", "▚", "▐", "▜", "▄", "▙", "▟", "█",
)


class Canvas:
    """A pixel buffer rendered as truecolor half-blocks (2 px per character row),
    or, when ``xs=2``, as 2x2 quadrant blocks for twice the horizontal detail."""

    def __init__(self, w, h, xs=1):
        self.w = w
        self.h = h if h % 2 == 0 else h - 1
        self.xs = xs
        self.pw = w * xs                      # physical buffer width (>= w)
        self.buf = [0] * (self.pw * self.h)
        self._sgr = {}

    def fill_template(self, tpl):
        self.buf = tpl[:]

    def px(self, x, y, c):
        x = int(x); y = int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            base = y * self.pw + x * self.xs
            for k in range(self.xs):
                self.buf[base + k] = c

    def rect(self, x0, y0, x1, y1, c):
        pw = self.pw; buf = self.buf
        px0 = int(x0 * self.xs); px1 = int(x1 * self.xs)
        if px1 < px0:
            px0, px1 = px1, px0
        if px0 < 0:
            px0 = 0
        if px1 >= pw:
            px1 = pw - 1
        for y in range(int(y0), int(y1) + 1):
            if 0 <= y < self.h:
                base = y * pw
                for px in range(px0, px1 + 1):
                    buf[base + px] = c

    def disc(self, cx, cy, r, c):
        r = max(0.5, r); rr = r * r
        if self.xs == 1:
            for dy in range(int(-r), int(r) + 1):
                for dx in range(int(-r), int(r) + 1):
                    if dx * dx + dy * dy <= rr:
                        self.px(cx + dx, cy + dy, c)
            return
        xs = self.xs; pw = self.pw; buf = self.buf; h = self.h
        for dy in range(int(-r), int(r) + 1):
            span = rr - dy * dy
            if span < 0:
                continue
            hx = math.sqrt(span)                          # logical half-width at this row
            y = int(cy + dy)
            if not (0 <= y < h):
                continue
            px0 = int((cx - hx) * xs); px1 = int((cx + hx) * xs)
            if px0 < 0:
                px0 = 0
            if px1 >= pw:
                px1 = pw - 1
            base = y * pw
            for px in range(px0, px1 + 1):
                buf[base + px] = c

    def ellipse(self, cx, cy, rx, ry, c):
        rx = max(0.5, rx); ry = max(0.5, ry)
        if self.xs == 1:
            for dy in range(int(-ry), int(ry) + 1):
                xx = rx * math.sqrt(max(0.0, 1 - (dy / ry) ** 2))
                for dx in range(int(-xx), int(xx) + 1):
                    self.px(cx + dx, cy + dy, c)
            return
        xs = self.xs; pw = self.pw; buf = self.buf; h = self.h
        for dy in range(int(-ry), int(ry) + 1):
            xx = rx * math.sqrt(max(0.0, 1 - (dy / ry) ** 2))
            y = int(cy + dy)
            if not (0 <= y < h):
                continue
            px0 = int((cx - xx) * xs); px1 = int((cx + xx) * xs)
            if px0 < 0:
                px0 = 0
            if px1 >= pw:
                px1 = pw - 1
            base = y * pw
            for px in range(px0, px1 + 1):
                buf[base + px] = c

    def thick(self, x0, y0, x1, y1, t, c):
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        r = max(0, t // 2)
        for i in range(n + 1):
            f = i / n
            self.disc(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, r, c)

    def shadow_ground(self, x, y, rx, ry):
        rx = max(0.5, rx); ry = max(0.5, ry)
        xs = self.xs; pw = self.pw; buf = self.buf; h = self.h
        for dy in range(int(-ry), int(ry) + 1):
            xx = rx * math.sqrt(max(0.0, 1 - (dy / ry) ** 2))
            yy = int(y + dy)
            if not (0 <= yy < h):
                continue
            px0 = int((x - xx) * xs); px1 = int((x + xx) * xs)
            if px0 < 0:
                px0 = 0
            if px1 >= pw:
                px1 = pw - 1
            base = yy * pw
            for px in range(px0, px1 + 1):
                p = buf[base + px]
                buf[base + px] = pack(((p >> 16) & 255) * 0.55, ((p >> 8) & 255) * 0.55, (p & 255) * 0.55)

    def shade_px(self, x, y, rgb, f):
        """Blend rgb into the pixel at logical (x, y) by factor f — used by the
        few effects that tint the existing buffer (god rays, the blaze vignette)."""
        x = int(x); y = int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            r0, g0, b0 = rgb
            base = y * self.pw + x * self.xs
            for k in range(self.xs):
                p = self.buf[base + k]
                self.buf[base + k] = pack(((p >> 16) & 255) * (1 - f) + r0 * f,
                                          ((p >> 8) & 255) * (1 - f) + g0 * f,
                                          (p & 255) * (1 - f) + b0 * f)

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

    def render_rows_quad(self):
        """Emit the buffer as 2x2 quadrant glyphs (xs=2). Each character cell maps
        a 2-wide x 2-tall block of pixels; the four sub-pixels are reduced to two
        colours (the luminance extremes) and the glyph encodes which sub-cells take
        the brighter one. A flat block is a solid █; a block that only varies top vs
        bottom collapses to ▀, i.e. exactly the half-block result — so smooth vertical
        gradients are untouched and the finer detail only shows up at real edges."""
        pw, h, buf = self.pw, self.h, self.buf
        cols = pw >> 1
        G = _QUAD_GLYPH
        rows = []
        for cy in range(h >> 1):
            r0 = (cy << 1) * pw
            r1 = r0 + pw
            out = []
            cur = None
            run = []
            for cx in range(cols):
                i0 = r0 + (cx << 1); i1 = r1 + (cx << 1)
                tl = buf[i0]; tr = buf[i0 + 1]; bl = buf[i1]; br = buf[i1 + 1]
                if tl == tr and tl == bl and tl == br:
                    fg = bg = tl; g = "█"
                else:
                    la = ((tl >> 16) & 255) * 299 + ((tl >> 8) & 255) * 587 + (tl & 255) * 114
                    lb = ((tr >> 16) & 255) * 299 + ((tr >> 8) & 255) * 587 + (tr & 255) * 114
                    lc = ((bl >> 16) & 255) * 299 + ((bl >> 8) & 255) * 587 + (bl & 255) * 114
                    ld = ((br >> 16) & 255) * 299 + ((br >> 8) & 255) * 587 + (br & 255) * 114
                    lmin = lmax = la; clo = chi = tl
                    if lb < lmin: lmin = lb; clo = tr
                    if lb > lmax: lmax = lb; chi = tr
                    if lc < lmin: lmin = lc; clo = bl
                    if lc > lmax: lmax = lc; chi = bl
                    if ld < lmin: lmin = ld; clo = br
                    if ld > lmax: lmax = ld; chi = br
                    mid = (lmin + lmax) * 0.5
                    m = (1 if la >= mid else 0) | (2 if lb >= mid else 0) \
                        | (4 if lc >= mid else 0) | (8 if ld >= mid else 0)
                    fg = chi; bg = clo; g = G[m]
                if cur == (fg, bg):
                    run.append(g)
                else:
                    if cur is not None:
                        out.append(self._pref(cur[0], cur[1])); out.append("".join(run))
                    cur = (fg, bg); run = [g]
            if cur is not None:
                out.append(self._pref(cur[0], cur[1])); out.append("".join(run))
            out.append(ESC + "[0m")
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
