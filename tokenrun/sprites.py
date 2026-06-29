"""Roadside props. Each draw_* takes (canvas, x, ground_y, size, biome) and is
registered in SPR. To add one: write a draw_x, register it in SPR, then list
its name in some biome's `kinds` in tokenrun.biomes.
"""
import math
from .render import pack, shade, lerpc


def draw_tree(cv, x, gy, s, b):
    cv.thick(x, gy, x, gy - s * 1.4, max(1, int(s * 0.22)), pack(70, 50, 36))
    leaf = b["accent"]
    cv.disc(x, gy - s * 1.7, s * 0.95, pack(*shade(leaf, 0.7)))
    cv.disc(x - s * 0.7, gy - s * 1.3, s * 0.7, pack(*shade(leaf, 0.55)))
    cv.disc(x + s * 0.7, gy - s * 1.3, s * 0.7, pack(*shade(leaf, 0.62)))
    cv.disc(x - s * 0.25, gy - s * 2.0, s * 0.55, pack(*lerpc(leaf, (255, 255, 255), 0.2)))


def draw_cactus(cv, x, gy, s, b):
    c = pack(*b["accent"]); cd = pack(*shade(b["accent"], 0.65))
    w = max(1, int(s * 0.32))
    cv.rect(x - w, gy - s * 1.8, x + w, gy, c)
    cv.rect(x - w, gy - s * 1.8, x - max(1, w // 2), gy, cd)
    cv.rect(x - s * 0.95, gy - s * 1.05, x - w, gy - s * 0.85, c)
    cv.rect(x - s * 0.95, gy - s * 1.45, x - s * 0.7, gy - s * 1.05, c)
    cv.rect(x + w, gy - s * 0.85, x + s * 0.95, gy - s * 0.65, c)
    cv.rect(x + s * 0.7, gy - s * 1.25, x + s * 0.95, gy - s * 0.65, c)


def draw_building(cv, x, gy, s, b):
    bw = s * 0.85; body = shade(b["accent"], 0.45)
    cv.rect(x - bw, gy - s * 2.4, x + bw, gy, pack(*body))
    cv.rect(x - bw, gy - s * 2.4, x - bw + max(1, int(s * 0.22)), gy, pack(*shade(body, 1.5)))
    win = pack(255, 214, 138)
    yy = gy - s * 2.2
    while yy < gy - s * 0.2:
        xx = x - bw + s * 0.3
        while xx < x + bw - s * 0.2:
            if (int(xx) * 7 + int(yy) * 13) % 3:
                cv.rect(xx, yy, xx + s * 0.16, yy + s * 0.2, win)
            xx += s * 0.4
        yy += s * 0.42


def draw_rock(cv, x, gy, s, b):
    c = shade(b["gNear"], 1.15)
    cv.ellipse(x, gy - s * 0.34, s * 0.85, s * 0.48, pack(*c))
    cv.ellipse(x - s * 0.22, gy - s * 0.52, s * 0.38, s * 0.3, pack(*shade(c, 1.25)))


def draw_crystal(cv, x, gy, s, b):
    c = b["accent"]
    cv.thick(x, gy, x, gy - s * 1.6, max(1, int(s * 0.3)), pack(*shade(c, 0.6)))
    cv.thick(x, gy - s * 0.8, x, gy - s * 1.7, max(1, int(s * 0.16)), pack(*lerpc(c, (255, 255, 255), 0.4)))
    cv.disc(x, gy - s * 1.7, s * 0.22, pack(255, 255, 255))


def draw_palm(cv, x, gy, s, b):
    trunk = pack(120, 84, 50)
    for i in range(int(s * 1.9)):                      # curved trunk
        f = i / max(1, s * 1.9)
        cv.disc(x + math.sin(f * 1.2) * s * 0.3, gy - i, max(1, s * 0.13), trunk)
    tx, ty = x + math.sin(1.2) * s * 0.3, gy - s * 1.9
    frond = (54, 168, 92)                              # palm green (not the water accent)
    for a in (-2.5, -1.8, -1.1, -0.3, 0.4):            # drooping fronds
        ex, ey = tx + math.cos(a) * s * 1.1, ty + math.sin(a) * s * 0.9 + s * 0.2
        cv.thick(tx, ty, ex, ey, max(1, int(s * 0.12)), pack(*shade(frond, 0.8 if a < -1 else 0.95)))
    cv.disc(tx, ty, s * 0.18, pack(*shade(frond, 0.7)))
    for k in range(3):
        cv.disc(tx + (k - 1) * s * 0.18, ty + s * 0.18, s * 0.1, pack(120, 90, 60))  # coconuts


def draw_pine(cv, x, gy, s, b):
    cv.thick(x, gy, x, gy - s * 0.6, max(1, int(s * 0.16)), pack(80, 58, 42))
    green = shade(b["accent"], 0.62)
    snow = (236, 240, 248)
    for k, yy in enumerate((1.9, 1.45, 1.0)):          # stacked snowy tiers
        w = s * (0.45 + k * 0.28)
        cy = gy - s * yy
        cv.thick(x - w, cy + s * 0.32, x + w, cy + s * 0.32, 1, pack(*green))
        for dy in range(int(s * 0.34)):
            ww = w * (1 - dy / max(1, s * 0.34))
            cv.thick(x - ww, cy + dy, x + ww, cy + dy, 1, pack(*green))
        cv.thick(x - w * 0.5, cy, x + w * 0.5, cy, 1, pack(*snow))


def draw_snowman(cv, x, gy, s, b):
    white = pack(238, 242, 250); shadow = pack(196, 206, 222)
    cv.disc(x, gy - s * 0.5, s * 0.55, white)
    cv.disc(x + s * 0.18, gy - s * 0.5, s * 0.42, shadow)
    cv.disc(x, gy - s * 1.15, s * 0.4, white)
    cv.disc(x, gy - s * 1.55, s * 0.3, white)
    cv.disc(x - s * 0.08, gy - s * 1.6, s * 0.06, pack(30, 30, 40))   # eyes
    cv.disc(x + s * 0.12, gy - s * 1.6, s * 0.06, pack(30, 30, 40))
    cv.thick(x + s * 0.1, gy - s * 1.5, x + s * 0.5, gy - s * 1.45, 1, pack(240, 140, 40))  # carrot


def draw_bigtree(cv, x, gy, s, b):
    cv.thick(x, gy, x, gy - s * 2.2, max(2, int(s * 0.3)), pack(78, 56, 40))
    leaf = b["accent"]
    cv.disc(x, gy - s * 2.6, s * 1.3, pack(*shade(leaf, 0.6)))
    cv.disc(x - s * 1.0, gy - s * 2.1, s * 0.9, pack(*shade(leaf, 0.48)))
    cv.disc(x + s * 1.0, gy - s * 2.1, s * 0.9, pack(*shade(leaf, 0.54)))
    cv.disc(x - s * 0.3, gy - s * 3.0, s * 0.7, pack(*lerpc(leaf, (255, 255, 255), 0.2)))


def draw_vine(cv, x, gy, s, b):
    leaf = shade(b["accent"], 0.7)
    cv.thick(x, gy - s * 2.4, x, gy - s * 0.4, max(1, int(s * 0.1)), pack(*shade(leaf, 0.7)))
    for i in range(5):
        yy = gy - s * 0.5 - i * s * 0.42
        cv.disc(x + (s * 0.22 if i % 2 else -s * 0.22), yy, s * 0.2, pack(*leaf))


def draw_volcano(cv, x, gy, s, b):
    rock = shade(b["gNear"], 1.1)
    for dy in range(int(s * 1.7)):                     # cone
        f = dy / max(1, s * 1.7)
        w = s * (1.2 * (1 - f) + 0.28)
        cv.thick(x - w, gy - dy, x + w, gy - dy, 1, pack(*shade(rock, 0.8 + 0.3 * f)))
    cv.ellipse(x, gy - s * 1.7, s * 0.32, s * 0.12, pack(60, 30, 30))   # crater
    cv.disc(x, gy - s * 1.7, s * 0.2, pack(255, 140, 40))               # glow
    for k in range(4):                                                  # spitting lava
        cv.disc(x + (k - 1.5) * s * 0.22, gy - s * 1.95 - (k % 2) * s * 0.25, s * 0.07, pack(255, 90 + k * 30, 30))


def draw_lavarock(cv, x, gy, s, b):
    cv.ellipse(x, gy - s * 0.34, s * 0.85, s * 0.46, pack(54, 38, 38))
    for k in range(3):
        cv.thick(x - s * 0.5 + k * s * 0.5, gy - s * 0.2, x - s * 0.3 + k * s * 0.5, gy - s * 0.55,
                 1, pack(255, 110, 40))                                  # lava cracks


def draw_coral(cv, x, gy, s, b):
    c = b["accent"]
    cv.thick(x, gy, x, gy - s * 0.8, max(1, int(s * 0.22)), pack(*c))
    for a in (-0.7, 0.0, 0.7):
        tipx, tipy = x + math.sin(a) * s * 0.8, gy - s * 1.4
        cv.thick(x, gy - s * 0.7, tipx, tipy, max(1, int(s * 0.16)), pack(*shade(c, 1.0)))
        cv.disc(tipx, tipy, s * 0.16, pack(*lerpc(c, (255, 255, 255), 0.3)))


def draw_seaweed(cv, x, gy, s, b):
    green = (60, 170, 120)
    for k in range(3):
        bx = x + (k - 1) * s * 0.3
        for i in range(int(s * 1.6)):
            cv.disc(bx + math.sin(i * 0.4 + k) * s * 0.25, gy - i, max(1, s * 0.1), pack(*shade(green, 0.7 + k * 0.12)))


def draw_neon(cv, x, gy, s, b):
    body = shade(b["gNear"], 1.0)
    cv.rect(x - s * 0.6, gy - s * 2.0, x + s * 0.6, gy, pack(*body))
    sign = b["accent"]
    cv.rect(x - s * 0.4, gy - s * 1.9, x + s * 0.4, gy - s * 1.4, pack(*lerpc(sign, (255, 255, 255), 0.3)))
    cv.rect(x - s * 0.5, gy - s * 1.1, x - s * 0.1, gy - s * 0.6, pack(120, 220, 255))
    cv.rect(x + s * 0.1, gy - s * 1.1, x + s * 0.5, gy - s * 0.6, pack(255, 220, 120))


SPR = {"tree": draw_tree, "cactus": draw_cactus, "building": draw_building, "rock": draw_rock,
       "crystal": draw_crystal, "palm": draw_palm, "pine": draw_pine, "snowman": draw_snowman,
       "bigtree": draw_bigtree, "vine": draw_vine, "volcano": draw_volcano, "lavarock": draw_lavarock,
       "coral": draw_coral, "seaweed": draw_seaweed, "neon": draw_neon}
