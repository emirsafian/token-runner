"""The hero runner and the dog companion: 2-bone IK limbs, the gait and lean,
the idle sit-down and coffee poses, the horizontal diver-swim (flutter kick,
fins, tank, bubbles — a doggy-paddle for the dog) they switch to in submerged
biomes, the surfboard pose they ride on the wave in the surf biome, and the
zero-g float (spacesuit, bubble helmet, life-support pack, thruster jets) they
drift in out in open space.
"""
import math
from .render import pack, shade, lerpc, grad, speedT


def _ik(ox, oy, tx, ty, l, forward):
    """2-bone IK (equal bones len l). Returns the knee/elbow so it bends the
    correct way: forward=True → joint ahead (+x) for knees; False → behind for elbows."""
    dx, dy = tx - ox, ty - oy
    d = min(math.hypot(dx, dy) or 1e-6, 2 * l - 1e-3)
    a = d / 2.0
    h = math.sqrt(max(0.0, l * l - a * a))
    ax, ay = dx / d, dy / d
    px, py = -ay, ax
    k1 = (ox + ax * a + px * h, oy + ay * a + py * h)
    k2 = (ox + ax * a - px * h, oy + ay * a - py * h)
    if forward:
        return k1 if k1[0] >= k2[0] else k2
    return k1 if k1[0] <= k2[0] else k2


def _draw_stool(cv, x, gy, s):
    """A little wooden stool for the idle runner to rest on."""
    wood = pack(150, 104, 60); woodd = pack(108, 72, 40); lite = pack(178, 130, 80)
    seat_y = gy - s * 0.55
    seat_h = max(1, int(s * 0.13))
    cv.rect(x - s * 0.52, seat_y, x + s * 0.52, seat_y + seat_h, wood)        # seat slab
    cv.rect(x - s * 0.52, seat_y, x + s * 0.52, seat_y + 1, lite)             # top highlight
    legw = max(1, int(s * 0.1))
    for lx in (-s * 0.42, s * 0.42):                                          # splayed legs
        cv.thick(x + lx, seat_y + seat_h, x + lx * 0.78, gy, legw, woodd)
    cv.thick(x - s * 0.34, gy - s * 0.2, x + s * 0.34, gy - s * 0.2, max(1, legw - 1), woodd)  # rung


def _draw_sit(cv, x, gy, s, cM, cD, cL, zzz, t_now):
    """An idle runner taking a breather on a little stool while you're away."""
    th = max(2, int(s * 0.24))
    breathe = math.sin(t_now * 1.6) * s * 0.04
    _draw_stool(cv, x, gy, s)                          # the seat, behind the body
    hx, hy = x, gy - s * 0.62                          # hips resting on the seat
    sx, sy = hx + s * 0.04, hy - s * 0.82 + breathe   # near-upright torso
    # thighs ~level on the seat → shins drop to feet on the ground
    for off, cc in ((s * 0.1, cD), (-s * 0.06, cM)):
        kx, ky = hx + s * 0.56 + off, hy + s * 0.04
        fx, fy = hx + s * 0.62 + off, gy
        cv.thick(hx, hy, kx, ky, th, cc)
        cv.thick(kx, ky, fx, fy, max(1, th - 1), cc)
    cv.thick(hx, hy, sx, sy, th + 1, cM)             # torso
    cv.thick(hx + 1, hy - 1, sx, sy, max(1, th - 1), cL)
    ex, ey = sx + s * 0.46, sy + s * 0.52            # arm resting on the thigh
    cv.thick(sx, sy, ex, ey, max(1, th - 1), cD)
    hr = s * 0.32
    hcx, hcy = sx + s * 0.18, sy - hr * 1.05
    cv.disc(hcx, hcy, hr, cM)
    cv.disc(hcx + hr * 0.35, hcy - hr * 0.1, hr * 0.5, cL)
    if zzz:                                          # drifting off, Zzz
        for i in range(3):
            zc = pack(*lerpc((150, 160, 190), (235, 240, 250), i / 2))
            ph = (t_now * 0.8 + i * 0.5) % 1.0
            cv.rect(hcx + s * 0.5 + i * s * 0.32, hcy - hr * 1.6 - i * s * 0.36 - ph * s * 0.3,
                    hcx + s * 0.5 + i * s * 0.32 + (2 + i), hcy - hr * 1.6 - i * s * 0.36 - ph * s * 0.3 + (2 + i), zc)


def _draw_coffee(cv, x, y, s):
    """A little steaming cup, shown over the head during a long think."""
    cup = pack(238, 240, 248); rim = pack(200, 205, 218)
    cv.rect(x - s * 0.22, y - s * 0.18, x + s * 0.22, y + s * 0.12, cup)
    cv.rect(x - s * 0.22, y - s * 0.18, x + s * 0.22, y - s * 0.1, rim)
    cv.rect(x - s * 0.32, y - s * 0.1, x - s * 0.22, y + s * 0.04, rim)   # handle
    cv.rect(x - s * 0.16, y - s * 0.06, x + s * 0.16, y + s * 0.08, pack(120, 78, 50))  # coffee
    for i in range(2):                                                    # steam
        cv.disc(x - s * 0.06 + i * s * 0.14, y - s * 0.32 - i * s * 0.06, 1, pack(210, 215, 225))


