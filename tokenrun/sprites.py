"""Roadside props. Each draw_* takes (canvas, x, ground_y, size, biome) and is
registered in SPR. To add one: write a draw_x, register it in SPR, then list
its name in some biome's `kinds` in tokenrun.biomes.
"""
import math
from .render import pack, shade, lerpc


def draw_tree(cv, x, gy, s, b):
    """A leafy tree with volume: a two-tone trunk + root flare, a canopy lit from
    the upper-right (toward the sun) down to a shadowed underside, and a ring of
    foliage clumps for an organic edge. Texture is gated on size so far trees stay
    clean."""
    leaf = b["accent"]
    c_dark = shade(leaf, 0.45)                     # shadowed lower-left / underside
    c_mid = shade(leaf, 0.62)
    c_lit = shade(leaf, 0.80)
    c_hi = lerpc(leaf, (255, 255, 255), 0.32)      # sun-lit upper-right
    bark = pack(78, 56, 40); barkd = pack(52, 36, 26); barkl = pack(104, 76, 54)

    tw = max(1, int(s * 0.24))                                   # tapered, two-tone trunk
    cv.thick(x, gy, x, gy - s * 1.4, tw, bark)
    cv.thick(x + max(0.5, s * 0.07), gy, x + max(0.5, s * 0.07), gy - s * 1.28, max(1, int(s * 0.07)), barkl)
    cv.thick(x - max(0.5, s * 0.07), gy, x - max(0.5, s * 0.07), gy - s * 1.28, max(1, int(s * 0.07)), barkd)
    if s > 5:
        cv.disc(x, gy, max(1, s * 0.2), bark)                                       # root flare
        cv.thick(x, gy - s * 0.8, x + s * 0.3, gy - s * 1.12, max(1, int(s * 0.08)), bark)  # a branch

    cy = gy - s * 1.75                                           # canopy centre
    cv.disc(x, cy + s * 0.3, s * 0.76, pack(*c_dark))            # shadowed underside (AO at the trunk)
    cv.disc(x - s * 0.5, cy + s * 0.04, s * 0.58, pack(*c_mid))
    cv.disc(x + s * 0.5, cy - s * 0.02, s * 0.6, pack(*c_mid))
    cv.disc(x - s * 0.06, cy - s * 0.2, s * 0.76, pack(*c_lit))    # main lit body
    cv.disc(x + s * 0.34, cy - s * 0.34, s * 0.48, pack(*c_hi))    # sun-lit shoulder
    if s > 3:                                                    # organic foliage clumps round the rim
        for ang, rr, col in ((2.6, 0.74, c_mid), (1.9, 0.82, c_lit), (1.15, 0.86, c_hi),
                             (0.45, 0.82, c_lit), (-0.25, 0.72, c_mid)):
            cv.disc(x + math.cos(ang) * s * rr, cy - math.sin(ang) * s * rr * 0.8, s * 0.2, pack(*col))


