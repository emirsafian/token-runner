"""The hero runner and the dog companion: 2-bone IK limbs, the gait and lean,
and the idle sit-down and coffee poses.
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


def draw_runner(cv, x, gy, s, phase, rate, thinking, redline, t_now,
                idle_dur=0.0, think_dur=0.0, color_override=None, ghost=False):
    moving = rate > 0.6 and not (thinking and rate < 8)
    col = color_override or grad(speedT(rate, redline))
    cM = pack(*col); cD = pack(*shade(col, 0.6)); cL = pack(*lerpc(col, (255, 255, 255), 0.4))
    cF = pack(*shade(col, 0.48))                    # far-side limbs, dimmer for depth

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

    def arm(p, cu, cf, w):
        ahx = sx + math.sin(p) * stride * 0.8
        ahy = sy + s * 0.8
        ex, ey = _ik(sx, sy, ahx, ahy, armL, False)  # elbow back
        cv.thick(sx, sy, ex, ey, w, cu)
        cv.thick(ex, ey, ahx, ahy, max(1, w - 1), cf)

    if ghost:
        cv.shadow_ground(x, gy + 1, s * 0.7, max(1, s * 0.16))
    else:
        cv.shadow_ground(x, gy + 1, s * 1.0, max(1, s * 0.26))
    leg(phase + math.pi, cF, cF, max(1, th - 1))     # far leg (behind), arm opposite phase
    arm(phase, cF, cF, max(1, th - 1))
    cv.thick(hx, hy, sx, sy, th + 1, cM)             # torso
    cv.thick(hx + 1, hy - 1, sx, sy, max(1, th - 1), cL)
    leg(phase, cD, cM, th)                            # near leg (front)
    arm(phase + math.pi, cD, cM, th)
    hr = s * 0.32                                     # head, ahead of shoulders (faces right)
    hcx = sx + math.sin(lean) * hr * 0.8
    hcy = sy - math.cos(lean) * hr * 1.05
    cv.disc(hcx, hcy, hr, cM)
    cv.disc(hcx + hr * 0.35, hcy - hr * 0.1, hr * 0.5, cL)

    if thinking and not ghost:
        if think_dur >= 8.0:                         # long think → coffee break
            _draw_coffee(cv, hcx + s * 0.7, hcy - hr * 1.7, s)
        else:
            n = (int(t_now * 3) % 3) + 1
            for i in range(n):
                cv.disc(hcx + s * 0.55 + i * s * 0.3, hcy - hr * 1.7 - i * s * 0.2, 1 + i * 0.8, pack(150, 140, 235))


# ----------------------------------------------------------------------------- companion dog
def draw_dog(cv, x, gy, s, phase, moving, t_now):
    """A small trotting dog that tags along beside the hero (opt-in companion)."""
    body = (226, 188, 132)
    cM = pack(*body); cD = pack(*shade(body, 0.68)); cL = pack(*lerpc(body, (255, 255, 255), 0.3))
    bw, bh = s * 0.85, s * 0.4
    bx, by = x, gy - s * 0.52
    cv.shadow_ground(x, gy + 1, s * 0.85, max(1, s * 0.2))
    sw = (s * 0.42) if moving else (s * 0.05)
    legs = ((-bw * 0.6, cD, 0.0), (bw * 0.5, cD, math.pi), (-bw * 0.45, cM, math.pi), (bw * 0.65, cM, 0.0))
    for lx, cc, off in legs:
        fx = bx + lx + math.sin(phase + off) * sw
        cv.thick(bx + lx, by + bh * 0.2, fx, gy, max(1, int(s * 0.13)), cc)
    cv.ellipse(bx, by, bw, bh, cM)
    cv.ellipse(bx, by - bh * 0.3, bw * 0.8, bh * 0.55, cL)
    wag = math.sin(t_now * (13 if moving else 5)) * s * 0.32
    cv.thick(bx - bw * 0.85, by - bh * 0.2, bx - bw * 1.25, by - s * 0.45 + wag, max(1, int(s * 0.11)), cM)
    hx2, hy2 = bx + bw * 0.95, by - bh * 0.45
    cv.disc(hx2, hy2, s * 0.3, cM)
    cv.rect(hx2, hy2 - s * 0.04, hx2 + s * 0.4, hy2 + s * 0.13, cM)            # snout
    cv.disc(hx2 - s * 0.14, hy2 - s * 0.26, s * 0.13, cD)                      # ear
    cv.disc(hx2 + s * 0.36, hy2 + s * 0.02, max(1, s * 0.06), pack(20, 20, 24))  # nose
    cv.disc(hx2 + s * 0.06, hy2 - s * 0.04, max(1, s * 0.05), pack(20, 20, 24))  # eye