def _bubbles(cv, x, y, s, t, n=4):
    """Air bubbles streaming up from a regulator/snout (deterministic, no RNG)."""
    bc = pack(212, 240, 248); bl = pack(255, 255, 255)
    for i in range(n):
        ph = (t * 0.6 + i / n) % 1.0                  # each bubble's rise cycle
        bx = x + math.sin(t * 2.2 + i * 1.7) * s * 0.16
        by = y - ph * s * 1.9
        r = max(0.5, s * (0.05 + 0.06 * ph))          # swells a touch as it rises
        cv.disc(bx, by, r, bc)
        cv.px(bx - r * 0.4, by - r * 0.4, bl)         # little glint


def _draw_dive(cv, x, gy, s, col, t, phase, rate, thinking, redline, ghost):
    """A scuba diver swimming horizontally (not walking): near-prone body, arms
    streamlined ahead, a flutter kick with fins, tank on the back, bubbles rising.
    Drives every swimmer in the deep — hero, buddy, ghost (companion dog has its
    own paddle). Hovers mid-water; only a faint shadow is left on the seabed."""
    cM = pack(*col); cD = pack(*shade(col, 0.6)); cL = pack(*lerpc(col, (255, 255, 255), 0.4))
    cF = pack(*shade(col, 0.48))
    th = max(2, int(s * 0.22))
    speed = min(rate, redline) / redline
    moving = rate > 0.6 and not (thinking and rate < 8)

    bt = math.sin(t * 1.3) * 0.06 - speed * 0.05    # near-horizontal, gentle porpoise, nose-down when fast
    ax, ay = math.cos(bt), math.sin(bt)             # forward, toward the head (+x)
    nx, ny = math.sin(bt), -math.cos(bt)            # up, out of the diver's back
    cy = gy - s * 1.15 + math.sin(t * 1.1) * s * 0.07   # hover mid-water with a slow bob
    hipx, hipy = x - ax * s * 0.55, cy - ay * s * 0.55
    shx, shy = x + ax * s * 0.5, cy + ay * s * 0.5
    hr = s * 0.3
    hcx, hcy = shx + ax * hr * 1.15, shy + ay * hr * 1.15
    finc = pack(*shade(col, 0.5))

    kick = math.sin(phase) if moving else math.sin(t * 2.2) * 0.55       # flutter-kick cadence
    kamp = s * (0.16 + 0.34 * speed) if moving else s * 0.1
    legSpan, armSpan = s * 1.15, s * 0.98

    cv.shadow_ground(x, gy + 1, s * 0.9, max(1, s * 0.16))              # faint shadow on the seabed

    def kicker(sign, w, c1, fin):
        k = kick * sign * kamp
        midx, midy = hipx - ax * legSpan * 0.5 + nx * k * 0.45, hipy - ay * legSpan * 0.5 + ny * k * 0.45
        ftx, fty = hipx - ax * legSpan + nx * k, hipy - ay * legSpan + ny * k
        cv.thick(hipx, hipy, midx, midy, w, c1)
        cv.thick(midx, midy, ftx, fty, max(1, w - 1), c1)
        if fin:                                      # flipper trailing off the foot
            cv.ellipse(ftx - ax * s * 0.3, fty - ay * s * 0.3, s * 0.32, s * 0.12, finc)

    def streamline(sign, w, c1):                     # arm reaching forward in a glide
        a = (math.sin(phase + 1.2) if moving else math.sin(t * 2.0)) * s * 0.08
        cv.thick(shx, shy, shx + ax * armSpan + nx * (sign * s * 0.1 + a),
                 shy + ay * armSpan + ny * (sign * s * 0.1 + a), w, c1)

    kicker(-1, max(1, th - 1), cF, not ghost)        # far leg + far arm (dimmer, behind)
    streamline(-1, max(1, th - 1), cF)
    if not ghost:                                    # air tank along the back (the up-side)
        tax, tay = hipx + ax * s * 0.15 + nx * s * 0.24, hipy + ay * s * 0.15 + ny * s * 0.24
        tbx, tby = shx - ax * s * 0.1 + nx * s * 0.24, shy - ay * s * 0.1 + ny * s * 0.24
        cv.thick(tax, tay, tbx, tby, max(2, int(s * 0.24)), pack(*shade((120, 200, 210), 0.68)))
        cv.thick(tax, tay, tbx, tby, max(1, int(s * 0.13)), pack(120, 200, 210))
        cv.disc(tax, tay, max(1, s * 0.08), pack(150, 158, 168))        # valve
    cv.thick(hipx, hipy, shx, shy, th + 1, cM)       # torso
    cv.thick(hipx + nx, hipy + ny, shx + nx, shy + ny, max(1, th - 1), cL)
    kicker(+1, th, cD, not ghost)                    # near leg + near arm
    streamline(+1, th, cM)
    cv.disc(hcx, hcy, hr, cM)
    cv.disc(hcx + ax * hr * 0.3 - nx * hr * 0.1, hcy + ay * hr * 0.3 - ny * hr * 0.1, hr * 0.5, cL)
    if not ghost:
        _draw_mask(cv, hcx, hcy, hr, s)              # dive mask + regulator
        _bubbles(cv, hcx + ax * hr * 0.4, hcy - hr * 0.6, s, t)         # bubbles rise straight up
    if thinking and not ghost:                       # pondering mid-dive → think dots above the head
        n = (int(t * 3) % 3) + 1
        for i in range(n):
            cv.disc(hcx + s * 0.3 + i * s * 0.28, hcy - hr * 1.5 - i * s * 0.22, 1 + i * 0.7, pack(150, 140, 235))


