"""Optional live usage: fetch the REAL Claude subscription limits — the exact
numbers Claude Code's own usage screen shows — from Anthropic's `/api/oauth/usage`,
so the gauges can display true limit percentages instead of a local estimate.

This is the one place tokenrun talks to the network, and it is **opt-in**
(``--live`` / ``TOKENRUN_LIVE=1``). It uses your own Claude Code OAuth token,
asks Anthropic about your own account, and shares nothing with anyone else. With
no token or no network it silently returns nothing and the caller falls back to
the local estimate. Still zero dependencies: standard-library ``urllib`` plus
the OS credential store the CLI already uses.

The response shape (documented in the Claude Code client) is::

    { "rate_limits": {
        "five_hour": { "used_percentage": <0-100>, "resets_at": <unix seconds> },  # may be absent
        "seven_day": { "used_percentage": <0-100|null>, "resets_at": <unix seconds> }
    } }

Some builds return the windows at the top level rather than under ``rate_limits``,
and older ones use ``utilization`` instead of ``used_percentage`` — both handled.
"""
import os
import json
import time
import threading
import subprocess
import urllib.request
import urllib.error

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_BETA = "oauth-2025-04-20"
HOME = os.path.expanduser("~")
TOKEN_FILE = os.path.join(HOME, ".tokenrun-token")
CREDS_FILE = os.path.join(HOME, ".claude", ".credentials.json")
KEYCHAIN_SERVICE = "Claude Code-credentials"
REFRESH = 60.0                 # seconds between fetches (limits move slowly)


def _read_body(r):
    """Read an HTTP response body, transparently decompressing gzip/deflate
    (urllib doesn't do it for us) so `json.loads` doesn't choke on raw bytes."""
    data = r.read()
    enc = (r.headers.get("Content-Encoding") or "").lower()
    if data[:2] == b"\x1f\x8b" or "gzip" in enc:
        import gzip
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
    elif "deflate" in enc:
        import zlib
        for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                data = zlib.decompress(data, wbits)
                break
            except Exception:
                continue
    return data.decode("utf-8", "replace")


def _oauth_from(d):
    """Pull the access token out of a Claude Code credentials blob."""
    if isinstance(d, dict):
        o = d.get("claudeAiOauth")
        if isinstance(o, dict) and o.get("accessToken"):
            return o["accessToken"]
        if d.get("accessToken"):
            return d["accessToken"]
    return None


def _from_creds_file():
    try:
        with open(CREDS_FILE) as fh:
            return _oauth_from(json.load(fh))
    except Exception:
        return None


def _from_keychain():
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
             "-a", os.environ.get("USER", ""), "-w"],
            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return None
    if not out:
        return None
    try:
        return _oauth_from(json.loads(out))
    except ValueError:
        return out or None          # a bare token string, not JSON


def find_token():
    """Locate an OAuth token with zero user effort: an explicit override first,
    then the same places the Claude Code CLI keeps its own."""
    t = os.environ.get("TOKENRUN_TOKEN")
    if t and t.strip():
        return t.strip()
    try:
        with open(TOKEN_FILE) as fh:
            t = fh.read().strip()
        if t:
            return t
    except OSError:
        pass
    return _from_creds_file() or _from_keychain()


def token_source():
    """Which source a token would come from (for diagnostics) — never the token."""
    if os.environ.get("TOKENRUN_TOKEN", "").strip():
        return "TOKENRUN_TOKEN env"
    try:
        with open(TOKEN_FILE) as fh:
            if fh.read().strip():
                return TOKEN_FILE
    except OSError:
        pass
    if _from_creds_file():
        return CREDS_FILE
    if _from_keychain():
        return f"keychain ({KEYCHAIN_SERVICE})"
    return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pct(obj):
    """Percentage-used (0-100) for one window, from whichever field is present."""
    if not isinstance(obj, dict):
        return None
    v = _num(obj.get("used_percentage"))
    if v is not None:
        return max(0.0, min(100.0, v))                 # already 0-100
    u = _num(obj.get("utilization"))
    if u is not None:
        u = u * 100.0 if u <= 1.5 else u               # tolerate a 0-1 fraction
        return max(0.0, min(100.0, u))
    r = _num(obj.get("remaining_percentage"))
    if r is not None:
        return max(0.0, min(100.0, 100.0 - r))
    return None


