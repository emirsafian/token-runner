"""The running world. Scene holds the per-frame state; build_frame assembles a
whole frame (sky, ground, parallax scenery with real depth, the hero, the
optional companion, the trail, milestone signs, and the toasts).
"""
import math
import time
import random
from .render import pack, shade, lerpc, clampi
from .biomes import BIOMES, DAYLIGHT, LAYERS, biome_of, day_phase
from .sprites import SPR, draw_rock
from .runner import draw_runner, draw_dog
from .critters import CRITTERS, _spawn_critter, _draw_critter
from .fmt import human, rate_str


_tpl_cache = {}


def template(w, h, biome, phase="day"):
    key = (w, h, biome, phase)
    t = _tpl_cache.get(key)
    if t:
        return t
    b = BIOMES[biome]
    bright, tint, amt, _night = DAYLIGHT.get(phase, DAYLIGHT["day"])
    HY = int(h * 0.42)
    buf = [0] * (w * h)
    for y in range(h):
        if y < HY:
            c = lerpc(b["skyTop"], b["skyHaze"], y / max(1, HY))
        else:
            c = lerpc(b["gFar"], b["gNear"], (y - HY) / max(1, h - HY))
        if amt or bright != 1.0:
            c = lerpc(shade(c, bright), tint, amt)
        pc = pack(*c)
        base = y * w
        for x in range(w):
            buf[base + x] = pc
    _tpl_cache[key] = buf
    if len(_tpl_cache) > 16:
        _tpl_cache.pop(next(iter(_tpl_cache)))
    return buf


class Scene:
    def __init__(self):
        self.scroll = 0.0
        self.birds = []
        self.parts = []
        self._phase = 0.0
        self._gphase = 1.7          # ghost-of-yesterday cadence (starts out of phase)
        self._bphase = 3.4          # buddy companion cadence (its own offset)
        self.t = time.time()
        self.bird_at = 0.0
        self.crit_at = 0.0
        self.scenery = []
        self.scenery_biome = None
        self.critters = []
        self.signs = []             # milestone signposts streaming past
        self.banners = []           # transient toast notifications
        self.events = []            # event tags this frame (for sound)
        self.cur_biome = None       # for the "new biome" toast
        self.idle_since = None
        self.think_since = None

    def banner(self, text, col, now, dur=2.8):
        self.banners.append({"text": text, "col": col, "until": now + dur})
        if len(self.banners) > 4:
            self.banners = self.banners[-4:]

    def ensure(self, b, W, name):
        if self.scenery and self.scenery_biome == name:
            return
        self.scenery_biome = name
        self.scenery = []
        for li, (yf, sf, spd, n) in enumerate(LAYERS):
            for k in range(n):
                self.scenery.append({"x": random.uniform(0, W * 1.35), "lay": li,
                                     "kind": random.choice(b["kinds"]), "jit": random.uniform(0.8, 1.25),
                                     "front": random.random() < 0.45})   # passes in front of the hero?


def _draw_sign(cv, x, gy, s, b):
    """A roadside milestone signpost (the token number is announced in a toast)."""
    cv.thick(x, gy, x, gy - s * 1.4, max(1, int(s * 0.12)), pack(110, 80, 52))
    board = pack(242, 232, 202); edge = pack(180, 150, 90)
    cv.rect(x - s * 0.7, gy - s * 1.85, x + s * 0.7, gy - s * 1.2, board)
    cv.rect(x - s * 0.7, gy - s * 1.85, x + s * 0.7, gy - s * 1.77, edge)
    cv.rect(x - s * 0.55, gy - s * 1.55, x + s * 0.45, gy - s * 1.5, edge)     # "text" lines
    cv.rect(x - s * 0.55, gy - s * 1.42, x + s * 0.1, gy - s * 1.37, edge)
    cv.disc(x + s * 0.5, gy - s * 1.68, max(1, s * 0.12), pack(220, 70, 70))