def _draw_mask(cv, hcx, hcy, hr, s):
    """A dive mask over the face with a regulator mouthpiece below it."""
    strap = pack(40, 46, 54); frame = pack(228, 234, 240); glass = pack(150, 220, 235)
    cv.thick(hcx - hr * 0.95, hcy - hr * 0.12, hcx + hr * 0.8, hcy - hr * 0.18,
             max(1, int(s * 0.07)), strap)                                  # strap round the head
    cv.ellipse(hcx + hr * 0.5, hcy, hr * 0.64, hr * 0.56, frame)            # mask frame
    cv.ellipse(hcx + hr * 0.5, hcy, hr * 0.46, hr * 0.4, glass)             # glass
    cv.disc(hcx + hr * 0.72, hcy - hr * 0.16, max(1, hr * 0.14), pack(255, 255, 255))  # glint
    cv.disc(hcx + hr * 0.62, hcy + hr * 0.62, max(1, s * 0.08), strap)      # regulator mouthpiece


def _draw_surfboard(cv, x, y, L, stripe, tilt):
    """A surfboard centred at (x, y), length 2L, aligned to the wave-face slope."""
    ax, ay = math.cos(tilt), math.sin(tilt)
    nx, ny = x + ax * L, y + ay * L                 # nose (down the line, +x)
    tx, ty = x - ax * L, y - ay * L                 # tail
    cv.thick(tx, ty, nx, ny, max(2, int(L * 0.32)), pack(196, 150, 96))                 # rail / underside
    cv.thick(tx, ty - 1, nx, ny - 1, max(1, int(L * 0.2)), pack(245, 240, 222))         # deck
    cv.thick(tx, ty - 1, nx, ny - 1, max(1, int(L * 0.09)), pack(*stripe))              # centre stripe
    cv.disc(nx, ny - 1, max(1, L * 0.16), pack(245, 240, 222))                          # rounded nose


def _draw_surf(cv, x, y, s, col, t, tilt, fast, ghost):
    """A surfer crouched on a board, riding the wave face — arms out for balance."""
    cM = pack(*col); cD = pack(*shade(col, 0.6)); cL = pack(*lerpc(col, (255, 255, 255), 0.4))
    cF = pack(*shade(col, 0.48))
    th = max(2, int(s * 0.22))
    ax, ay = math.cos(tilt), math.sin(tilt)         # along the board (down the line)
    nx, ny = math.sin(tilt), -math.cos(tilt)        # up out of the water
    wob = math.sin(t * 2.3) * s * 0.04              # balance wobble
    L = s * 0.98

    cv.shadow_ground(x, y + 1, s * 1.05, max(1, s * 0.22))           # board shadow on the water
    if not ghost and fast > 0.45:                                    # spray kicking off the tail
        for i in range(3):
            ph = (t * 3 + i / 3.0) % 1.0
            sx = x - ax * L * (1.0 + ph * 0.7); sy = y - ay * L - ph * s * 0.5
            cv.disc(sx, sy, max(0.6, s * (0.12 - 0.08 * ph)), pack(*lerpc(col, (255, 255, 255), 0.7)))
    _draw_surfboard(cv, x, y, L, lerpc(col, (255, 255, 255), 0.35), tilt)

    foot = s * 0.07
    ffx, ffy = x + ax * L * 0.44 + nx * foot, y + ay * L * 0.44 + ny * foot   # front foot
    bfx, bfy = x - ax * L * 0.42 + nx * foot, y - ay * L * 0.42 + ny * foot   # back foot
    ch = s * (0.8 - 0.28 * fast)                    # lower, more aggressive crouch when fast
    hpx = x + nx * ch - ax * s * 0.05               # hips, just back of centre
    hpy = y + ny * ch - ay * s * 0.05 + wob
    tl = s * 0.8
    leanf = 0.16 + 0.34 * fast
    shx = hpx + nx * tl + ax * s * leanf            # shoulders lean down the line
    shy = hpy + ny * tl + ay * s * leanf
    legL, armL = s * 0.6, s * 0.46

    def limb(ox, oy, tx2, ty2, ln, fwd, w, c1, c2):
        jx, jy = _ik(ox, oy, tx2, ty2, ln, fwd)
        cv.thick(ox, oy, jx, jy, w, c1)
        cv.thick(jx, jy, tx2, ty2, max(1, w - 1), c2)

    fhx, fhy = shx + ax * s * 0.92 - nx * s * 0.12, shy + ay * s * 0.92 - ny * s * 0.12  # front hand reaches ahead
    bhx = shx - ax * s * 0.5 + nx * s * 0.5                                              # back hand up for balance
    bhy = shy - ay * s * 0.5 + ny * s * 0.5 + wob
    limb(hpx, hpy, bfx, bfy, legL, True, max(1, th - 1), cF, cF)     # back leg (far)
    limb(shx, shy, bhx, bhy, armL, False, max(1, th - 1), cF, cF)    # back arm (far)
    cv.thick(hpx, hpy, shx, shy, th + 1, cM)                         # torso
    cv.thick(hpx + nx, hpy + ny, shx + nx, shy + ny, max(1, th - 1), cL)
    limb(hpx, hpy, ffx, ffy, legL, True, th, cD, cM)                 # front leg (near)
    limb(shx, shy, fhx, fhy, armL, False, th, cD, cM)                # front arm (near)
    hr = s * 0.3
    hcx = shx + nx * hr * 1.05 + ax * hr * 0.4
    hcy = shy + ny * hr * 1.05 + ay * hr * 0.4
    cv.disc(hcx, hcy, hr, cM)
    cv.disc(hcx + ax * hr * 0.3 - nx * hr * 0.1, hcy + ay * hr * 0.3 - ny * hr * 0.1, hr * 0.5, cL)


