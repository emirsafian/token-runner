"""Ambient life: one kind per biome (CRITTERS), plus fireflies at night."""
import math
import random
from .render import pack, shade, lerpc


CRITTERS = {
    "JUNGLE": "butterfly", "AMAZON": "butterfly", "DESERT": "tumbleweed", "BEACH": "crab",
    "SURF": "dolphin", "OCEAN": "fish", "SNOW": "bird", "VOLCANO": "ember", "CITY": "drone",
    "NEON": "drone", "COSMOS": "ufo", "SPACE": "comet",
}


def _spawn_critter(scene, biome, W, H, HY, GY, night):
    kind = CRITTERS.get(biome, "butterfly")
    if night and kind not in ("fish", "ember", "ufo", "comet") and random.random() < 0.45:
        kind = "firefly"
    c = {"kind": kind, "ph": random.uniform(0, 6.28), "vy": 0.0}
    if kind in ("crab", "tumbleweed"):
        c.update(x=W + 6, y=GY, vx=-random.uniform(26, 46))
    elif kind == "dolphin":
        base = random.uniform(HY + (GY - HY) * 0.35, HY + (GY - HY) * 0.72)   # waterline it leaps from
        c.update(x=W + 8, y=base, vx=-random.uniform(36, 56), base=base, x0=W + 8,
                 arc_len=random.uniform(W * 0.5, W * 0.85), amp=random.uniform((GY - HY) * 0.32, (GY - HY) * 0.5))
    elif kind == "fish":
        c.update(x=W + 6, y=random.uniform(HY + 4, GY - 2), vx=-random.uniform(30, 56))
    elif kind == "ember":
        c.update(x=random.uniform(0, W), y=GY, vx=-random.uniform(3, 11), vy=-random.uniform(10, 22))
    elif kind == "firefly":
        c.update(x=random.uniform(0, W), y=random.uniform(HY, GY - 2), vx=-random.uniform(2, 8))
    elif kind == "comet":
        c.update(x=W + 8, y=random.uniform(HY * 0.15, HY * 0.9), vx=-random.uniform(72, 112), vy=random.uniform(14, 28))
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
    elif k == "dolphin":
        frac = (c["x0"] - x) / max(1.0, c["arc_len"])
        if frac > 1.0:
            return                                       # splashed back down, now underwater
        fc = max(0.0, min(1.0, frac))
        yy = c["base"] - math.sin(fc * math.pi) * c["amp"]
        ang = math.cos(fc * math.pi) * 0.7               # nose up on the rise, down on the fall
        dx, dy = -math.cos(ang), math.sin(ang)           # body axis, snout toward travel (-x)
        gc = pack(150, 170, 196); bc = pack(216, 232, 240)
        for i in range(-3, 4):                           # sleek arched body
            cv.disc(x + dx * i * 1.15, yy + dy * i * 1.15 - abs(i) * 0.22, max(0.6, 1.8 - abs(i) * 0.16), gc)
        cv.disc(x + dx * 3.4, yy + dy * 3.4, 0.9, gc)    # snout
        cv.disc(x + dx * 1.3, yy + dy * 1.3 + 0.7, 1.0, bc)   # pale belly
        cv.thick(x - dx * 0.4, yy - dy * 0.4, x - dx * 1.4 - dy * 2.0, yy - dy * 1.4 + dx * 2.0, 1, gc)  # dorsal fin
        cv.thick(x - dx * 3.4, yy - dy * 3.4, x - dx * 4.2 - dy * 1.6, yy - dy * 4.2 + dx * 1.6, 1, gc)  # tail fluke
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
    elif k == "comet":
        tail = lerpc(b["accent"], (255, 255, 255), 0.4)
        for i in range(6):                               # tail streaming up-back (opposite to travel)
            cv.disc(x + i * 1.8, y - i * 0.55, max(0.6, 1.6 - i * 0.22), pack(*lerpc(tail, b["skyTop"], i / 6)))
        cv.disc(x, y, 1.4, pack(255, 255, 255))          # bright head
    else:  # bird-like
        flap = math.sin(t * 9 + c["ph"]) * 1.6
        cc = pack(*shade(b["far"], 0.85)); cv.thick(x - 2, y + flap, x, y, 1, cc); cv.thick(x, y, x + 2, y + flap, 1, cc)
