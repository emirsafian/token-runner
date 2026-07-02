# Token Runner 🏃

**Token Runner** quietly turns your coding into a game. The tokens you burn drive
a little side-scrolling runner on a spare pane: a low-key visual nudge that keeps
you in flow. Cover more ground, beat your own record, keep pushing.

It reads the logs your coding tool already writes locally, so there's nothing to
set up. Zero dependencies, just Python 3. The only thing it ever sends anywhere
is a check of your own Claude usage limits for the two side gauges — turn that
off with one keystroke (`u`) or `--no-live` and it's fully offline.

![tokenrun in motion](docs/tokenrun.gif)

<!-- Record it with `tokenrun --demo`, save the clip as docs/tokenrun.gif, and it shows up here. -->

## Supported tools

The name is generic on purpose: today it reads one tool, with more planned.

| Tool | Status |
|---|---|
| **Claude Code** | ✅ Supported |
| Cursor, Copilot, Codex, Gemini CLI, Aider, … | Not yet, PRs welcome |

Only the engine is tool-specific, so adding one is a small, contained change.
Want yours? [Open an issue](https://github.com/emirsafian/token-runner/issues)
or see [CONTRIBUTING.md](CONTRIBUTING.md).

## Install

Pick whichever fits. Each one gives you a `tokenrun` command.

**Homebrew:**

```sh
brew install emirsafian/tap/tokenrun
```

**One line, no git, no pip:**

```sh
curl -fsSL https://raw.githubusercontent.com/emirsafian/token-runner/main/install.sh | sh
```

That drops `tokenrun` into `~/.local/bin`. If piping to `sh` makes you nervous,
open `install.sh` first and read it. It's short.

**pipx (or pip):**

```sh
pipx install git+https://github.com/emirsafian/token-runner
```

**From source (best if you want to hack on it):**

```sh
git clone https://github.com/emirsafian/token-runner
cd token-runner
python3 -m tokenrun
```

The only thing you need is Python 3, which Macs and most Linux boxes already have.

## Run it

```sh
tokenrun
```

Controls: `q` or Ctrl-C quits, `TAB` flips between the runner and the dashboard,
`c` cycles your companion, `b` rotates the scene — `AUTO` (the biome follows
your token distance) then each world in turn (jungle, desert, beach, surf, ocean,
snow, …), wrapping back to `AUTO` — and `u` cycles the usage gauges (real limits →
local estimate → off). Leave it open on a spare pane and glance at it while you
work. It fills your terminal and reflows when you resize.

## The runner

Your live token speed drives a third-person runner, drawn in truecolor half
blocks (`▀` is two stacked pixels per cell, the
[chafa](https://github.com/hpjansson/chafa) trick), so it's real pixel art at
about 4 ms a frame.

- tok/s moves the runner: rest, walk, jog, run, then a flat out BLAZE where the
  screen edges glow warm.
- thinking makes him stop and ponder, with a coffee on a long one. Go idle and he
  sits down on a stool, then nods off.
- the tokens you generate become distance, rolling you through 12 biomes (jungle,
  desert, beach, surf, ocean, snow, amazon, volcano, city, neon, cosmos, space).
- the surf break drops the runner onto a surfboard, carving a rolling wave with a
  foaming crest and a curling barrel — buoys and sailboats bob past, dolphins
  leap, and your companion rides its own board alongside (the dog, tongue out).
- the ocean is fully submerged: the runner stops walking and **swims like a diver**
  — horizontal, finning with a flutter kick, mask and air tank on, bubbles
  trailing up through slanting light shafts. Your companion swims too (the dog
  doggy-paddles in its own mask and tank).
- past the cosmos you drift out into **open space**: gravity cuts out and the
  runner — and companions — **float in spacesuits and bubble helmets**, thrusters
  puffing as you speed up, past a slow-turning planet, drifting asteroids and
  satellites, and a streaking comet.
- the sky matches your actual clock: dawn, day, dusk, night, with a sun, a moon,
  and stars. Each biome has its own critters, and fireflies come out at night.
- want company? Press `c` to cycle through none, a ghost of yesterday, a dog, or a
  friend who keeps pace. Or start with `--dog` or `--buddy`.

### Beat your own record 🏅

The point is to make your own output a little more fun to push. Everything comes
from the same local logs and is saved in `~/.tokenrun.json`:

- **Ghost of yesterday:** the `vs Y'DAY` number compares today's tokens to this
  same time yesterday. Press `c` to also race a faint ghost runner placed by that
  gap. Get ahead and it falls behind you.
- **Personal best:** a bright marker on the speed bar. Beat it and a NEW PERSONAL
  BEST popup fires.
- **Streak:** days you coded in a row.
- **Milestones:** run past a signpost at 100K, 500K, 1M tokens, and so on.
- **Session & week gauges:** two small translucent bars worn bottom-left, one
  for the 5-hour block and one for the trailing 7 days. They're blended right
  into the scene, so the runner and the world keep moving behind them, in the
  same heatmap gradient as the speed bar — cool and low when you're light,
  climbing warm as they fill — with the reset countdown above and the amount
  below. By default they show your **real** Claude limit percentages (see
  below); press `u` to switch to a local estimate or hide them.

### The usage gauges: real limits, estimate, or off (`u`)

Out of the box the two gauges show the **actual** numbers from Claude's usage
page — the same "3% used / resets in 4 hr 20 min" you see in Claude Code, session
and weekly. Press `u` to cycle **real → local estimate → off**.

Getting the real numbers is the one time tokenrun uses the network: a single
authenticated call to Anthropic's own usage API, using the Claude Code token
already on your machine (keychain on macOS, `~/.claude` on Linux) — your token,
your account, nothing shared with anyone. No token or no connection just falls
back to the local estimate, and it tells you on screen which mode it's in.

Want it **fully offline**? Press `u` to the estimate (or hidden) state, or start
with `--no-live` (`TOKENRUN_LIVE=0`) and it never touches the network — the gauge
then estimates against your own heaviest recent usage. You can also point the
live mode at a token yourself with `TOKENRUN_TOKEN` or a `~/.tokenrun-token`
file, and `tokenrun --usage-check` prints exactly what the usage API returns.

## The dashboard

Press `TAB` and the whole screen flips to a plain speedometer dashboard: the big
tok/s number, a needle, a recent-speed sparkline, and your 5 hour and 7 day
totals broken into in, cache, out, total. `TAB` again drops you back into the
run. Same engine, no second process. A small two-line version of these stats also
rides along the top while you run, so you always have the numbers.

Only output drives the speed, because output is the part produced over time.
Input and cache are sent all at once per request, so they show up as totals, not
speed.

## Options

| flag / env | default | what it does |
|---|---|---|
| `--tau` / `TOKENRUN_TAU` | `90` | smoothing time for the speedometer (seconds). Lower is twitchier. |
| `--redline` / `TOKENRUN_REDLINE` | `160` | tok/s that counts as full speed / red |
| `--dir` / `TOKENRUN_DIR` | `~/.claude/projects` | where Claude Code keeps its logs |
| `--fps` | `14` | frames per second |
| `--dog` / `--buddy` | off | start with a companion (cycle in-app with `c`) |
| `--no-live` / `TOKENRUN_LIVE=0` | off | fully offline: gauges use a local estimate, no call to Anthropic (in-app: `u`) |
| `--no-usage` | off | start with the usage gauges hidden (toggle with `u`) |
| `--sound` | off | footsteps and cues via macOS afplay |
| `--no-daylight` | off | turn off the time-of-day tint |
| `--demo` | off | scripted run that shows everything, for recording |
| `--width` | `0` | force a width in columns (`0` uses the terminal) |
| `--once` | off | print one frame and quit |
| `--no-alt` | off | don't use the alternate screen buffer |

**Make a demo:** `tokenrun --demo` plays a scripted loop that shows off
everything (every speed, all the biomes, day to night, each companion, the
popups, an idle sit-down, and a peek at the dashboard) on fake data. Nothing is
read from or written to your real usage. Screen record it and press `q` to stop.

## How it works

Claude Code writes a JSONL transcript for each session under `~/.claude/projects/`.
Every assistant turn records its token usage and a timestamp. tokenrun reads
those files, skips the duplicate streaming snapshots, and on each tick only reads
the new bytes at the end, so it stays fast even with hundreds of megabytes of
history. Subagent turns count too.

It's pure Python 3 standard library. No pip install of anything, ever. That's a
rule, not an accident.

## Layout

It's a small package, one job per file, so adding things is easy:

```
tokenrun/
  cli.py        args, the main loop, the TAB toggle
  engine.py     reads transcripts, rates, the 5h / 7d windows
  usage.py      optional --live fetch of the real limits
  dashboard.py  the speedometer view
  render.py     colours and ANSI
  canvas.py     the half-block pixel buffer + PNG writer
  biomes.py     the worlds          <- add a biome
  sprites.py    the props + SPR     <- add a tree
  runner.py     the runner + the dog
  critters.py   ambient life
  scene.py      build_frame, the world assembly
  records.py    personal best / streak / milestones
  hud.py        the game HUD + toasts
  demo.py       the --demo run
```

## Good to know

- The runner, distance, and dashboard totals only see usage on this machine for
  this account — other machines and claude.ai won't show up. (The usage-gauge
  percentages are the exception: they come from Anthropic and reflect your whole
  account, unless you switch the gauge to the local estimate with `u`.)
- The dashboard's 5 hour block and weekly totals are rebuilt from your local
  transcripts and get close to Anthropic's real accounting, which isn't fully
  exposed. Treat them as a good guide, not a billing statement — the usage gauges
  show the exact limit percentages.

## Contributing

Yes please. Adding a biome, a prop, or a critter is a one-file job. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. Do whatever you want with it, just keep the notice. See [LICENSE](LICENSE).