def _jets(cv, x, y, ax, ay, s, t, power, n=3):
    """Thruster exhaust puffing backward (away from +x travel) off the pack — the
    space speed cue. Brighter and longer the faster you go (deterministic)."""
    for i in range(n):
        ph = (t * 3.2 + i / n) % 1.0
        jx = x - ax * s * (0.2 + ph * 1.25)
        jy = y - ay * s * (0.2 + ph * 1.25)
        r = max(0.6, s * (0.06 + 0.16 * power) * (1.0 - ph * 0.7))
        cv.disc(jx, jy, r, pack(*lerpc((255, 255, 255), (110, 170, 255), ph)))


def _helmet_dome(cv, hcx, hcy, hr):
    """The clear glass bubble of a space helmet — draw the head over it so it
    reads as a dome ringing the face."""
    cv.disc(hcx, hcy, hr * 1.36, pack(178, 216, 240))


def _helmet_shine(cv, hcx, hcy, hr, s):
    """The neck rim, a curved reflection streak and a glint on the dome."""
    cv.thick(hcx - hr * 1.02, hcy + hr * 0.8, hcx + hr * 1.02, hcy + hr * 0.8,
             max(1, int(s * 0.06)), pack(150, 196, 222))                       # neck rim
    cv.thick(hcx - hr * 0.62, hcy - hr * 0.78, hcx - hr * 0.12, hcy - hr * 1.2,
             max(1, int(s * 0.06)), pack(236, 248, 255))                       # reflection streak
    cv.disc(hcx - hr * 0.5, hcy - hr * 0.5, max(1, hr * 0.2), pack(255, 255, 255))  # bright glint