def _to_epoch(v):
    """resets_at may be Unix seconds (number or numeric string) or an ISO-8601
    string — return Unix seconds either way, or None if it can't be read."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    try:
        return float(s)
    except ValueError:
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _window(obj):
    if not isinstance(obj, dict):
        return None
    pct = _pct(obj)
    if pct is None:
        return None
    return {"pct": pct, "resets_at": _to_epoch(obj.get("resets_at"))}


def parse_usage(raw):
    """Turn the raw JSON response into {'five_hour': win|None, 'seven_day': win|None}."""
    rl = raw.get("rate_limits", raw) if isinstance(raw, dict) else {}
    if not isinstance(rl, dict):
        rl = {}
    return {"five_hour": _window(rl.get("five_hour")),
            "seven_day": _window(rl.get("seven_day"))}


def diagnose():
    """One-shot verbose check for `--usage-check`: token source, HTTP status, the
    response's structure (keys + the resets_at value — a timestamp, not a secret)
    and the parsed result. Returns report lines. Never prints the token itself."""
    out = []
    src = token_source()
    out.append("token: " + (("found via " + src) if src else "NOT FOUND"))
    if not src:
        out.append("→ set TOKENRUN_TOKEN, drop a token in ~/.tokenrun-token, or run Claude Code once.")
        return out
    tok = find_token()
    for beta in (OAUTH_BETA, None):
        h = {"Authorization": f"Bearer {tok}", "User-Agent": "tokenrun"}
        if beta:
            h["anthropic-beta"] = beta
        h["Accept"] = "application/json"
        h["Accept-Encoding"] = "identity"
        tag = f"beta={beta}" if beta else "no-beta"
        try:
            with urllib.request.urlopen(urllib.request.Request(USAGE_URL, headers=h), timeout=10) as r:
                ctype = r.headers.get("Content-Type", "?")
                cenc = r.headers.get("Content-Encoding", "none")
                body = _read_body(r)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = " · " + _read_body(e)[:160].replace("\n", " ")
            except Exception:
                pass
            out.append(f"  HTTP {e.code} ({tag}){detail}")
            continue
        except Exception as e:
            out.append(f"  request error ({tag}): {e!r}")
            continue
        out.append(f"  HTTP 200 ({tag})  content-type={ctype} encoding={cenc} bytes={len(body)}")
        try:
            raw = json.loads(body)
        except ValueError:
            out.append("  body is not JSON; first 200 chars: " + repr(body[:200]))
            return out
        rl = raw.get("rate_limits", raw) if isinstance(raw, dict) else {}
        if isinstance(raw, dict):
            out.append("  top-level keys: " + ", ".join(map(str, raw.keys())))
        for w in ("five_hour", "seven_day"):
            win = rl.get(w) if isinstance(rl, dict) else None
            if isinstance(win, dict):
                out.append(f"  {w}: keys={list(win.keys())}  resets_at={win.get('resets_at')!r}")
            else:
                out.append(f"  {w}: {win!r}")
        out.append("  parsed: " + repr(parse_usage(raw)))
        out.append("→ live usage OK. Run `tokenrun --live`." if any(parse_usage(raw).values())
                   else "→ reached the API but couldn't read any window; paste the lines above.")
        return out
    out.append("→ every attempt failed; the gauges will use the local estimate.")
    return out


class LiveUsage:
    """Polls `/api/oauth/usage` on a background thread so the render loop never
    blocks on the network. `snapshot()` returns the latest parsed windows, or
    None until the first successful fetch."""

    def __init__(self):
        self._data = None
        self._lock = threading.Lock()
        self._last = 0.0
        self._busy = False
        self._hdrs = None                 # the anthropic-beta header variant that worked
        self._tok = find_token()          # cached; only re-read when a call is rejected
        self.available = self._tok is not None
        self.error = None

    def _request(self, tok, extra):
        h = {"Authorization": f"Bearer {tok}", "User-Agent": "tokenrun",
             "Accept": "application/json", "Accept-Encoding": "identity"}
        h.update(extra)
        req = urllib.request.Request(USAGE_URL, headers=h)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(_read_body(r))

    def _fetch(self):
        # The exact anthropic-beta header this endpoint wants isn't certain, so try
        # a couple of variants and remember whichever the server accepts.
        variants = [self._hdrs] if self._hdrs is not None else [{"anthropic-beta": OAUTH_BETA}, {}]
        try:
            tok = self._tok or find_token()
            if not tok:
                raise RuntimeError("no-token")
            last = None
            for hv in variants:
                try:
                    raw = self._request(tok, hv)
                except urllib.error.HTTPError as e:
                    last = f"HTTP {e.code}"
                    if e.code in (401, 403):             # token stale → the CLI may have refreshed it
                        fresh = find_token()
                        if fresh and fresh != tok:
                            self._tok = tok = fresh
                            try:
                                raw = self._request(tok, hv)
                            except Exception as e2:
                                last = getattr(e2, "code", None) and f"HTTP {e2.code}" or type(e2).__name__
                                continue
                        else:
                            continue                     # a fresh token wouldn't help; try next header variant
                    else:
                        continue                         # 400/404/etc → likely the header; try next variant
                except Exception as e:
                    last = getattr(e, "reason", None) or type(e).__name__
                    continue
                self._hdrs = hv                          # this variant worked; stick with it
                with self._lock:
                    self._data = parse_usage(raw)
                    self.error = None
                return
            raise RuntimeError(last or "fetch-failed")
        except Exception as e:
            with self._lock:
                self.error = getattr(e, "reason", None) or (str(e) if isinstance(e, RuntimeError) else type(e).__name__)
        finally:
            self._busy = False

    def poll(self, now):
        """Kick off a fetch if it's time and one isn't already running. Cheap and
        non-blocking; safe to call every frame."""
        if self._busy or now - self._last < REFRESH:
            return
        self._last = now
        self._busy = True
        threading.Thread(target=self._fetch, daemon=True).start()

    def snapshot(self):
        with self._lock:
            return self._data