def draw_cactus(cv, x, gy, s, b):
    c = b["accent"]; cM = pack(*c); cd = pack(*shade(c, 0.62)); cl = pack(*lerpc(c, (255, 255, 255), 0.25))
    w = max(1, int(s * 0.32))
    cv.rect(x - w, gy - s * 1.8, x + w, gy, cM)                            # trunk
    cv.disc(x, gy - s * 1.8, w, cM)                                        # rounded crown
    cv.rect(x - w, gy - s * 1.8, x - max(1, w // 2), gy, cd)               # shaded left
    cv.rect(x + max(1, int(w * 0.5)), gy - s * 1.8, x + w, gy, cl)         # lit right edge
    cv.rect(x - s * 0.95, gy - s * 1.05, x - w, gy - s * 0.85, cM)         # left arm
    cv.rect(x - s * 0.95, gy - s * 1.45, x - s * 0.7, gy - s * 1.05, cM)
    cv.disc(x - s * 0.82, gy - s * 1.45, max(1, s * 0.13), cM)             # rounded arm tip
    cv.rect(x + w, gy - s * 0.85, x + s * 0.95, gy - s * 0.65, cM)         # right arm
    cv.rect(x + s * 0.7, gy - s * 1.25, x + s * 0.95, gy - s * 0.65, cM)
    cv.disc(x + s * 0.82, gy - s * 1.25, max(1, s * 0.13), cM)             # rounded arm tip
    if s > 3:
        cv.thick(x - w * 0.25, gy - s * 1.65, x - w * 0.25, gy - s * 0.15, 1, cd)  # rib (shade)
        cv.thick(x + w * 0.45, gy - s * 1.65, x + w * 0.45, gy - s * 0.15, 1, cl)  # rib (lit)
        cv.disc(x, gy - s * 1.86, max(1, s * 0.09), pack(228, 96, 132))    # a bloom on top


def draw_building(cv, x, gy, s, b):
    bw = s * 0.85; body = shade(b["accent"], 0.45)
    cv.rect(x - bw, gy - s * 2.4, x + bw, gy, pack(*body))
    cv.rect(x - bw, gy - s * 2.4, x - bw + max(1, int(s * 0.18)), gy, pack(*shade(body, 1.5)))   # lit left edge
    cv.rect(x + bw - max(1, int(s * 0.14)), gy - s * 2.4, x + bw, gy, pack(*shade(body, 0.7)))   # shaded right edge
    cv.rect(x - bw, gy - s * 2.52, x + bw, gy - s * 2.4, pack(*shade(body, 1.2)))                # parapet
    cv.rect(x + bw * 0.28, gy - s * 2.76, x + bw * 0.66, gy - s * 2.52, pack(*shade(body, 0.92)))  # rooftop tank
    cv.thick(x - bw * 0.5, gy - s * 2.52, x - bw * 0.5, gy - s * 2.95, 1, pack(*shade(body, 1.5)))  # antenna
    win = pack(255, 214, 138); wind = pack(*shade(body, 0.72)); winc = pack(150, 200, 255)
    yy = gy - s * 2.2
    while yy < gy - s * 0.5:
        xx = x - bw + s * 0.3
        while xx < x + bw - s * 0.2:
            h = (int(xx) * 7 + int(yy) * 13) % 5
            cv.rect(xx, yy, xx + s * 0.16, yy + s * 0.2, wind if h == 0 else (winc if h == 1 else win))
            xx += s * 0.4
        yy += s * 0.42
    cv.rect(x - s * 0.18, gy - s * 0.5, x + s * 0.18, gy, pack(*shade(body, 0.6)))   # entrance


def draw_rock(cv, x, gy, s, b):
    base = shade(b["gNear"], 1.15)
    dk = shade(base, 0.78); lt = shade(base, 1.22); hi = lerpc(base, (255, 255, 255), 0.3)
    cv.ellipse(x, gy - s * 0.32, s * 0.86, s * 0.5, pack(*dk))            # mass, shadow side
    cv.ellipse(x - s * 0.06, gy - s * 0.4, s * 0.64, s * 0.42, pack(*base))   # body
    cv.ellipse(x + s * 0.22, gy - s * 0.52, s * 0.34, s * 0.26, pack(*lt))    # lit upper-right facet
    cv.ellipse(x + s * 0.34, gy - s * 0.58, s * 0.18, s * 0.13, pack(*hi))    # sun glint
    if s > 3:
        cv.thick(x + s * 0.05, gy - s * 0.18, x - s * 0.12, gy - s * 0.46, 1, pack(*dk))  # a crack
        cv.ellipse(x - s * 0.72, gy - s * 0.1, s * 0.2, s * 0.12, pack(*base))            # a pebble at the base


def draw_crystal(cv, x, gy, s, b):
    c = b["accent"]; cd = shade(c, 0.55); cl = lerpc(c, (255, 255, 255), 0.45); core = lerpc(c, (255, 255, 255), 0.75)
    cv.disc(x, gy - s * 0.9, s * 0.7, pack(*shade(c, 0.32)))                # ambient glow halo
    for dx, h, w in ((0.0, 1.7, 0.3), (-0.5, 1.15, 0.2), (0.5, 1.0, 0.18)):  # a cluster of shards
        bx = x + s * dx
        cv.thick(bx, gy, bx, gy - s * h, max(1, int(s * w)), pack(*cd))                        # shard (shadow facet)
        cv.thick(bx + s * w * 0.4, gy, bx + s * w * 0.4, gy - s * h, max(1, int(s * w * 0.5)), pack(*cl))  # lit facet
        cv.disc(bx, gy - s * h, max(1, s * w * 0.7), pack(*core))                               # glowing tip
    cv.disc(x, gy - s * 1.7, max(1, s * 0.12), pack(255, 255, 255))


def draw_palm(cv, x, gy, s, b):
    trunk = (120, 84, 50); trunkL = (152, 112, 72); trunkD = (92, 62, 38)
    ring = max(2, int(s * 0.3))
    for i in range(int(s * 1.9)):                      # curved, ringed trunk
        f = i / max(1, s * 1.9)
        cxx = x + math.sin(f * 1.2) * s * 0.3
        cv.disc(cxx, gy - i, max(1, s * 0.13), pack(*trunk))
        cv.disc(cxx + s * 0.05, gy - i, max(1, s * 0.05), pack(*trunkL))     # lit right edge
        if i % ring == 0:
            cv.disc(cxx - s * 0.04, gy - i, max(1, s * 0.06), pack(*trunkD))  # segment ring
    tx, ty = x + math.sin(1.2) * s * 0.3, gy - s * 1.9
    frond = (54, 168, 92); frondL = (98, 202, 122); frondD = (38, 130, 74)   # palm green (not the water accent)
    for a in (-2.6, -2.0, -1.3, -0.5, 0.2, 0.7):       # drooping fronds, lit toward the right
        col = frondD if a < -1.3 else (frondL if a > -0.2 else frond)
        mx, my = tx + math.cos(a) * s * 0.6, ty + math.sin(a) * s * 0.5 + s * 0.1
        ex, ey = tx + math.cos(a) * s * 1.15, ty + math.sin(a) * s * 0.95 + s * 0.28
        cv.thick(tx, ty, mx, my, max(1, int(s * 0.12)), pack(*col))
        cv.thick(mx, my, ex, ey, max(1, int(s * 0.07)), pack(*col))          # thinner drooping tip
        cv.disc(ex, ey, max(1, s * 0.06), pack(*frondL))                     # leaf tip
    cv.disc(tx, ty, s * 0.2, pack(*frondD))                                  # crown knot
    for k in range(3):
        cv.disc(tx + (k - 1) * s * 0.16, ty + s * 0.2, max(1, s * 0.1), pack(110, 78, 50))  # coconuts


def draw_pine(cv, x, gy, s, b):
    cv.thick(x, gy, x, gy - s * 0.6, max(1, int(s * 0.16)), pack(74, 52, 38))
    cv.thick(x + max(0.5, s * 0.05), gy, x + max(0.5, s * 0.05), gy - s * 0.55, 1, pack(96, 70, 50))  # lit trunk edge
    green = shade(b["accent"], 0.62); greenL = shade(b["accent"], 0.8); greenD = shade(b["accent"], 0.48)
    snow = (236, 240, 248); snowS = (198, 212, 234)
    for k, yy in enumerate((1.9, 1.45, 1.0)):          # stacked snowy tiers, lit from the right
        w = s * (0.45 + k * 0.28)
        cy = gy - s * yy
        for dy in range(int(s * 0.34)):
            ww = w * (1 - dy / max(1, s * 0.34))
            cv.thick(x - ww, cy + dy, x + ww, cy + dy, 1, pack(*green))
            cv.thick(x + ww * 0.12, cy + dy, x + ww, cy + dy, 1, pack(*greenL))   # lit right side
        cv.thick(x - w, cy + s * 0.32, x + w, cy + s * 0.33, 1, pack(*greenD))    # shaded skirt
        cv.thick(x - w * 0.55, cy, x + w * 0.5, cy, max(1, int(s * 0.07)), pack(*snow))   # snow cap
        cv.thick(x - w * 0.5, cy + max(1, int(s * 0.07)), x + w * 0.45, cy + max(1, int(s * 0.07)), 1, pack(*snowS))
    cv.disc(x, gy - s * 2.02, max(1, s * 0.09), pack(*snow))   # snowy tip


def draw_snowman(cv, x, gy, s, b):
    white = (240, 244, 252); shad = (192, 204, 222); hi = (255, 255, 255); coal = pack(34, 34, 44)
    for cyf, r in ((0.5, 0.55), (1.15, 0.42), (1.6, 0.3)):     # three stacked balls, lit from the right
        cy = gy - s * cyf
        cv.disc(x, cy, s * r, pack(*white))
        cv.disc(x - s * r * 0.42, cy + s * r * 0.22, s * r * 0.66, pack(*shad))   # shadow lower-left
        cv.disc(x + s * r * 0.4, cy - s * r * 0.4, s * r * 0.38, pack(*hi))       # highlight upper-right
    cv.thick(x - s * 0.42, gy - s * 1.15, x - s * 0.85, gy - s * 1.36, max(1, int(s * 0.05)), pack(96, 66, 42))  # stick arms
    cv.thick(x + s * 0.4, gy - s * 1.18, x + s * 0.82, gy - s * 0.98, max(1, int(s * 0.05)), pack(96, 66, 42))
    cv.disc(x - s * 0.1, gy - s * 1.68, max(1, s * 0.05), coal)             # eyes
    cv.disc(x + s * 0.12, gy - s * 1.68, max(1, s * 0.05), coal)
    cv.thick(x + s * 0.12, gy - s * 1.58, x + s * 0.52, gy - s * 1.53, max(1, int(s * 0.07)), pack(240, 140, 40))  # carrot
    for i in range(3):                                                      # coal buttons
        cv.disc(x, gy - s * (1.04 + i * 0.16), max(1, s * 0.04), coal)
    if s > 4:
        cv.rect(x - s * 0.3, gy - s * 1.42, x + s * 0.32, gy - s * 1.34, pack(210, 72, 72))   # scarf
        cv.rect(x + s * 0.18, gy - s * 1.34, x + s * 0.28, gy - s * 1.12, pack(210, 72, 72))  # scarf tail


def draw_bigtree(cv, x, gy, s, b):
    """A jungle giant: buttressed two-tone trunk, a tall layered canopy lit from the
    upper-right with a ring of foliage clumps. (The big sibling of draw_tree.)"""
    leaf = b["accent"]
    c_dark = shade(leaf, 0.42); c_mid = shade(leaf, 0.58); c_lit = shade(leaf, 0.76)
    c_hi = lerpc(leaf, (255, 255, 255), 0.28)
    bark = pack(80, 58, 42); barkd = pack(54, 38, 28); barkl = pack(106, 78, 56)
    tw = max(2, int(s * 0.3))
    cv.thick(x, gy, x, gy - s * 2.3, tw, bark)
    cv.thick(x + max(0.5, s * 0.1), gy, x + max(0.5, s * 0.1), gy - s * 2.1, max(1, int(s * 0.09)), barkl)
    cv.thick(x - max(0.5, s * 0.1), gy, x - max(0.5, s * 0.1), gy - s * 2.1, max(1, int(s * 0.09)), barkd)
    if s > 4:
        cv.thick(x, gy - s * 0.32, x - s * 0.5, gy, max(1, int(s * 0.14)), bark)   # buttress roots
        cv.thick(x, gy - s * 0.32, x + s * 0.5, gy, max(1, int(s * 0.14)), bark)
        cv.thick(x, gy - s * 1.45, x + s * 0.55, gy - s * 1.95, max(1, int(s * 0.12)), bark)  # a high branch
    cy = gy - s * 2.55                                          # canopy centre
    cv.disc(x, cy + s * 0.5, s * 1.15, pack(*c_dark))           # shadowed underside
    cv.disc(x - s * 0.95, cy + s * 0.1, s * 0.82, pack(*c_mid))
    cv.disc(x + s * 0.95, cy + s * 0.05, s * 0.85, pack(*c_mid))
    cv.disc(x - s * 0.1, cy - s * 0.35, s * 1.05, pack(*c_lit))   # main lit crown
    cv.disc(x + s * 0.5, cy - s * 0.55, s * 0.66, pack(*c_hi))    # sun-lit shoulder
    if s > 3:
        for ang, rr, col in ((2.6, 0.95, c_mid), (2.0, 1.02, c_lit), (1.2, 1.06, c_hi),
                             (0.4, 1.0, c_lit), (-0.3, 0.9, c_mid)):
            cv.disc(x + math.cos(ang) * s * rr, cy - math.sin(ang) * s * rr * 0.78, s * 0.26, pack(*col))


def draw_vine(cv, x, gy, s, b):
    leaf = shade(b["accent"], 0.72); leafL = shade(b["accent"], 0.92); stem = shade(b["accent"], 0.5)
    prevx, prevy = x, gy - s * 2.4
    for i in range(1, 13):                                     # a gently curving stem
        f = i / 12.0
        nx = x + math.sin(f * 6.0) * s * 0.18
        ny = gy - s * 2.4 + f * s * 2.0
        cv.thick(prevx, prevy, nx, ny, max(1, int(s * 0.08)), pack(*stem))
        prevx, prevy = nx, ny
    for i in range(5):                                         # leaf pairs along the stem
        f = (i + 0.5) / 5.0
        lx = x + math.sin(f * 6.0) * s * 0.18
        ly = gy - s * 2.4 + f * s * 2.0
        cv.ellipse(lx - s * 0.26, ly, s * 0.22, s * 0.12, pack(*leaf))       # left leaf (shadow)
        cv.ellipse(lx + s * 0.26, ly, s * 0.22, s * 0.12, pack(*leafL))      # right leaf (lit)
    cv.disc(x + math.sin(6.0) * s * 0.18, gy - s * 0.4, max(1, s * 0.12), pack(228, 120, 150))  # a bloom at the tip


def draw_volcano(cv, x, gy, s, b):
    rock = shade(b["gNear"], 1.1)
    HH = int(s * 1.7)
    for dy in range(HH):                               # cone, lit on the right slope
        f = dy / max(1, HH)
        w = s * (1.2 * (1 - f) + 0.28)
        cv.thick(x - w, gy - dy, x + w, gy - dy, 1, pack(*shade(rock, 0.78 + 0.3 * f)))
        cv.thick(x + w * 0.15, gy - dy, x + w, gy - dy, 1, pack(*shade(rock, 0.96 + 0.34 * f)))
    for sgn in (-1, 1):                                # lava streaks trickling down both slopes
        for dy in range(int(s * 1.3)):
            f = dy / max(1, s * 1.3)
            sx = x + sgn * s * (0.1 + 0.95 * f)
            cv.px(sx, gy - s * 1.55 + dy, pack(255, int(130 - 50 * f), 40))
            if dy % 3 == 0:
                cv.px(sx + sgn, gy - s * 1.55 + dy, pack(255, int(90 - 30 * f), 30))
    cv.ellipse(x, gy - s * 1.7, s * 0.34, s * 0.13, pack(60, 28, 28))   # crater rim
    cv.disc(x, gy - s * 1.68, s * 0.22, pack(255, 150, 50))             # crater glow
    cv.disc(x, gy - s * 1.68, max(1, s * 0.1), pack(255, 230, 120))     # hot core
    for k in range(5):                                                  # spitting lava
        cv.disc(x + (k - 2) * s * 0.2, gy - s * 1.95 - (k % 2) * s * 0.28, max(1, s * 0.06), pack(255, 90 + k * 26, 30))
    for k in range(3):                                                  # drifting smoke plume
        cv.disc(x - s * 0.1 + k * s * 0.07, gy - s * 2.05 - k * s * 0.3, s * (0.14 + k * 0.05),
                pack(*shade((92, 74, 74), 1.0 + k * 0.12)))


def draw_lavarock(cv, x, gy, s, b):
    cv.ellipse(x, gy - s * 0.32, s * 0.88, s * 0.5, pack(46, 32, 32))           # mass
    cv.ellipse(x + s * 0.2, gy - s * 0.48, s * 0.3, s * 0.2, pack(72, 52, 52))  # lit upper-right facet
    for k in range(3):                                                          # glowing cracks
        x0 = x - s * 0.5 + k * s * 0.5
        cv.thick(x0, gy - s * 0.18, x0 + s * 0.2, gy - s * 0.52, 1, pack(255, 120, 40))
        cv.px(x0 + s * 0.1, gy - s * 0.35, pack(255, 220, 130))                 # hot spot
    cv.disc(x, gy - s * 0.3, max(1, s * 0.08), pack(255, 90, 30))               # a molten vent


def draw_coral(cv, x, gy, s, b):
    c = b["accent"]; cl = lerpc(c, (255, 255, 255), 0.3); cd = shade(c, 0.7)
    cv.thick(x, gy, x, gy - s * 0.8, max(1, int(s * 0.24)), pack(*cd))           # trunk (shadow base)
    cv.thick(x + s * 0.04, gy, x + s * 0.04, gy - s * 0.8, max(1, int(s * 0.12)), pack(*c))  # lit front
    for a in (-0.9, -0.35, 0.3, 0.85):                                           # branches
        midx, midy = x + math.sin(a) * s * 0.5, gy - s * 1.0
        tipx, tipy = x + math.sin(a) * s * 0.95, gy - s * (1.3 + 0.2 * math.cos(a))
        cv.thick(x, gy - s * 0.7, midx, midy, max(1, int(s * 0.16)), pack(*c))
        cv.thick(midx, midy, tipx, tipy, max(1, int(s * 0.11)), pack(*cl))       # lit upper branch
        cv.disc(tipx, tipy, max(1, s * 0.14), pack(*cl))                         # rounded tip
        cv.disc(midx, midy, max(1, s * 0.07), pack(*cd))                         # polyp bump


def draw_seaweed(cv, x, gy, s, b):
    green = (60, 170, 120); greenL = (110, 210, 150)
    blade = max(2, int(s * 0.4))
    for k in range(3):
        bx = x + (k - 1) * s * 0.3
        n = int(s * 1.6)
        for i in range(n):
            wx = bx + math.sin(i * 0.4 + k) * s * 0.25
            cv.disc(wx, gy - i, max(1, s * 0.1), pack(*shade(green, 0.7 + k * 0.12)))
            if i > 0 and i % blade == 0:                                         # little blades off the strand
                side = -1 if (i // blade) % 2 else 1
                cv.ellipse(wx + side * s * 0.18, gy - i, s * 0.14, s * 0.07, pack(*shade(green, 0.86 + k * 0.1)))
        cv.disc(bx + math.sin((n - 1) * 0.4 + k) * s * 0.25, gy - n, max(1, s * 0.09), pack(*greenL))  # bright tip


def draw_buoy(cv, x, gy, s, b):
    """A channel buoy bobbing on the surface — red float, white band, a beacon."""
    red = pack(214, 78, 66); white = pack(238, 242, 246); dark = pack(150, 44, 38)
    cv.ellipse(x, gy - s * 0.5, s * 0.4, s * 0.55, red)              # float body
    cv.ellipse(x - s * 0.12, gy - s * 0.6, s * 0.16, s * 0.3, pack(*lerpc((214, 78, 66), (255, 255, 255), 0.4)))
    cv.rect(x - s * 0.4, gy - s * 0.62, x + s * 0.4, gy - s * 0.48, white)   # band
    cv.rect(x - s * 0.4, gy - s * 1.05, x + s * 0.4, gy - s * 1.0, dark)     # cage rail
    cv.thick(x, gy - s * 1.0, x, gy - s * 1.4, max(1, int(s * 0.1)), dark)   # mast
    cv.disc(x, gy - s * 1.45, max(1, s * 0.14), pack(255, 210, 90))          # beacon light


def draw_sailboat(cv, x, gy, s, b):
    """A little sailboat drifting on the horizon."""
    hull = pack(60, 70, 92); sail = pack(244, 246, 250); saild = pack(206, 214, 228)
    cv.thick(x, gy - s * 1.9, x, gy - s * 0.4, max(1, int(s * 0.08)), pack(120, 96, 70))   # mast
    for dy in range(int(s * 1.4)):                                   # mainsail (triangle to the right)
        ww = s * 0.7 * (1 - dy / max(1, s * 1.4))
        cv.thick(x + s * 0.04, gy - s * 1.8 + dy, x + s * 0.04 + ww, gy - s * 1.8 + dy, 1,
                 sail if dy % 3 else saild)
    cv.thick(x - s * 0.5, gy - s * 1.5, x - s * 0.04, gy - s * 0.5, max(1, int(s * 0.08)), sail)  # jib
    cv.thick(x - s * 0.62, gy - s * 0.42, x + s * 0.62, gy - s * 0.42, max(1, int(s * 0.2)), hull) # hull
    cv.thick(x - s * 0.42, gy - s * 0.24, x + s * 0.42, gy - s * 0.24, max(1, int(s * 0.12)), hull)


def draw_neon(cv, x, gy, s, b):
    body = shade(b["gNear"], 1.0)
    cv.rect(x - s * 0.6, gy - s * 2.0, x + s * 0.6, gy, pack(*body))
    cv.rect(x - s * 0.6, gy - s * 2.0, x - s * 0.52, gy, pack(*shade(b["gNear"], 1.35)))    # lit edge
    sign = b["accent"]

    def glow(x0, y0, x1, y1, col):                                              # a sign with a soft halo
        cv.rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1, pack(*shade(col, 0.5)))
        cv.rect(x0, y0, x1, y1, pack(*col))

    cv.rect(x - s * 0.42, gy - s * 1.92, x + s * 0.42, gy - s * 1.4, pack(*lerpc(sign, (255, 255, 255), 0.3)))  # marquee
    cv.rect(x - s * 0.46, gy - s * 1.97, x + s * 0.46, gy - s * 1.92, pack(*lerpc(sign, (255, 255, 255), 0.6)))  # marquee glow
    glow(x - s * 0.5, gy - s * 1.1, x - s * 0.1, gy - s * 0.6, (120, 220, 255))
    glow(x + s * 0.1, gy - s * 1.1, x + s * 0.5, gy - s * 0.6, (255, 220, 120))
    for i in range(4):                                                          # a vertical neon strip
        cv.rect(x + s * 0.5, gy - s * 1.86 + i * s * 0.42, x + s * 0.58, gy - s * 1.66 + i * s * 0.42, pack(255, 90, 170))


def draw_asteroid(cv, x, gy, s, b):
    """A drifting space rock, lit on its star-facing shoulder, a couple of craters."""
    rock = (96, 92, 104); lit = lerpc(rock, (212, 216, 230), 0.5)
    cv.ellipse(x, gy - s * 0.42, s * 0.8, s * 0.58, pack(*shade(rock, 0.7)))
    cv.ellipse(x + s * 0.16, gy - s * 0.52, s * 0.5, s * 0.36, pack(*rock))
    cv.ellipse(x + s * 0.3, gy - s * 0.64, s * 0.26, s * 0.18, pack(*lit))            # lit shoulder
    cv.disc(x - s * 0.22, gy - s * 0.32, max(1, s * 0.12), pack(*shade(rock, 0.5)))   # craters
    cv.disc(x + s * 0.1, gy - s * 0.28, max(1, s * 0.08), pack(*shade(rock, 0.5)))


def draw_satellite(cv, x, gy, s, b):
    """A little satellite drifting by: a gold body, two solar-panel wings, a dish."""
    body = pack(208, 178, 90); bodyd = pack(150, 120, 56)
    cy = gy - s * 0.6
    cv.rect(x - s * 0.22, cy - s * 0.28, x + s * 0.22, cy + s * 0.28, body)
    cv.rect(x - s * 0.22, cy - s * 0.28, x - s * 0.08, cy + s * 0.28, bodyd)          # shaded edge
    panel = pack(70, 110, 190); grid = pack(120, 160, 230)
    for sgn in (-1, 1):                                                               # two wings
        wx0 = x + sgn * s * 0.3; wx1 = x + sgn * s * 0.95
        cv.thick(x + sgn * s * 0.22, cy, wx0, cy, max(1, int(s * 0.06)), pack(150, 150, 160))  # boom
        cv.rect(min(wx0, wx1), cy - s * 0.2, max(wx0, wx1), cy + s * 0.2, panel)
        cv.thick(wx0, cy, wx1, cy, 1, grid)                                           # panel seam
    cv.disc(x, cy - s * 0.44, max(1, s * 0.16), pack(225, 228, 236))                  # dish
    cv.thick(x, cy - s * 0.28, x, cy - s * 0.44, max(1, int(s * 0.05)), pack(150, 150, 160))


SPR = {"tree": draw_tree, "cactus": draw_cactus, "building": draw_building, "rock": draw_rock,
       "crystal": draw_crystal, "palm": draw_palm, "pine": draw_pine, "snowman": draw_snowman,
       "bigtree": draw_bigtree, "vine": draw_vine, "volcano": draw_volcano, "lavarock": draw_lavarock,
       "coral": draw_coral, "seaweed": draw_seaweed, "neon": draw_neon,
       "buoy": draw_buoy, "sailboat": draw_sailboat,
       "asteroid": draw_asteroid, "satellite": draw_satellite}