def _draw_float(cv, x, gy, s, col, t, phase, rate, thinking, redline, ghost):
    """An astronaut adrift in zero-g: a relaxed, near-horizontal float with a slow
    scissor-drift of the limbs, a life-support pack on the back, a bubble helmet,
    and thruster jets that puff as you accelerate. Drives every floater — hero,
    buddy, ghost (the dog paddles in its own helmet). No ground in the void, so no
    shadow is cast; the body simply hovers high in frame."""
    cM = pack(*col); cD = pack(*shade(col, 0.6)); cL = pack(*lerpc(col, (255, 255, 255), 0.4))
    cF = pack(*shade(col, 0.48))
    th = max(2, int(s * 0.22))
    speed = min(rate, redline) / redline
    moving = rate > 0.6 and not (thinking and rate < 8)

    bt = -0.12 + math.sin(t * 0.9) * 0.07 - speed * 0.06   # head-up recline, slow tumble, nose-in when fast
    ax, ay = math.cos(bt), math.sin(bt)                    # forward, toward the head (+x)
    nx, ny = math.sin(bt), -math.cos(bt)                   # up, out of the back
    cy = gy - s * 1.55 + math.sin(t * 0.8) * s * 0.12      # float high off the (absent) ground, slow bob
    hipx, hipy = x - ax * s * 0.55, cy - ay * s * 0.55
    shx, shy = x + ax * s * 0.5, cy + ay * s * 0.5
    hr = s * 0.3
    hcx, hcy = shx + ax * hr * 1.15, shy + ay * hr * 1.15

    drift = math.sin(phase) if moving else math.sin(t * 1.1) * 0.6      # slow scissor cadence
    kamp = s * (0.2 + 0.2 * speed) if moving else s * 0.16
    legSpan, armSpan = s * 1.05, s * 0.92

    if not ghost:                                          # life-support pack, jets firing under power
        bpx = (hipx + shx) * 0.5 + nx * s * 0.28
        bpy = (hipy + shy) * 0.5 + ny * s * 0.28
        cv.thick(bpx - ax * s * 0.3, bpy - ay * s * 0.3, bpx + ax * s * 0.3, bpy + ay * s * 0.3,
                 max(2, int(s * 0.34)), pack(214, 218, 226))              # pack body
        cv.thick(bpx - ax * s * 0.3, bpy - ay * s * 0.3, bpx, bpy,
                 max(1, int(s * 0.18)), pack(150, 156, 168))             # shaded half
        if moving and speed > 0.05:
            _jets(cv, hipx + nx * s * 0.16, hipy + ny * s * 0.16, ax, ay, s, t, speed)

    def limb(span, sign, w, c1, bend):                    # a loose drifting leg off the hip
        k = drift * sign * kamp
        midx = hipx - ax * span * 0.5 + nx * (k * 0.5 + sign * bend)
        midy = hipy - ay * span * 0.5 + ny * (k * 0.5 + sign * bend)
        ftx = hipx - ax * span + nx * k
        fty = hipy - ay * span + ny * k
        cv.thick(hipx, hipy, midx, midy, w, c1)
        cv.thick(midx, midy, ftx, fty, max(1, w - 1), c1)

    def arm(sign, w, c1):                                 # arms reaching loosely ahead
        a = (math.sin(phase + 1.0) if moving else math.sin(t * 1.0)) * s * 0.12
        cv.thick(shx, shy, shx + ax * armSpan + nx * (sign * s * 0.18 + a),
                 shy + ay * armSpan + ny * (sign * s * 0.18 + a), w, c1)

    limb(legSpan, -1, max(1, th - 1), cF, s * 0.12)       # far leg + far arm (dim, behind)
    arm(-1, max(1, th - 1), cF)
    cv.thick(hipx, hipy, shx, shy, th + 1, cM)            # torso
    cv.thick(hipx + nx, hipy + ny, shx + nx, shy + ny, max(1, th - 1), cL)
    limb(legSpan, +1, th, cD, s * 0.12)                   # near leg + near arm
    arm(+1, th, cM)
    if not ghost:                                         # suit chest light
        cv.disc(shx - ax * s * 0.1 + nx * s * 0.16, shy - ay * s * 0.1 + ny * s * 0.16,
                max(1, s * 0.07), pack(120, 220, 160))
        _helmet_dome(cv, hcx, hcy, hr)
    cv.disc(hcx, hcy, hr, cM)                             # head, inside the dome
    cv.disc(hcx + ax * hr * 0.3 - nx * hr * 0.1, hcy + ay * hr * 0.3 - ny * hr * 0.1, hr * 0.5, cL)
    if not ghost:
        _helmet_shine(cv, hcx, hcy, hr, s)
    if thinking and not ghost:                            # pondering adrift → think dots above
        n = (int(t * 3) % 3) + 1
        for i in range(n):
            cv.disc(hcx + s * 0.3 + i * s * 0.28, hcy - hr * 1.7 - i * s * 0.22, 1 + i * 0.7, pack(150, 140, 235))


