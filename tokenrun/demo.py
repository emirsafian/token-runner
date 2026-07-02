"""The scripted --demo run: a fake engine and a director that parade every
feature on a loop, for recording a demo. Reads and writes no real data.
"""
import math
from .render import clampi


class DemoEngine:
    """A scripted stand-in for the Engine, same interface, but every value is
    driven by demo_director() so you can screen-record an appealing run with no
    real data (and nothing is written to your records)."""

    def __init__(self):
        self.msgs = []
        self.last_mtime = 0.0
        self.rate = 0.0
        self.thinking = False
        self.dist = 0.0
        self.reset = 7200.0
        self.wreset = 400000.0

    def poll(self):
        pass

    def ewma_rate(self, now, tau):
        return self.rate

    def in_flight(self, now):
        return self.thinking

    def block(self, now):
        o = self.dist
        return o, o * 0.18, o * 44.0, o * 45.2, self.reset, True

    def window(self, now, span):
        return self.dist * 7, self.dist * 1.3, self.dist * 320, self.dist * 1850

    def week_reset_in(self, now):
        return self.wreset

    def block_peak(self, now):
        return 20_000_000.0        # fixed cap so the demo session gauge fills progressively

    def day_peak(self, now):
        return 130_000_000.0       # week_ref = 7x this; demo week gauge stays partial

    def buckets(self, now, span, n):
        return [max(0.0, 55 + 55 * math.sin(i * 0.27) + 26 * math.sin(i * 0.09 + 1)) for i in range(max(0, n))]


def demo_director(eng, cfg, records, now, t0):
    """Drive the fake run through every feature on a ~74s loop; returns the view."""
    LOOP = 74.0
    e = (now - t0) % LOOP

    def ramp(a, b, t1, t2):
        return a + (b - a) * clampi((e - t1) / (t2 - t1), 0.0, 1.0)

    if e < 3:      rate, think = 0.0, False                     # rest, standing
    elif e < 8:    rate, think = ramp(0, 18, 3, 8), False       # walk
    elif e < 14:   rate, think = 52.0, False                    # jog
    elif e < 22:   rate, think = ramp(72, 108, 14, 22), False   # run
    elif e < 30:   rate, think = 152.0, False                   # BLAZE
    elif e < 36:   rate, think = 0.0, True                      # thinking pause (☕)
    elif e < 45:   rate, think = 96.0, False                    # run
    elif e < 50:   rate, think = 40.0, False                    # jog
    elif e < 64:   rate, think = 0.0, False                     # idle → sits down (Zzz late)
    elif e < 70:   rate, think = 100.0, False                   # space cruise (zero-g float)
    else:          rate, think = ramp(0, 28, 70, 74), False     # walk → loops

    eng.rate = rate
    eng.thinking = think
    eng.last_mtime = now
    eng.dist = 4000 + e * 5200                                  # biomes + milestones roll by
    eng.reset = max(120.0, 8000.0 - e * 80.0)
    eng.wreset = max(1800.0, 200000.0 - e * 2700.0)

    if e < 22:         cfg.companion = "ghost"                  # showcase each companion in turn
    elif 34 <= e < 44: cfg.companion = "dog"
    elif 44 <= e < 50: cfg.companion = "buddy"
    elif 64 <= e < 70: cfg.companion = "dog"                    # a dog floats through space
    else:              cfg.companion = None
    cfg.force_biome = ("SURF" if 30 <= e < 44 else "OCEAN" if 44 <= e < 56  # surf, dive, then out to space
                       else "SPACE" if 64 <= e < 70 else None)
    cfg.force_phase = ("day" if e < 18 else "dusk" if e < 36 else "night" if e < 56
                       else "dawn" if e < 64 else "night")

    records.has_yesterday = True
    records.streak = 12
    records.longest = 30
    records.ghost_gap = 18000 + e * 600
    if e < getattr(cfg, "_demo_e", LOOP):                       # looped → re-arm the PB toast
        records.pb_rate = 138.0
        records._last_pb = 0.0
    cfg._demo_e = e
    return "dash" if 58.0 <= e < 63.0 else "run"               # a quick dashboard peek
