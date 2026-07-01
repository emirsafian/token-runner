"""The worlds you run through: biome palettes, daylight phases, gait thresholds.

Add a biome by copying a BIOMES entry, recolouring it, and adding its name to
BIOME_ORDER. The `kinds` tuple names props from tokenrun.sprites (the SPR keys).
"""
import time


BIOMES = {
    "JUNGLE": dict(skyTop=(40, 96, 120), skyHaze=(150, 200, 170), gFar=(74, 120, 78),
                   gNear=(40, 80, 48), sun=(255, 244, 210), accent=(94, 210, 160),
                   far=(34, 70, 56), kinds=("tree", "tree", "tree", "rock")),
    "DESERT": dict(skyTop=(120, 120, 150), skyHaze=(245, 210, 150), gFar=(214, 180, 120),
                   gNear=(160, 118, 70), sun=(255, 236, 180), accent=(240, 205, 120),
                   far=(150, 116, 80), kinds=("cactus", "cactus", "rock", "cactus")),
    "BEACH": dict(skyTop=(78, 158, 196), skyHaze=(206, 230, 228), gFar=(228, 208, 152),
                  gNear=(202, 176, 116), sun=(255, 250, 226), accent=(86, 200, 206),
                  far=(118, 182, 192), kinds=("palm", "palm", "rock", "palm")),
    "SURF": dict(skyTop=(64, 150, 206), skyHaze=(190, 226, 238), gFar=(44, 126, 172),
                 gNear=(18, 78, 128), sun=(255, 250, 226), accent=(196, 240, 246),
                 far=(96, 150, 172), kinds=("buoy", "sailboat", "buoy", "sailboat")),
    "OCEAN": dict(skyTop=(18, 70, 112), skyHaze=(58, 150, 172), gFar=(30, 92, 122),
                  gNear=(16, 54, 84), sun=(186, 236, 240), accent=(255, 148, 162),
                  far=(22, 80, 110), kinds=("coral", "seaweed", "coral", "rock")),
    "SNOW": dict(skyTop=(122, 152, 188), skyHaze=(228, 234, 242), gFar=(228, 234, 244),
                 gNear=(182, 198, 218), sun=(255, 250, 242), accent=(150, 202, 236),
                 far=(170, 186, 208), kinds=("pine", "pine", "snowman", "rock")),
    "AMAZON": dict(skyTop=(36, 90, 96), skyHaze=(172, 206, 150), gFar=(46, 98, 56),
                   gNear=(24, 60, 36), sun=(240, 246, 200), accent=(70, 202, 92),
                   far=(22, 64, 46), kinds=("bigtree", "vine", "tree", "bigtree")),
    "VOLCANO": dict(skyTop=(58, 28, 40), skyHaze=(152, 78, 58), gFar=(72, 52, 52),
                    gNear=(40, 28, 28), sun=(255, 150, 70), accent=(255, 110, 40),
                    far=(54, 36, 40), kinds=("volcano", "lavarock", "rock", "volcano")),
    "CITY": dict(skyTop=(24, 34, 60), skyHaze=(120, 140, 180), gFar=(70, 80, 100),
                 gNear=(36, 42, 58), sun=(255, 220, 170), accent=(130, 180, 255),
                 far=(44, 56, 86), kinds=("building", "building", "building", "tree")),
    "NEON": dict(skyTop=(20, 12, 40), skyHaze=(72, 40, 110), gFar=(40, 30, 64),
                 gNear=(22, 16, 38), sun=(255, 120, 210), accent=(255, 60, 180),
                 far=(36, 24, 60), kinds=("neon", "building", "neon", "building")),
    "COSMOS": dict(skyTop=(8, 6, 22), skyHaze=(60, 40, 100), gFar=(48, 40, 86),
                   gNear=(20, 16, 40), sun=(210, 220, 255), accent=(180, 158, 240),
                   far=(40, 32, 72), kinds=("rock", "crystal", "rock", "crystal")),
    "SPACE": dict(skyTop=(6, 7, 18), skyHaze=(26, 22, 54), gFar=(18, 16, 40),
                  gNear=(8, 8, 22), sun=(214, 224, 255), accent=(150, 200, 255),
                  far=(30, 26, 60), kinds=("asteroid", "satellite", "asteroid", "asteroid")),
}
# the journey: land → beach → surf → dive → cold → deep jungle → fire → city → cosmos → the void
BIOME_ORDER = ["JUNGLE", "DESERT", "BEACH", "SURF", "OCEAN", "SNOW", "AMAZON", "VOLCANO", "CITY", "NEON", "COSMOS", "SPACE"]
BIOME_STEP = 40_000

# submerged scenes: the hero + companions gear up in scuba kit and bubbles rise.
UNDERWATER = frozenset({"OCEAN"})
# surface scenes: the hero + companions ride a rolling wave on surfboards.
SURF = frozenset({"SURF"})
# zero-g scenes: the hero + companions float in spacesuits, thrusters puffing.
SPACEWALK = frozenset({"SPACE"})

# time-of-day from the wall clock: (brightness, tint rgb, tint amount, is_night)
DAYLIGHT = {
    "day":   (1.00, (255, 255, 255), 0.00, False),
    "dawn":  (0.86, (255, 168, 120), 0.22, False),
    "dusk":  (0.74, (255, 116, 84), 0.30, False),
    "night": (0.44, (38, 44, 88), 0.42, True),
}

# parallax layers: (yfrac horizon→ground, sizefrac of H, speed factor, count)
LAYERS = [(0.10, 0.055, 0.22, 4), (0.50, 0.11, 0.52, 3), (1.0, 0.17, 1.0, 3)]


def biome_of(dist):
    return BIOME_ORDER[int(dist // BIOME_STEP) % len(BIOME_ORDER)]


def day_phase(now):
    """Map the local wall-clock hour to a daylight phase."""
    lt = time.localtime(now)
    h = lt.tm_hour + lt.tm_min / 60.0
    if 5.0 <= h < 7.5:
        return "dawn"
    if 7.5 <= h < 17.0:
        return "day"
    if 17.0 <= h < 20.0:
        return "dusk"
    return "night"


def gait_of(rate, thinking):
    if thinking and rate < 8:
        return "thinking"
    if rate < 1:
        return "resting"
    if rate < 22:
        return "walk"
    if rate < 70:
        return "jog"
    if rate < 130:
        return "run"
    return "BLAZE"
