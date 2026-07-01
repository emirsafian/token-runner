"""The running world. Scene holds the per-frame state; build_frame assembles a
whole frame (sky, ground, parallax scenery with real depth, the hero, the
optional companion, the trail, milestone signs, and the toasts).
"""
import math
import time
import random
from .render import pack, shade, lerpc, clampi
from .biomes import BIOMES, DAYLIGHT, LAYERS, UNDERWATER, SURF, SPACEWALK, biome_of, day_phase
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
    for d in range(depth):
        f = amt * (1 - d / depth)
        if f <= 0:
            continue
        for x in range(W):
            cv.shade_px(x, d, g, f); cv.shade_px(x, H - 1 - d, g, f)
        for y in range(H):
            cv.shade_px(d, y, g, f); cv.shade_px(W - 1 - d, y, g, f)


def _surf_wave_top(px, W, HY, GY, scroll):
    """The sea-surface height (screen y) at column px: a big wave hump near cx,
    a trough dip in front of it, plus a small travelling ripple. Water is below."""
    span = GY - HY
    sea = HY + span * 0.5                                   # mean sea level
    cx = W * 0.44                                           # the breaking wave's crest, just behind the hero
    d = px - cx
    hump = math.exp(-(d * d) / (2 * (W * 0.17) ** 2)) * span * 0.42      # the wave rises here
    dl = px - (cx - W * 0.34)
    dip = math.exp(-(dl * dl) / (2 * (W * 0.11) ** 2)) * span * 0.07     # trough just ahead of the face
    ripple = math.sin(px * 0.12 - scroll * 0.06) * span * 0.02
    return sea - hump + dip + ripple


def _wave_tilt(px, W, HY, GY, scroll):
    """Slope of the wave face at px, as an angle, clamped — for tilting boards."""
    dy = _surf_wave_top(px + 2, W, HY, GY, scroll) - _surf_wave_top(px - 2, W, HY, GY, scroll)
    return max(-0.5, min(0.5, math.atan2(dy, 4.0)))