def _blaze_glow(cv, speed):
    """Warm vignette on the screen edges while redlining."""
    W, H = cv.w, cv.h
    g = (255, 120, 40)
    amt = 0.16 + 0.22 * speed
    depth = max(2, int(H * 0.06))
    buf = cv.buf
    for d in range(depth):
        f = amt * (1 - d / depth)
        if f <= 0:
            continue
        for x in range(W):
            for y in (d, H - 1 - d):
                i = y * W + x; p = buf[i]
                buf[i] = pack(((p >> 16) & 255) * (1 - f) + g[0] * f,
                              ((p >> 8) & 255) * (1 - f) + g[1] * f,
                              (p & 255) * (1 - f) + g[2] * f)
        for y in range(H):
            for x in (d, W - 1 - d):
                i = y * W + x; p = buf[i]
                buf[i] = pack(((p >> 16) & 255) * (1 - f) + g[0] * f,
                              ((p >> 8) & 255) * (1 - f) + g[1] * f,
                              (p & 255) * (1 - f) + g[2] * f)


def build_frame(cv, eng, scene, cfg, now, records=None):
    W, H = cv.w, cv.h
    HY = int(H * 0.42)
    GY = H - 3
    rx = W * 0.27                                 # the hero's fixed x
    scene.events = []

    rate = eng.ewma_rate(now, cfg.tau)
    thinking = eng.in_flight(now)
    blk = eng.block(now)
    dist = blk[0]
    new_biome = getattr(cfg, "force_biome", None) or biome_of(dist)
    if scene.cur_biome is None:
        scene.cur_biome = new_biome
    elif new_biome != scene.cur_biome:
        scene.cur_biome = new_biome
        scene.banner("➜  ENTERING " + new_biome, BIOMES[new_biome]["accent"], now, dur=3.0)
        scene.events.append("biome")
    cfg.biome = new_biome
    b = BIOMES[cfg.biome]

    phase_name = getattr(cfg, "force_phase", None) or (day_phase(now) if getattr(cfg, "daylight", True) else "day")
    night = DAYLIGHT[phase_name][3]

    moving = rate > 0.6 and not (thinking and rate < 8)
    speed = min(rate, cfg.redline) / cfg.redline
    dt = min(0.2, max(0.0, now - scene.t)); scene.t = now
    lat = speed * 82 * dt if moving else 0.0   # base lateral pixels this frame
    scene.scroll += lat
    if moving:
        scene._phase += speed * 9 * dt
        scene._gphase += speed * 9 * dt * 0.93    # ghost: hero's cadence, gently detuned (never lockstep)
        scene._bphase += speed * 9 * dt * 0.97    # buddy: same idea, its own detune

    # idle / think timers (drive the sit-down + coffee poses)
    if thinking:
        scene.think_since = scene.think_since or now
        scene.idle_since = None
    elif moving:
        scene.think_since = scene.idle_since = None
    else:
        scene.idle_since = scene.idle_since or now
        scene.think_since = None
    idle_dur = (now - scene.idle_since) if scene.idle_since else 0.0
    think_dur = (now - scene.think_since) if scene.think_since else 0.0

    cv.fill_template(template(W, H, cfg.biome, phase_name))

    # ---- sky: stars at night/cosmos, sun or moon, clouds (or bubbles underwater)
    sunx = W * 0.78
    if night or cfg.biome == "COSMOS":
        for i in range(46):
            sx = (i * 53 + scene.scroll * 0.04) % W
            sy = (i * 29) % HY
            tw = 0.5 + 0.5 * math.sin(now * 2 + i)
            cv.px(sx, sy, pack(*lerpc((110, 110, 150), (255, 255, 255), (i % 5) / 5 * tw)))
    if cfg.biome == "COSMOS":
        cv.disc(sunx, HY * 0.4, H * 0.05, pack(*b["sun"]))
    elif night:
        cv.disc(sunx, HY * 0.34, H * 0.06, pack(226, 230, 246))            # moon
        cv.disc(sunx + H * 0.022, HY * 0.32, H * 0.05, pack(*lerpc((226, 230, 246), b["skyTop"], 0.45)))
    else:
        suny = HY * (0.4 if phase_name == "day" else 0.72)                 # low sun at dawn/dusk
        scol = b["sun"] if phase_name == "day" else lerpc(b["sun"], (255, 120, 60), 0.55)
        cv.disc(sunx, suny, H * 0.085, pack(*lerpc(scol, b["skyHaze"], 0.5)))
        cv.disc(sunx, suny, H * 0.05, pack(*scol))
    if cfg.biome == "OCEAN":                                               # rising bubbles
        span = max(4, GY - HY - 2)
        for i in range(16):
            bx = (i * 37 + 11) % W
            by = GY - int((now * 16 + i * 29) % span)
            cv.px(bx, by, pack(*lerpc(b["skyHaze"], (255, 255, 255), 0.5)))
    elif cfg.biome != "COSMOS":
        for i in range(4):
            cx = (W + 40) - (scene.scroll * 0.18 + i * W / 3.0) % (W + 80)
            cy = HY * (0.22 + 0.13 * (i % 3))
            cc = pack(*lerpc(b["skyHaze"], (255, 255, 255), 0.12 if night else 0.45))
            cv.ellipse(cx, cy, H * 0.06, H * 0.02, cc)
            cv.ellipse(cx + H * 0.05, cy + 1, H * 0.04, H * 0.016, cc)

    # ---- far silhouette ridge (slow parallax)
    sil = pack(*b["far"])
    for x in range(W):
        amp = H * 0.05
        yy = HY - int((math.sin((x + scene.scroll * 0.12) * 0.025) * 0.5 + 0.5) * amp)
        for y in range(yy, HY):
            cv.px(x, y, sil)

    # ---- ground: soft mid depth line + lateral tufts (speed cue, scroll left)
    midy = HY + max(1, int((GY - HY) * 0.34))
    ml = pack(*shade(lerpc(b["gFar"], b["gNear"], 0.45), 0.96))
    for x in range(0, W, 3):                      # faint dashed mid-ground, not a hard line
        cv.px(x, midy, ml)
    tlit = pack(*shade(b["gNear"], 1.3)); tdrk = pack(*shade(b["gNear"], 0.65))
    for i in range(W // 6):
        tx = (i * 6 - scene.scroll) % (W + 8)
        ty = GY - 1 + (i % 2)
        cv.px(tx, ty, tlit if i % 3 else tdrk)
        cv.px(tx + 1, ty, tdrk)

    # ---- scenery: lateral parallax layers (advance, recycle off-left)
    scene.ensure(b, W, cfg.biome)
    for it in scene.scenery:
        yf, sf, spd, _ = LAYERS[it["lay"]]
        it["x"] -= lat * spd
        size = max(1.5, H * sf * it["jit"])
        if it["x"] < -size * 3:
            it["x"] += W + size * 3 + random.uniform(0, W * 0.45)
            it["kind"] = random.choice(b["kinds"]); it["jit"] = random.uniform(0.8, 1.25)
            it["front"] = random.random() < 0.45    # re-roll depth each time it comes around
    for it in sorted(scene.scenery, key=lambda o: o["lay"]):  # far → near
        yf, sf, spd, _ = LAYERS[it["lay"]]
        size = max(1.5, H * sf * it["jit"])
        gy = HY + yf * (GY - HY)
        if -size * 3 < it["x"] < W + size * 3:
            cv.shadow_ground(it["x"], gy + 1, size * 1.0, max(1, size * 0.25))   # shadow always (under all)
            if it["lay"] == 2 and it.get("front"):
                continue                          # this one passes in front of the hero → sprite drawn later
            SPR.get(it["kind"], draw_rock)(cv, it["x"], min(gy, H - 2), size, b)

    # ---- milestone signposts (spawn on crossing a token threshold; scroll past)
    if records is not None:
        hit = records.check_milestone(dist)
        if hit:
            scene.signs.append({"x": W + 8, "m": hit})
            scene.banner("MILESTONE  " + human(hit) + " tokens this block", (255, 222, 120), now, dur=3.4)
            scene.events.append("milestone")
    for sg in scene.signs:
        sg["x"] -= lat
    scene.signs = [sg for sg in scene.signs if sg["x"] > -12]
    for sg in scene.signs:
        _draw_sign(cv, sg["x"], GY, max(6, H * 0.16), b)

    # ---- birds (drift left, flap), skipped underwater (fish handle it)
    if cfg.biome != "OCEAN":
        if now - scene.bird_at > 5 and len(scene.birds) < 3:
            scene.bird_at = now
            scene.birds.append({"x": W + 5, "y": HY * (0.3 + 0.4 * ((int(now) % 3) / 3)), "vx": -(18 + 14 * speed)})
        for bd in scene.birds:
            bd["x"] += bd["vx"] * dt
        scene.birds = [bd for bd in scene.birds if bd["x"] > -6]
        flap = math.sin(now * 9) * 1.6
        for bd in scene.birds:
            c = pack(*shade(b["far"], 0.8))
            cv.thick(bd["x"] - 2, bd["y"] + flap, bd["x"], bd["y"], 1, c)
            cv.thick(bd["x"], bd["y"], bd["x"] + 2, bd["y"] + flap, 1, c)

    # ---- ambient critters (one kind per biome, fireflies at night)
    if now - scene.crit_at > random.uniform(2.2, 4.5) and len(scene.critters) < 4:
        scene.crit_at = now
        _spawn_critter(scene, cfg.biome, W, H, HY, GY, night)
    for c in scene.critters:
        c["x"] += c["vx"] * dt; c["y"] += c.get("vy", 0.0) * dt; c["ph"] += dt
    scene.critters = [c for c in scene.critters if c["x"] > -12 and c["y"] > -4]
    for c in scene.critters:
        _draw_critter(cv, c, b, now)

    gy, rs = GY, max(7, H * 0.24)
    phase = scene._phase
    blaze = rate >= 130

    # ---- ghost of yesterday: a faint runner offset by your token gap vs this time y'day.
    #      Opt-in via the companion cycle, so 'solo' is truly just the hero (the
    #      numeric 'vs Y'DAY' stays in the HUD either way).
    if (records is not None and records.has_yesterday and abs(records.ghost_gap) > 200
            and getattr(cfg, "companion", None) == "ghost"):
        off = clampi(records.ghost_gap / 600.0, -W * 0.34, W * 0.34)   # ahead of y'day → ghost trails you
        ghx = clampi(rx - off, rs * 1.4, W - rs * 1.4)
        draw_runner(cv, ghx, gy, rs * 0.92, scene._gphase, rate, False, cfg.redline, now,
                    color_override=(150, 158, 178), ghost=True)

    # ---- trail
    if moving and rate > 24 and not thinking and (blaze or (int(now * 60) % 2) == 0):
        for _ in range(2 if blaze else 1):       # punchier trail at BLAZE
            scene.parts.append({"x": rx - rs * 0.45, "y": gy - rs * 0.1 * (now % 1), "vx": -(40 + rate) * 0.6,
                                "vy": -(10 + (50 if blaze else 0)) * (0.3 + 0.6 * (now % 1)),
                                "life": 0.45 + 0.35 * (now % 1), "blaze": blaze})
    for p in scene.parts:
        p["life"] -= dt; p["x"] += p["vx"] * dt; p["y"] += p["vy"] * dt; p["vy"] += 50 * dt
    scene.parts = [p for p in scene.parts if p["life"] > 0][-80:]
    for p in scene.parts:
        a = max(0.0, min(1.0, p["life"] * 2))
        c = (255, int(120 + 110 * a), 60) if p["blaze"] else lerpc((150, 150, 160), b["gNear"], 0.3)
        if p["blaze"]:
            cv.disc(p["x"], p["y"], 1.6, pack(*c))
        else:
            cv.px(p["x"], p["y"], pack(*c))

    # ---- companion (opt-in): a dog, or a friend who keeps pace beside you
    comp = getattr(cfg, "companion", None)
    if comp == "dog":
        draw_dog(cv, rx - rs * 1.35, gy, rs * 0.52, scene._phase * 1.6 if moving else now * 2, moving, now)
    elif comp == "buddy":
        draw_runner(cv, rx - rs * 1.5, gy, rs * 0.9, scene._bphase, rate, False, cfg.redline, now,
                    color_override=(120, 170, 235))

    # ---- the hero
    draw_runner(cv, rx, gy, rs, phase, rate, thinking, cfg.redline, now, idle_dur=idle_dur, think_dur=think_dur)

    # ---- foreground scenery flagged "front": drawn over the hero, so he passes behind it
    yf2, sf2 = LAYERS[2][0], LAYERS[2][1]
    for it in scene.scenery:
        if it["lay"] != 2 or not it.get("front"):
            continue
        size = max(1.5, H * sf2 * it["jit"])
        if -size * 3 < it["x"] < W + size * 3:
            SPR.get(it["kind"], draw_rock)(cv, it["x"], min(HY + yf2 * (GY - HY), H - 2), size, b)

    # ---- new personal best (after we know this frame's rate)
    if records is not None and records.tick_rate(rate, now):
        scene.banner("NEW PERSONAL BEST  " + rate_str(rate) + " tok/s", (255, 224, 120), now, dur=3.0)
        scene.events.append("pb")

    if blaze:
        _blaze_glow(cv, speed)

    return rate, thinking, dist, blk
