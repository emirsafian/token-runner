"""Ambient life: one kind per biome (CRITTERS), plus fireflies at night."""
import math
import random
from .render import pack, shade, lerpc


CRITTERS = {
    "JUNGLE": "butterfly", "AMAZON": "butterfly", "DESERT": "tumbleweed", "BEACH": "crab",
    "OCEAN": "fish", "SNOW": "bird", "VOLCANO": "ember", "CITY": "drone", "NEON": "drone", "COSMOS": "ufo",
}


def _spawn_critter(scene, biome, W, H, HY, GY, night):
    kind = CRITTERS.get(biome, "butterfly")
    if night and kind not in ("fish", "ember", "ufo") and random.random() < 0.45:
        kind = "firefly"
    c = {"kind": kind, "ph": random.uniform(0, 6.28), "vy": 0.0}
    if kind in ("crab", "tumbleweed"):
        c.update(x=W + 6, y=GY, vx=-random.uniform(26, 46))
    elif kind == "fish":
        c.update(x=W + 6, y=random.uniform(HY + 4, GY - 2), vx=-random.uniform(30, 56))
    elif kind == "ember":
        c.update(x=random.uniform(0, W), y=GY, vx=-random.uniform(3, 11), vy=-random.uniform(10, 22))
    elif kind == "firefly":
        c.update(x=random.uniform(0, W), y=random.uniform(HY, GY - 2), vx=-random.uniform(2, 8))
    elif kind in ("drone", "ufo"):
        c.update(x=W + 6, y=random.uniform(HY * 0.35, HY), vx=-random.uniform(18, 34))
    else:  # butterfly / bird
        c.update(x=W + 6, y=random.uniform(HY, GY - 4), vx=-random.uniform(14, 26))
    scene.critters.append(c)


def _draw_critter(cv, c, b, t):
    k, x, y = c["kind"], c["x"], c["y"]
    if k == "butterfly":
        wing = pack(*b["accent"]); flap = math.sin(t * 12 + c["ph"]) * 1.6
        cv.disc(x - 1, y - flap, 1.3, wing); cv.disc(x + 1, y + flap, 1.3, wing); cv.px(x, y, pack(30, 30, 40))
    elif k == "tumbleweed":
        cv.disc(x, y - 2, 2.2, pack(*shade(b["gNear"], 1.25)))
    elif k == "crab":
        cc = pack(228, 92, 70); lg = math.sin(t * 16) * 0.8
        cv.ellipse(x, y - 1, 2.2, 1.3, cc)
        cv.px(x - 3, y - 3, cc); cv.px(x + 3, y - 3, cc); cv.px(x - 2, y + lg, cc); cv.px(x + 2, y - lg, cc)
    elif k == "fish":
        cc = pack(*lerpc(b["accent"], (255, 255, 255), 0.1))
        cv.ellipse(x, y, 2.1, 1.2, cc); cv.thick(x - 2, y, x - 3.6, y - 1.2, 1, cc); cv.thick(x - 2, y, x - 3.6, y + 1.2, 1, cc)
    elif k == "ember":
        a = 0.5 + 0.5 * math.sin(t * 10 + c["ph"]); cv.px(x, y, pack(255, int(120 + 100 * a), 40))
    elif k == "firefly":
        a = 0.35 + 0.65 * abs(math.sin(t * 4 + c["ph"]))
        cv.disc(x, y + math.sin(t * 1.5 + c["ph"]) * 2, 1.5, pack(int(210 * a), int(255 * a), int(120 * a)))
    elif k == "drone":
        cv.rect(x - 1, y, x + 1, y + 1, pack(70, 80, 100)); cv.px(x, y - 1, pack(255, 70, 70) if int(t * 4) % 2 else pack(70, 255, 90))
    elif k == "ufo":
        cv.ellipse(x, y, 3, 1, pack(*b["accent"])); cv.disc(x, y - 1, 1.4, pack(200, 255, 230))
    else:  # bird-like
        flap = math.sin(t * 9 + c["ph"]) * 1.6
        cc = pack(*shade(b["far"], 0.85)); cv.thick(x - 2, y + flap, x, y, 1, cc); cv.thick(x, y, x + 2, y + flap, 1, cc)
