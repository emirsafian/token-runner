"""Opt-in sound cues via macOS afplay (a no-op on other platforms)."""
import os
import sys
import time
import shutil
import subprocess


MAC_SOUNDS = {
    "step": "/System/Library/Sounds/Tink.aiff",
    "blaze": "/System/Library/Sounds/Blow.aiff",
    "biome": "/System/Library/Sounds/Glass.aiff",
    "pb": "/System/Library/Sounds/Hero.aiff",
    "milestone": "/System/Library/Sounds/Funk.aiff",
}


class Sound:
    def __init__(self, on):
        self.on = bool(on) and sys.platform == "darwin" and shutil.which("afplay")
        self.last = {}

    def play(self, name, gap=0.0, vol=0.3):
        if not self.on:
            return
        now = time.time()
        if now - self.last.get(name, 0) < gap:
            return
        self.last[name] = now
        p = MAC_SOUNDS.get(name)
        if p and os.path.exists(p):
            try:
                subprocess.Popen(["afplay", "-v", str(vol), p],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
