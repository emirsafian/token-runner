# Contributing

Glad you're here. It's a small package and easy to get into. Adding a new world
or a little animal is genuinely a 10 minute job once you see how the pieces fit.

## The one rule

No dependencies. Standard library Python 3 only. If a change needs a `pip
install`, it doesn't fit here. Half the point is that you can drop the package
anywhere and it just runs.

## How it fits together

One package, one job per file. Open the file named after the thing you want to
change:

```
tokenrun/
  cli.py        args, the main loop, the TAB view toggle, --png/--once
  engine.py     reads the transcripts; the numbers behind everything
  dashboard.py  the speedometer view (TAB)
  render.py     colour math + ANSI (pack/shade/lerpc/grad)
  canvas.py     the half-block pixel canvas + PNG writer
  biomes.py     BIOMES, daylight, gaits          <- add a world
  sprites.py    the draw_* props + the SPR map    <- add a prop
  runner.py     the runner, the dog, the poses
  critters.py   ambient life (CRITTERS)
  scene.py      build_frame: assembles each frame
  records.py    personal best, streak, milestones
  hud.py        the game HUD + toasts
  demo.py       the scripted --demo run
```

Every frame is assembled in one place, `scene.build_frame`.

## Trying a change

You don't need a live Claude session to see your work. From the repo root:

- `python3 -m tokenrun --once` prints a single frame and exits.
- `python3 -m tokenrun --demo` plays a scripted run on fake data.
- `python3 -m tokenrun --png frame.png --rate 120 --biome OCEAN` renders one
  frame to a PNG, the fastest way to check pixel art. Add `--phase night` for the
  dark version. The biome name must match a `BIOMES` key exactly (uppercase).

Run `python3 -m tokenrun --help` for the rest of the flags.

## Add your own ...

### A biome (a new world)

1. Add an entry to `BIOMES` in `tokenrun/biomes.py`. Easiest is to copy an
   existing one and change the colours. Each biome has a sky gradient (`skyTop`,
   `skyHaze`), a ground gradient (`gFar`, `gNear`), a `sun` colour (also the
   moon), an `accent` (the signature colour props pull from), a `far` colour for
   distant shapes, and `kinds`, a tuple of prop names to scatter around.
2. Add the name to `BIOME_ORDER`. That's the order you travel through them, and
   each one lasts `BIOME_STEP` (40,000) tokens.
3. Optional: give it some ambient life in `tokenrun/critters.py` (below).
4. Look at it: `python3 -m tokenrun --png out.png --biome YOURNAME`.

### A prop (a tree, a building, anything roadside)

1. Write a function in `tokenrun/sprites.py`, same shape as the rest:

   ```python
   def draw_thing(cv, x, gy, s, b):
       # x, gy = where it sits on the ground; s = size; b = the biome dict
       cv.disc(x, gy - s, s * 0.6, pack(*b["accent"]))
   ```

   Draw with the canvas tools (`cv.px`, `cv.rect`, `cv.disc`, `cv.ellipse`,
   `cv.thick`) and pull colours from `b` so it matches the biome. Colours go
   through `pack(r, g, b)`. `shade(colour, f)` lightens or darkens and
   `lerpc(a, b, t)` blends two colours. Only hardcode a colour when it should not
   follow the biome.
2. Register it in `SPR`.
3. Put that name in some biome's `kinds`.
4. Check it with `--png`.

### A critter (the little ambient life)

In `tokenrun/critters.py`:

- To reuse a look that already exists, just point a biome at it:
  `CRITTERS["YOURBIOME"] = "crab"`.
- For a brand new one, add a branch in `_spawn_critter` (set its starting `x`/`y`
  and velocity `vx`/`vy`) and one in `_draw_critter` (draw it; `c["ph"]` is a
  random phase and `t` is time).

### A companion (the figure beside you)

Today it cycles none, ghost, dog, buddy. The drawing lives in
`tokenrun/scene.py` (search for `comp = getattr(cfg, "companion", None)` in
`build_frame`) and the cycle lives in `tokenrun/cli.py`:

1. Draw it, either a new function or by reusing `draw_runner` / `draw_dog` with a
   `color_override`.
2. Add it to the cycle list `order = [None, "ghost", "dog", "buddy"]` and to the
   two small dicts under it that set the popup text and colour.
3. Optional: add a `--cat` flag in `main()`, the same way `--dog` works.

### A scene that changes the character (swim, surf, climb, …)

The biggest jump: a scene where the hero **and** companions get a new pose, like
the underwater swim (`OCEAN`) or surfing (`SURF`). That spans ~6 files and the
tricky bit is wiring the new mode into all four figures (hero, buddy, ghost, dog)
plus gating the land-only cues. There's a step-by-step recipe (with the patterns,
the exact wiring sites, and the verification commands) in
`.claude/skills/add-scene/SKILL.md` — copy `_draw_dive` / `_draw_surf` as your
starting point.

## Style

Match the file you're editing. Keep things small and readable. If you're adding
to the game, a screenshot in the pull request helps a lot.

## Pull requests

Open one against `main`. Say what it does, and for anything visual drop in a
before/after image. That's it.