def _draw_surf_water(cv, b, HY, GY, scroll, t):
    """Paint the rideable wave: a glassy sunlit face, a foaming crest, a curling
    lip at the barrel, and drifting foam streaks as a speed cue."""
    W, H = cv.w, cv.h
    span = GY - HY
    cx = W * 0.44
    glass = lerpc(b["gFar"], (255, 255, 255), 0.24)
    deep = b["gNear"]
    foam = pack(255, 255, 255)
    foamc = pack(*lerpc(b["accent"], (255, 255, 255), 0.5))
    faceD = max(4, int(span * 0.6))
    for x in range(W):
        ti = int(_surf_wave_top(x, W, HY, GY, scroll))
        for j in range(faceD):                             # glassy face up top → deeper water below
            y = ti + j
            if 0 <= y < H:
                cv.px(x, y, pack(*lerpc(glass, deep, j / faceD)))
        if 0 <= ti < H:
            cv.px(x, ti, foam)                             # bright foam crest
        if 0 <= ti - 1 < H and (int(x + t * 8) % 5) < 2:
            cv.px(x, ti - 1, foamc)                        # broken spray flecks above it
    ly = _surf_wave_top(cx, W, HY, GY, scroll)             # curling lip of the barrel
    cv.disc(cx, ly - 1, max(1, span * 0.05), foam)
    for k in range(6):
        a = k / 5.0
        hx = cx - a * span * 0.5
        hy = ly - span * 0.06 * math.sin(a * math.pi) + math.sin(t * 3 + k) * 0.6
        cv.disc(hx, hy, max(0.6, span * 0.04 * (1 - a * 0.5)), foam)
    for i in range(W // 7):                                # foam streaks sliding across the open water
        fx = (i * 7 - scroll) % (W + 7)
        fy = _surf_wave_top(fx, W, HY, GY, scroll) + span * (0.3 + 0.12 * (i % 3))
        if fy < H:
            cv.px(fx, fy, foamc)


def _draw_space(cv, b, HY, GY, scroll, t):
    """Paint deep space: a drifting nebula wash, a distant star, a big planet limb
    curving across the lower frame (shaded by the star), and a parallax starfield
    with the stars correctly hidden behind the planet."""
    W, H = cv.w, cv.h
    neb1 = pack(*lerpc(b["skyTop"], b["accent"], 0.20))
    neb2 = pack(*lerpc(b["skyTop"], (170, 116, 214), 0.20))
    for i, nc in ((0, neb1), (1, neb2), (2, neb1)):                       # soft, slow-drifting clouds
        nx = (W * (0.18 + 0.32 * i) - scroll * (0.02 + 0.01 * i)) % (W + W * 0.6) - W * 0.3
        ny = HY * (0.26 + 0.22 * i)
        cv.ellipse(nx, ny, W * 0.15, H * 0.09, nc)

    sxp, syp = W * 0.82, HY * 0.4                                         # the distant star (light source)
    cv.disc(sxp, syp, max(1, H * 0.04), pack(*lerpc(b["skyHaze"], (255, 255, 255), 0.4)))   # halo
    cv.disc(sxp, syp, max(1, H * 0.02), pack(255, 255, 255))                                # core

    pcx, pcy, pr = W * 0.64, H * 1.16, H * 0.46                           # planet, mostly below frame
    base = lerpc(b["accent"], (54, 74, 120), 0.5)
    cdark = shade(base, 0.42); clit = lerpc(base, (236, 240, 255), 0.34)
    y0 = max(0, int(pcy - pr))
    for y in range(y0, H):                                                # row-scan only the visible cap
        dy = y - pcy
        if abs(dy) > pr:
            continue
        half = math.sqrt(max(0.0, pr * pr - dy * dy))
        for x in range(max(0, int(pcx - half)), min(W, int(pcx + half) + 1)):
            lit = max(0.0, (x - pcx) / pr * 0.72 - dy / pr * 0.72 + 0.28)   # lit toward the upper-right star
            cv.px(x, y, pack(*lerpc(cdark, clit, min(1.0, lit))))

    pr2 = pr * pr
    for i in range(64):                                                  # the starfield
        sx = (i * 73 + scroll * 0.05) % W
        sy = (i * 41 + (i * i) % 19) % H
        dx = sx - pcx; dy = sy - pcy
        if dx * dx + dy * dy <= pr2:
            continue                                                     # behind the planet
        tw = 0.45 + 0.55 * math.sin(t * 2.0 + i * 1.3)
        cv.px(sx, sy, pack(*lerpc((90, 96, 140), (255, 255, 255), max(0.0, (i % 5) / 5 * tw))))
        if i % 11 == 0:
            cv.px(sx, sy, pack(255, 255, 255))                           # a few brighter ones


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
    underwater = cfg.biome in UNDERWATER
    surf = cfg.biome in SURF
    space = cfg.biome in SPACEWALK

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

    cv.fill_template(template(cv.pw, H, cfg.biome, phase_name))
    if space:                                                              # the void: nebula, planet, starfield
        _draw_space(cv, b, HY, GY, scene.scroll, now)

    # ---- sky: stars at night/cosmos, sun or moon, clouds (or bubbles underwater)
    sunx = W * 0.78
    if (night or cfg.biome == "COSMOS") and not space:
        for i in range(46):
            sx = (i * 53 + scene.scroll * 0.04) % W
            sy = (i * 29) % HY
            tw = 0.5 + 0.5 * math.sin(now * 2 + i)
            cv.px(sx, sy, pack(*lerpc((110, 110, 150), (255, 255, 255), (i % 5) / 5 * tw)))
    if space:
        pass                                                              # planet already drawn by _draw_space
    elif cfg.biome == "COSMOS":
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
    elif cfg.biome != "COSMOS" and not space:
        for i in range(4):
            cx = (W + 40) - (scene.scroll * 0.18 + i * W / 3.0) % (W + 80)
            cy = HY * (0.22 + 0.13 * (i % 3))
            cc = pack(*lerpc(b["skyHaze"], (255, 255, 255), 0.12 if night else 0.45))
            cv.ellipse(cx, cy, H * 0.06, H * 0.02, cc)
            cv.ellipse(cx + H * 0.05, cy + 1, H * 0.04, H * 0.016, cc)

    # ---- god rays: slanted light shafts drifting down through the water column
    if underwater:
        rc = lerpc((255, 255, 255), b["skyHaze"], 0.35)
        bandw = max(2, int(W * 0.04))
        for k in range(3):
            cx0 = (k * W / 2.6 + scene.scroll * 0.05) % (W + 80) - 40
            for yy in range(GY):
                f = 0.22 * (1 - yy / max(1, GY))                 # brightest near the surface
                if f <= 0.01:
                    continue
                cxx = int(cx0 + yy * 0.5)                        # slant the shaft as it descends
                for dx in range(bandw):
                    cv.shade_px(cxx + dx, yy, rc, f)

    # ---- surf: paint the rolling wave the hero and companion ride on
    if surf:
        _draw_surf_water(cv, b, HY, GY, scene.scroll, now)

    # ---- far silhouette ridge (slow parallax), but the void has no horizon
    if not space:
        sil = pack(*b["far"])
        for x in range(W):
            amp = H * 0.05
            yy = HY - int((math.sin((x + scene.scroll * 0.12) * 0.025) * 0.5 + 0.5) * amp)
            for y in range(yy, HY):
                cv.px(x, y, sil)

    # ---- ground: soft mid depth line + lateral tufts (speed cue, scroll left)
    if not surf and not space:                    # surf has its own water; space has no ground
        midy = HY + max(1, int((GY - HY) * 0.34))
        ml = pack(*shade(lerpc(b["gFar"], b["gNear"], 0.45), 0.96))
        for x in range(0, W, 3):                  # faint dashed mid-ground, not a hard line
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
        # on the surf, buoys + boats bob on the wave surface; on land they sit on their layer's ground
        gy_it = _surf_wave_top(it["x"], W, HY, GY, scene.scroll) if surf else HY + yf * (GY - HY)
        if -size * 3 < it["x"] < W + size * 3:
            if not space:                         # floating debris in the void casts no ground shadow
                cv.shadow_ground(it["x"], gy_it + 1, size * 1.0, max(1, size * 0.25))
            if it["lay"] == 2 and it.get("front") and not surf:
                continue                          # this one passes in front of the hero → sprite drawn later
            SPR.get(it["kind"], draw_rock)(cv, it["x"], min(gy_it, H - 2), size, b)

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

    # ---- birds (drift left, flap), skipped underwater (fish handle it) and in space
    if cfg.biome != "OCEAN" and not space:
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
        ggy = _surf_wave_top(ghx, W, HY, GY, scene.scroll) if surf else gy
        gtilt = _wave_tilt(ghx, W, HY, GY, scene.scroll) if surf else 0.0
        draw_runner(cv, ghx, ggy, rs * 0.92, scene._gphase, rate, False, cfg.redline, now,
                    color_override=(150, 158, 178), ghost=True, underwater=underwater, surf=surf, tilt=gtilt, space=space)

    # ---- trail (dust kicked up on land; the surf scene makes its own spray)
    if moving and rate > 24 and not thinking and not surf and not space and (blaze or (int(now * 60) % 2) == 0):
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
        cx_ = rx - rs * 1.35
        cgy = _surf_wave_top(cx_, W, HY, GY, scene.scroll) if surf else gy
        draw_dog(cv, cx_, cgy, rs * 0.52, scene._phase * 1.6 if moving else now * 2, moving, now,
                 underwater=underwater, surf=surf, tilt=_wave_tilt(cx_, W, HY, GY, scene.scroll) if surf else 0.0,
                 space=space)
    elif comp == "buddy":
        bx_ = rx - rs * 1.5
        bgy = _surf_wave_top(bx_, W, HY, GY, scene.scroll) if surf else gy
        draw_runner(cv, bx_, bgy, rs * 0.9, scene._bphase, rate, False, cfg.redline, now,
                    color_override=(120, 170, 235), underwater=underwater, surf=surf,
                    tilt=_wave_tilt(bx_, W, HY, GY, scene.scroll) if surf else 0.0, space=space)

    # ---- the hero
    hgy = _surf_wave_top(rx, W, HY, GY, scene.scroll) if surf else gy
    draw_runner(cv, rx, hgy, rs, phase, rate, thinking, cfg.redline, now, idle_dur=idle_dur, think_dur=think_dur,
                underwater=underwater, surf=surf, tilt=_wave_tilt(rx, W, HY, GY, scene.scroll) if surf else 0.0,
                space=space)

    # ---- foreground scenery flagged "front": drawn over the hero, so he passes behind it
    yf2, sf2 = LAYERS[2][0], LAYERS[2][1]
    for it in scene.scenery:
        if surf or it["lay"] != 2 or not it.get("front"):
            continue                              # surf draws all its buoys/boats behind the rider
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
