"""Command-line entry: arg parsing, the main loop, the TAB view toggle, and the
--png / --once self-check paths.
"""
import os
import sys
import time
import select
import argparse

from .render import ESC, ALT_ON, ALT_OFF, get_size
from .engine import Engine, WEEK, DEFAULT_DIR
from .canvas import Canvas, write_png
from .scene import Scene, build_frame
from .records import Records
from .hud import game_hud, banner_line, dash_footer, draw_usage_gauges, gauge_overlay, MUTE
from .fmt import human
from .usage import LiveUsage
from .dashboard import build as dashboard_build
from .demo import DemoEngine, demo_director
from .sound import Sound
from .biomes import BIOMES, BIOME_ORDER, DAYLIGHT, day_phase, gait_of, biome_of


class Cfg:
    pass


def _live_gauge(win, now):
    """Turn a live usage window {pct, resets_at} into a (frac, reset_s, active,
    label) gauge tuple, or None so the caller falls back to the local estimate."""
    if not win or win.get("pct") is None:
        return None
    pct = win["pct"]
    ra = win.get("resets_at")
    reset = max(0.0, ra - now) if ra else 0.0
    return pct / 100.0, reset, ra is not None, f"{pct:.0f}%"


def run(cfg):
    demo = getattr(cfg, "demo", False)
    eng = DemoEngine() if demo else Engine(cfg.root)
    eng.poll()
    scene = Scene()
    snd = Sound(cfg.sound)
    records = Records(path=os.devnull) if demo else Records()
    cfg.biome = "JUNGLE"
    cfg.max_width = 0          # for the embedded dashboard
    cfg.usage_mode = getattr(cfg, "usage_mode", "live")   # live → estimate → off (u toggles)

    live_usage = None          # created lazily the first time we're in "live" mode (reads the token then)

    kb, fd = None, None
    if sys.stdin.isatty():
        try:
            import termios, tty
            fd = sys.stdin.fileno()
            kb = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            kb = None
    alt = cfg.alt and sys.stdout.isatty()
    if alt:
        sys.stdout.write(ALT_ON + ESC + "[?7l" + ESC + "[2J")  # ?7l = disable line-wrap (no scroll garble)
        sys.stdout.flush()

    view = "run"               # "run" = the game · "dash" = the dashboard
    frame_n = 0
    last_live_note = 0.0
    live_ok = False
    last_poll = 0.0
    last_step = 0.0
    last_save = time.time()
    frame_dt = 1.0 / cfg.fps
    now = time.time()
    demo_t0 = now
    total7d = eng.window(now, WEEK)[3]
    sess_ref = eng.block_peak(now)
    week_ref = 7 * eng.day_peak(now)
    if not demo:
        records.refresh(eng, now)
    try:
        while True:
            now = time.time()
            if now - last_poll >= 1.0:
                eng.poll(); last_poll = now
                total7d = eng.window(now, WEEK)[3]
                sess_ref = eng.block_peak(now)
                week_ref = 7 * eng.day_peak(now)
                if cfg.usage_mode == "live":
                    if live_usage is None:                        # first entry into live mode → read token, start fetching
                        live_usage = LiveUsage()
                        if not live_usage.available:
                            scene.banner("LIVE USAGE  no token · using estimate (u to switch)", (235, 170, 90), now, dur=4.0)
                    live_usage.poll(now)
                    lsnap = live_usage.snapshot()
                    if lsnap is not None and any(lsnap.values()):
                        if not live_ok:
                            scene.banner("LIVE USAGE  connected · showing real limits", (120, 200, 140), now, dur=3.0)
                            live_ok = True
                    elif now - last_live_note > 15:                # surface why it fell back (not while still loading)
                        if live_usage.error:
                            scene.banner(f"LIVE USAGE  {live_usage.error} · using estimate", (235, 170, 90), now, dur=4.0)
                            last_live_note = now
                        elif lsnap is not None:                   # got a response, but no usable windows in it
                            scene.banner("LIVE USAGE  no limit data in response · using estimate", (235, 170, 90), now, dur=4.0)
                            last_live_note = now
                if not demo:
                    bumped = records.refresh(eng, now)
                    if bumped and bumped > 1:
                        scene.banner(f"DAY {bumped} STREAK  keep it going", (255, 184, 92), now, dur=3.2)
                        if cfg.sound:
                            snd.play("pb", gap=2, vol=0.4)
                    if now - last_save > 20:
                        records.save(); last_save = now
            cols, rows = get_size()
            if demo:
                view = demo_director(eng, cfg, records, now, demo_t0)

            overlay = ""
            if view == "dash":
                cfg.width = cols
                cfg.interval = 1.0
                cfg.footer_hint = dash_footer(cols)
                lines = dashboard_build(eng, cfg, now, frame_n)
                slack = rows - len(lines)
                if slack > 3:                       # center vertically, like the dashboard
                    lines = [""] * (slack // 2) + lines
                step = 0.25
            else:
                W = max(40, min((cfg.force_width or cols) - 1, 240))  # -1: never touch last column
                ch_rows = max(8, rows - 2)
                cv = Canvas(W, ch_rows * 2, xs=2 if getattr(cfg, "hi", False) else 1)
                rate, thinking, dist, blk = build_frame(cv, eng, scene, cfg, now, records)
                # usage gauges (u cycles live → estimate → off): in live mode prefer the REAL
                # limits, else the local estimate; alpha-blended in so the scene shows through
                gmeta = None
                if cfg.usage_mode != "off":
                    snap = live_usage.snapshot() if (cfg.usage_mode == "live" and live_usage) else None
                    sess_g = (_live_gauge(snap and snap["five_hour"], now)
                              or (blk[3] / max(sess_ref, blk[3], 1.0), blk[4], blk[5], human(blk[3])))
                    week_g = (_live_gauge(snap and snap["seven_day"], now)
                              or (total7d / max(week_ref, total7d, 1.0), eng.week_reset_in(now),
                                  total7d > 0, human(total7d)))
                    gmeta = draw_usage_gauges(cv, sess_g, week_g)
                live = (now - eng.last_mtime) < 25
                if cfg.sound:
                    if gait_of(rate, thinking) in ("walk", "jog", "run") and now - last_step > max(0.12, 0.5 - rate / 400):
                        snd.play("step", vol=0.22); last_step = now
                    if rate >= 130:
                        snd.play("blaze", gap=1.4, vol=0.3)
                    if "biome" in scene.events:
                        snd.play("biome", vol=0.4)
                    if "pb" in scene.events:
                        snd.play("pb", gap=2, vol=0.45)
                    if "milestone" in scene.events:
                        snd.play("milestone", gap=2, vol=0.45)
                rows_img = cv.render_rows_quad() if getattr(cfg, "hi", False) else cv.render_rows()
                scene.banners = [bn for bn in scene.banners if bn["until"] > now]
                for k, bn in enumerate(scene.banners[-2:]):       # toast band(s) near the top
                    if 1 + k < len(rows_img):
                        rows_img[1 + k] = banner_line(W, bn["text"], bn["col"])
                lines = game_hud(W, rate, thinking, live, dist, blk, total7d, cfg.biome,
                                 cfg.redline, frame_n, streak=records.streak, pb=records.pb_rate,
                                 ghost_gap=records.ghost_gap, has_ghost=records.has_yesterday) + rows_img
                step = frame_dt

                # gauge labels ride on top of the (already blended) bars, on the scene's own colour
                overlay = gauge_overlay(cv, gmeta, len(lines) - len(rows_img))

            if len(lines) > rows:
                lines = lines[:rows]
            buf = ESC + "[H" + "\r\n".join(l + ESC + "[K" for l in lines) + ESC + "[J" + overlay
            sys.stdout.write(buf); sys.stdout.flush()
            frame_n += 1

            deadline = time.time() + step
            while True:
                rem = deadline - time.time()
                if rem <= 0:
                    break
                if fd is not None:
                    r, _, _ = select.select([sys.stdin], [], [], rem)
                    if r:
                        ch = sys.stdin.read(1)
                        if ch in ("q", "Q", "\x03"):
                            return
                        if ch in ("\t", "v", "V"):       # toggle game ⇄ dashboard
                            view = "dash" if view == "run" else "run"
                            scene.t = time.time()        # avoid a dt jump when we return
                            break
                        if ch in ("c", "C"):             # cycle companion: none → ghost → dog → buddy
                            order = [None, "ghost", "dog", "buddy"]
                            cur = getattr(cfg, "companion", None)
                            cfg.companion = order[(order.index(cur) + 1) % len(order)] if cur in order else "ghost"
                            msg = {None: "running solo", "ghost": "RACING YESTERDAY'S GHOST",
                                   "dog": "A DOG JOINS THE RUN", "buddy": "A FRIEND JOINS THE RUN"}[cfg.companion]
                            bc = {None: MUTE, "ghost": (170, 178, 198), "dog": (226, 188, 132),
                                  "buddy": (120, 170, 235)}[cfg.companion]
                            scene.banner(msg, bc, time.time(), dur=1.8)
                            break
                        if ch in ("h", "H"):             # toggle hi-res quadrant rendering
                            cfg.hi = not getattr(cfg, "hi", False)
                            scene.banner("HI-RES  " + ("ON" if cfg.hi else "OFF"),
                                         (150, 210, 255), time.time(), dur=1.6)
                            break
                        if ch in ("u", "U"):             # cycle the usage gauges: live → estimate → off
                            order = ["live", "estimate", "off"]
                            cfg.usage_mode = order[(order.index(cfg.usage_mode) + 1) % len(order)]
                            if demo and cfg.usage_mode == "live":   # demo never touches the network
                                cfg.usage_mode = "estimate"
                            live_ok = False                          # re-announce on the next successful live fetch
                            label = {"live": "USAGE  live limits", "estimate": "USAGE  local estimate",
                                     "off": "USAGE  hidden"}[cfg.usage_mode]
                            scene.banner(label, (150, 210, 255), time.time(), dur=1.6)
                            break
                        if ch in ("b", "B"):             # cycle the scene: auto → each biome → auto
                            order = [None] + BIOME_ORDER
                            cur = getattr(cfg, "force_biome", None)
                            i = order.index(cur) if cur in order else 0
                            cfg.force_biome = order[(i + 1) % len(order)]
                            target = cfg.force_biome or biome_of(eng.block(time.time())[0])
                            scene.cur_biome = cfg.biome = target   # adopt now → no duplicate "ENTERING" toast
                            label = ("SCENE  " + target) if cfg.force_biome else ("SCENE  AUTO · " + target)
                            scene.banner(label, BIOMES[target]["accent"], time.time(), dur=2.2)
                            break
                else:
                    time.sleep(min(rem, 0.05))
    except KeyboardInterrupt:
        return
    finally:
        if not demo:
            records.save(force=True)
        if alt:
            sys.stdout.write(ESC + "[?7h" + ALT_OFF); sys.stdout.flush()  # restore line-wrap
        if kb is not None:
            try:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, kb)
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser(description="Claude Code token speed, as a half-block runner")
    ap.add_argument("--dir", default=os.environ.get("TOKENRUN_DIR", DEFAULT_DIR))
    ap.add_argument("--tau", type=float, default=float(os.environ.get("TOKENRUN_TAU", "90")))
    ap.add_argument("--redline", type=float, default=float(os.environ.get("TOKENRUN_REDLINE", "160")))
    ap.add_argument("--fps", type=float, default=14.0)
    ap.add_argument("--sound", action="store_true", help="footsteps + cues via macOS afplay")
    ap.add_argument("--dog", action="store_true", help="start with the dog companion (cycle in-app with c)")
    ap.add_argument("--buddy", action="store_true", help="start with the runner-buddy companion (cycle with c)")
    ap.add_argument("--no-daylight", action="store_true", help="disable time-of-day tinting")
    ap.add_argument("--live", action="store_true", help="(default) real Claude limit %% in the gauges")
    ap.add_argument("--no-live", action="store_true",
                    help="fully offline: gauges use a local estimate, no call to Anthropic. "
                         "Env: TOKENRUN_LIVE=0. (In-app, u cycles live → estimate → off.)")
    ap.add_argument("--no-usage", action="store_true", help="start with the usage gauges hidden (toggle with u)")
    ap.add_argument("--usage-check", action="store_true",
                    help="diagnose live usage: print whether a token was found and what the usage "
                         "API returns, then exit (prints no secrets)")
    ap.add_argument("--hi", action="store_true",
                    help="hi-res quadrant blocks: 2x horizontal detail (toggle in-app with h)")
    ap.add_argument("--demo", action="store_true",
                    help="scripted fake run that shows every feature (for recording a demo video)")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-alt", action="store_true")
    ap.add_argument("--width", type=int, default=0)
    ap.add_argument("--png", default=None, help="render one frame to a PNG and exit (self-verify)")
    ap.add_argument("--scale", type=int, default=5, help="PNG pixel scale")
    ap.add_argument("--rate", type=float, default=None, help="force tok/s for --png")
    ap.add_argument("--biome", default=None, help="force biome for --png")
    ap.add_argument("--phase", default=None, help="force daylight phase for --png (day/dawn/dusk/night)")
    ap.add_argument("--frames", type=int, default=24, help="advance N frames before --png")
    ap.add_argument("--think", action="store_true", help="force thinking pose for --png")
    ap.add_argument("--idle", type=float, default=None, help="force N seconds idle (sit pose) for --png")
    ap.add_argument("--ghost", type=float, default=None, help="fake yesterday token gap for --png ghost test")
    a = ap.parse_args()

    cfg = Cfg()
    cfg.root = os.path.expanduser(a.dir)
    cfg.tau = max(5.0, a.tau)
    cfg.redline = max(10.0, a.redline)
    cfg.fps = max(2.0, min(30.0, a.fps))
    cfg.sound = a.sound
    cfg.alt = not a.no_alt
    cfg.force_width = max(0, a.width)
    cfg.biome = "JUNGLE"
    cfg.force_biome = None
    cfg.companion = "buddy" if a.buddy else ("dog" if a.dog else None)
    cfg.daylight = not a.no_daylight
    cfg.force_phase = a.phase if a.phase in DAYLIGHT else None
    cfg.demo = a.demo
    cfg.hi = a.hi
    # usage gauges: live (real limits) by default; u cycles live → estimate → off in-app
    env_off = os.environ.get("TOKENRUN_LIVE", "").lower() in ("0", "false", "no", "off")
    if a.no_usage:
        cfg.usage_mode = "off"
    elif a.no_live or env_off:
        cfg.usage_mode = "estimate"
    else:
        cfg.usage_mode = "live"
    if a.demo and cfg.usage_mode == "live":          # demo never touches the network
        cfg.usage_mode = "estimate"

    if a.usage_check:
        from .usage import diagnose
        for line in diagnose():
            print(line)
        return

    if a.png:
        cfg.force_biome = a.biome if a.biome in BIOMES else None
        cfg.biome = cfg.force_biome or "JUNGLE"
        eng = Engine(cfg.root); eng.poll()
        if a.idle is not None:
            eng.ewma_rate = lambda now, tau: 0.0
            eng.in_flight = lambda now: False
        elif a.rate is not None:
            eng.ewma_rate = lambda now, tau: float(a.rate)
            eng.in_flight = lambda now: bool(a.think)
        elif a.think:
            eng.in_flight = lambda now: True
        rec = None
        if a.ghost is not None:
            rec = Records(path=os.devnull)
            rec.has_yesterday = True
            rec.ghost_gap = float(a.ghost)
            rec.pb_rate = (a.rate or 100.0) * 1.25
            cfg.companion = "ghost"               # the ghost is now a companion-cycle option
        cols, rows = get_size()
        W = min(cfg.force_width or cols, 240)
        ch = max(8, rows - 2)
        t = time.time()
        sc = Scene()
        if a.idle is not None:
            sc.idle_since = t - a.idle           # pre-age the idle timer to show sit/Zzz
        cv = Canvas(W, ch * 2)
        for _ in range(max(1, a.frames)):
            cv = Canvas(W, ch * 2)
            sc.t = t - 1.0 / cfg.fps
            t += 1.0 / cfg.fps
            build_frame(cv, eng, sc, cfg, t, rec)
        write_png(a.png, cv.w, cv.h, cv.buf, max(1, a.scale))
        print(f"wrote {a.png}  ({cv.w * a.scale}x{cv.h * a.scale}px, biome={cfg.biome}, "
              f"phase={cfg.force_phase or day_phase(t)})")
        return

    if a.once:
        eng = Engine(cfg.root); eng.poll()
        cols, rows = get_size()
        W = min(cfg.force_width or cols, 240)
        cv = Canvas(W, max(8, rows - 2) * 2, xs=2 if a.hi else 1)
        sc = Scene(); sc.t = time.time() - 0.1
        build_frame(cv, eng, sc, cfg, time.time())
        for l in (cv.render_rows_quad() if a.hi else cv.render_rows()):
            sys.stdout.write(l + "\n")
        return

    if not a.demo and not os.path.isdir(cfg.root):
        sys.stderr.write(f"tokenrun: no Claude data at {cfg.root}\n")
        sys.exit(1)

    run(cfg)