def draw_runner(cv, x, gy, s, phase, rate, thinking, redline, t_now,
                idle_dur=0.0, think_dur=0.0, color_override=None, ghost=False,
                underwater=False, surf=False, tilt=0.0, space=False):
    moving = rate > 0.6 and not (thinking and rate < 8)
    col = color_override or grad(speedT(rate, redline))
    cM = pack(*col); cD = pack(*shade(col, 0.6)); cL = pack(*lerpc(col, (255, 255, 255), 0.4))
    cF = pack(*shade(col, 0.48))                    # far-side limbs, dimmer for depth

    if surf:                                         # riding the wave on a board (overrides the gait)
        _draw_surf(cv, x, gy, s, col, t_now, tilt, min(rate, redline) / redline, ghost)
        return
    if underwater:                                   # swimming horizontally like a diver (overrides the gait)
        _draw_dive(cv, x, gy, s, col, t_now, phase, rate, thinking, redline, ghost)
        return
    if space:                                        # floating in zero-g (overrides the gait)
        _draw_float(cv, x, gy, s, col, t_now, phase, rate, thinking, redline, ghost)
        return

    if not ghost:
        if not moving and not thinking and idle_dur >= 5.0:      # been idle a while → sit down
            cv.shadow_ground(x, gy + 1, s * 0.9, max(1, s * 0.22))
            _draw_sit(cv, x, gy, s, cM, cD, cL, idle_dur >= 14.0, t_now)
            return

    th = max(2, int(s * 0.24))
    speed = min(rate, redline) / redline
    lean = (0.05 if not moving else 0.09) + speed * 0.20  # gentle athletic lean (was a hunched ~45°)
    stride = (s * 0.5) if moving else (s * 0.14)
    lift = (s * 0.52) if moving else 0.0
    bob = (abs(math.sin(phase)) * s * 0.10) if moving else 0.0
    legL, armL = s * 0.66, s * 0.42
    hx, hy = x, gy - s * 1.15 - bob                 # hip
    sx = hx + math.sin(lean) * s * 1.0              # shoulder (forward by lean)
    sy = hy - math.cos(lean) * s * 1.0

    def leg(p, ct, cs, w):
        # foot follows a real gait: plant forward → push back on ground → lift & recover
        fx = hx + math.sin(p) * stride
        fy = gy - lift * max(0.0, math.cos(p))
        kx, ky = _ik(hx, hy, fx, fy, legL, True)    # knee forward
        cv.thick(hx, hy, kx, ky, w, ct)
        cv.thick(kx, ky, fx, fy, max(1, w - 1), cs)
        cv.disc(kx, ky, max(1, w * 0.5), ct)        # rounded knee
        cv.ellipse(fx + s * 0.07, fy - s * 0.015, s * 0.17, max(1, s * 0.075), cs)  # foot, toes forward

    def arm(p, cu, cf, w):
        ahx = sx + math.sin(p) * stride * 0.8
        ahy = sy + s * 0.8
        ex, ey = _ik(sx, sy, ahx, ahy, armL, False)  # elbow back
        cv.thick(sx, sy, ex, ey, w, cu)
        cv.thick(ex, ey, ahx, ahy, max(1, w - 1), cf)
        cv.disc(ahx, ahy, max(1, s * 0.09), cf)     # hand

    if ghost:
        cv.shadow_ground(x, gy + 1, s * 0.7, max(1, s * 0.16))
    else:
        cv.shadow_ground(x, gy + 1, s * 1.0, max(1, s * 0.26))
    leg(phase + math.pi, cF, cF, max(1, th - 1))     # far leg (behind), arm opposite phase
    arm(phase, cF, cF, max(1, th - 1))
    cv.disc(hx, hy, max(1, th * 0.6), cM)            # hip joint
    cv.thick(hx, hy, sx, sy, th + 1, cM)             # torso
    cv.thick(hx + 1, hy - 1, sx, sy, max(1, th - 1), cL)
    cv.disc(sx, sy, max(1, th * 0.62), cM)           # shoulder
    cv.disc(sx + math.sin(lean) * th * 0.2, sy - th * 0.2, max(1, th * 0.4), cL)  # chest highlight
    leg(phase, cD, cM, th)                            # near leg (front)
    arm(phase + math.pi, cD, cM, th)
    hr = s * 0.32                                     # head, ahead of shoulders (faces right)
    hcx = sx + math.sin(lean) * hr * 0.8
    hcy = sy - math.cos(lean) * hr * 1.05
    cv.disc(hcx, hcy, hr, cM)
    cv.disc(hcx + hr * 0.35, hcy - hr * 0.1, hr * 0.5, cL)
    if s > 7:
        cv.disc(hcx + hr * 0.52, hcy + hr * 0.04, max(1, s * 0.045), pack(38, 40, 52))  # eye, faces right

    if thinking and not ghost:
        if think_dur >= 8.0:                         # long think → coffee break
            _draw_coffee(cv, hcx + s * 0.7, hcy - hr * 1.7, s)
        else:
            n = (int(t_now * 3) % 3) + 1
            for i in range(n):
                cv.disc(hcx + s * 0.55 + i * s * 0.3, hcy - hr * 1.7 - i * s * 0.2, 1 + i * 0.8, pack(150, 140, 235))


# ----------------------------------------------------------------------------- companion dog
def _draw_dog_scuba(cv, bx, by, bw, bh, hx2, hy2, s):
    """A mini air tank along the spine + a dive mask for the companion dog."""
    tankc = (120, 200, 210); tankd = shade(tankc, 0.68)
    tx, ty = bx - bw * 0.1, by - bh * 0.75                                    # strapped on the back
    cv.thick(tx - bw * 0.22, ty, tx + bw * 0.22, ty, max(2, int(s * 0.2)), pack(*tankd))
    cv.thick(tx - bw * 0.22, ty, tx + bw * 0.06, ty, max(1, int(s * 0.11)), pack(*tankc))
    cv.disc(tx + bw * 0.24, ty, max(1, s * 0.07), pack(150, 158, 168))        # valve
    frame = pack(228, 234, 240); glass = pack(150, 220, 235); strap = pack(40, 46, 54)
    cv.thick(hx2 - s * 0.2, hy2 - s * 0.06, hx2 + s * 0.3, hy2 - s * 0.06, max(1, int(s * 0.05)), strap)
    cv.ellipse(hx2 + s * 0.08, hy2 - s * 0.02, s * 0.28, s * 0.22, frame)     # mask frame over the eye
    cv.ellipse(hx2 + s * 0.08, hy2 - s * 0.02, s * 0.2, s * 0.15, glass)      # glass
    cv.disc(hx2 + s * 0.18, hy2 - s * 0.12, max(1, s * 0.06), pack(255, 255, 255))  # glint


def draw_dog(cv, x, gy, s, phase, moving, t_now, underwater=False, surf=False, tilt=0.0, space=False):
    """A small trotting dog that tags along beside the hero (opt-in companion)."""
    body = (226, 188, 132)
    cM = pack(*body); cD = pack(*shade(body, 0.68)); cL = pack(*lerpc(body, (255, 255, 255), 0.3))
    bw, bh = s * 0.85, s * 0.4

    if space:                                                                 # the dog floats in its own helmet
        bob = math.sin(t_now * 1.3) * s * 0.12
        bx, by = x, gy - s * 1.7 - bob                                       # drift well up in the void
        fy = by + bh * 0.55 + s * 0.3                                        # paws paddle below the belly
        pad = t_now * 5
        for i, (lx, cc) in enumerate(((bw * 0.62, cM), (bw * 0.28, cM), (-bw * 0.25, cD), (-bw * 0.55, cD))):
            px = bx + lx + math.cos(pad + i * 1.4) * s * 0.18               # paws paddling slowly
            py = fy + math.sin(pad + i * 1.4) * s * 0.12
            cv.thick(bx + lx, by + bh * 0.25, px, py, max(1, int(s * 0.12)), cc)
        cv.disc(bx - bw * 0.08, by - bh * 1.0, max(1, s * 0.13), pack(214, 218, 226))   # life-support nub
        cv.ellipse(bx, by, bw, bh, cM)
        cv.ellipse(bx, by - bh * 0.3, bw * 0.8, bh * 0.55, cL)
        cv.thick(bx - bw * 0.85, by - bh * 0.15, bx - bw * 1.3, by - bh * 0.3 + math.sin(t_now * 3) * s * 0.2,
                 max(1, int(s * 0.11)), cM)                                  # tail drifting behind
        hx2, hy2 = bx + bw * 0.95, by - bh * 0.4
        dcx, dcy = hx2 + s * 0.14, hy2 - s * 0.02
        _helmet_dome(cv, dcx, dcy, s * 0.42)                                # dome over the whole muzzle
        cv.disc(hx2, hy2, s * 0.3, cM)
        cv.rect(hx2, hy2 - s * 0.04, hx2 + s * 0.4, hy2 + s * 0.13, cM)      # snout
        cv.disc(hx2 - s * 0.14, hy2 - s * 0.26, s * 0.13, cD)               # ear
        cv.disc(hx2 + s * 0.36, hy2 + s * 0.02, max(1, s * 0.06), pack(20, 20, 24))  # nose
        cv.disc(hx2 + s * 0.06, hy2 - s * 0.04, max(1, s * 0.05), pack(20, 20, 24))  # eye
        _helmet_shine(cv, dcx, dcy, s * 0.42, s)
        return

    if surf:                                                                  # the dog rides its own board
        _draw_surfboard(cv, x, gy, s * 1.2, lerpc(body, (255, 255, 255), 0.25), tilt)
        cv.shadow_ground(x, gy + 1, s * 0.95, max(1, s * 0.18))
        bob = math.sin(t_now * 2.2) * s * 0.05
        bx, by = x, gy - s * 0.5 + bob
        for lx in (-bw * 0.5, -bw * 0.18, bw * 0.2, bw * 0.5):                # four paws braced on the deck
            cv.thick(bx + lx, by + bh * 0.2, bx + lx, gy - s * 0.03, max(1, int(s * 0.12)), cD if lx < 0 else cM)
        cv.ellipse(bx, by, bw, bh, cM)
        cv.ellipse(bx, by - bh * 0.3, bw * 0.8, bh * 0.55, cL)
        ear = math.sin(t_now * 9) * s * 0.18                                  # ears + tail flapping in the wind
        cv.thick(bx - bw * 0.85, by - bh * 0.3, bx - bw * 1.2, by - s * 0.55 + math.sin(t_now * 12) * s * 0.3,
                 max(1, int(s * 0.11)), cM)                                   # tail up
        hx2, hy2 = bx + bw * 0.95, by - bh * 0.5
        cv.disc(hx2, hy2, s * 0.3, cM)
        cv.rect(hx2, hy2 - s * 0.04, hx2 + s * 0.4, hy2 + s * 0.13, cM)       # snout
        cv.disc(hx2 - s * 0.16, hy2 - s * 0.24 + ear, s * 0.13, cD)          # ear streaming back
        cv.thick(hx2 + s * 0.34, hy2 + s * 0.14, hx2 + s * 0.5, hy2 + s * 0.3, max(1, int(s * 0.07)),
                 pack(228, 116, 128))                                         # tongue out, having a blast
        cv.disc(hx2 + s * 0.36, hy2 + s * 0.02, max(1, s * 0.06), pack(20, 20, 24))  # nose
        cv.disc(hx2 + s * 0.06, hy2 - s * 0.04, max(1, s * 0.05), pack(20, 20, 24))  # eye
        return

    if underwater:                                                           # doggy-paddle: swims, doesn't walk
        bob = math.sin(t_now * 1.7) * s * 0.1
        bx, by = x, gy - s * 1.45 - bob                                      # float mid-water, well off the seabed
        fy = by + bh * 0.55 + s * 0.3                                        # paws paddle below the belly
        cv.shadow_ground(x, gy + 1, s * 0.8, max(1, s * 0.14))             # faint shadow on the seabed
        pad = t_now * 7
        for i, (lx, cc) in enumerate(((bw * 0.62, cM), (bw * 0.28, cM), (-bw * 0.25, cD), (-bw * 0.55, cD))):
            px = bx + lx + math.cos(pad + i * 1.4) * s * 0.16               # paws churning in circles
            py = fy + math.sin(pad + i * 1.4) * s * 0.1
            cv.thick(bx + lx, by + bh * 0.25, px, py, max(1, int(s * 0.12)), cc)
        cv.ellipse(bx, by, bw, bh, cM)
        cv.ellipse(bx, by - bh * 0.3, bw * 0.8, bh * 0.55, cL)
        cv.thick(bx - bw * 0.85, by - bh * 0.15, bx - bw * 1.3, by - bh * 0.3 + math.sin(t_now * 6) * s * 0.22,
                 max(1, int(s * 0.11)), cM)                                  # tail streaming behind
        hx2, hy2 = bx + bw * 0.95, by - bh * 0.4
        cv.disc(hx2, hy2, s * 0.3, cM)
        cv.rect(hx2, hy2 - s * 0.04, hx2 + s * 0.4, hy2 + s * 0.13, cM)      # snout
        cv.disc(hx2 - s * 0.14, hy2 - s * 0.26, s * 0.13, cD)               # ear
        _draw_dog_scuba(cv, bx, by, bw, bh, hx2, hy2, s)                     # tank + mask
        cv.disc(hx2 + s * 0.36, hy2 + s * 0.02, max(1, s * 0.06), pack(20, 20, 24))  # nose
        cv.disc(hx2 + s * 0.06, hy2 - s * 0.04, max(1, s * 0.05), pack(20, 20, 24))  # eye
        _bubbles(cv, hx2 + s * 0.42, hy2 - s * 0.3, s * 0.9, t_now, n=3)     # bubbles off the snout
        return

    bx, by = x, gy - s * 0.52
    cv.shadow_ground(x, gy + 1, s * 0.85, max(1, s * 0.2))
    sw = (s * 0.42) if moving else (s * 0.05)
    legs = ((-bw * 0.6, cD, 0.0), (bw * 0.5, cD, math.pi), (-bw * 0.45, cM, math.pi), (bw * 0.65, cM, 0.0))
    for lx, cc, off in legs:
        fx = bx + lx + math.sin(phase + off) * sw
        cv.thick(bx + lx, by + bh * 0.2, fx, gy, max(1, int(s * 0.13)), cc)
        cv.ellipse(fx + s * 0.03, gy - s * 0.015, s * 0.1, max(1, s * 0.05), cc)   # paw
    cv.disc(bx - bw * 0.52, by + bh * 0.05, bh * 0.78, cM)                     # haunch (rounds the rear)
    cv.ellipse(bx, by, bw, bh, cM)                                            # body
    cv.disc(bx + bw * 0.5, by - bh * 0.05, bh * 0.7, cM)                       # chest
    cv.ellipse(bx, by - bh * 0.3, bw * 0.8, bh * 0.55, cL)                     # back highlight
    wag = math.sin(t_now * (13 if moving else 5)) * s * 0.32
    cv.thick(bx - bw * 0.85, by - bh * 0.2, bx - bw * 1.25, by - s * 0.45 + wag, max(1, int(s * 0.11)), cM)
    cv.disc(bx - bw * 1.25, by - s * 0.45 + wag, max(1, s * 0.1), cL)          # fluffy tail tip
    hx2, hy2 = bx + bw * 0.95, by - bh * 0.45
    cv.disc(hx2 - s * 0.26, hy2 - s * 0.22, s * 0.12, cD)                      # far ear (behind, dim)
    cv.disc(hx2, hy2, s * 0.3, cM)                                            # head
    cv.rect(hx2, hy2 - s * 0.04, hx2 + s * 0.4, hy2 + s * 0.13, cM)            # snout
    cv.disc(hx2 + s * 0.4, hy2 + s * 0.045, s * 0.085, cM)                     # rounded muzzle tip
    cv.disc(hx2 - s * 0.12, hy2 - s * 0.26, s * 0.14, cM)                      # near ear (lit)
    cv.disc(hx2 + s * 0.36, hy2 + s * 0.02, max(1, s * 0.06), pack(20, 20, 24))  # nose
    cv.disc(hx2 + s * 0.06, hy2 - s * 0.04, max(1, s * 0.05), pack(20, 20, 24))  # eye
    cv.px(hx2 + s * 0.085, hy2 - s * 0.06, pack(245, 245, 250))                # eye glint
