"""Generate small retro sound effects into assets/sounds/ (run once).

Usage:  python assets/make_sounds.py
"""

import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")


def _write(name: str, samples: list[float], amp: float = 0.5) -> None:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = bytearray()
        for s in samples:
            v = max(-1.0, min(1.0, s * amp))
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(bytes(frames))
    print("wrote", path)


def _tone(dur: float, freq: float, decay: float = 0.0) -> list[float]:
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        env = math.exp(-decay * t) if decay > 0 else 1.0
        out.append(math.sin(2 * math.pi * freq * t) * env)
    return out


def _note(freq: float, dur: float, gap: float = 0.02) -> list[float]:
    seg = _tone(dur, freq, decay=3.0)
    seg += [0.0] * int(RATE * gap)
    return seg


def spin() -> list[float]:
    """0.8s mechanical whoosh: rising filtered noise + rising tone."""
    dur = 0.8
    n = int(RATE * dur)
    out = []
    rng = random.Random(7)
    prev = 0.0
    for i in range(n):
        t = i / RATE
        freq = 380 + 1200 * (t / dur)
        white = rng.uniform(-1, 1)
        prev = 0.25 * prev + 0.75 * white  # crude low-pass -> softer hiss
        env = min(1.0, t * 8) * min(1.0, (dur - t) * 8)
        tone = math.sin(2 * math.pi * freq * t) * 0.35
        out.append((prev * 0.7 + tone) * env)
    return out


def tick() -> list[float]:
    """Short mechanical click when a reel latches."""
    return _tone(0.06, 1500, decay=55.0)


def win() -> list[float]:
    """Rising arpeggio: C5 E5 G5 C6."""
    out = []
    for f in (523.25, 659.25, 783.99, 1046.5):
        out += _note(f, 0.16)
    out += _tone(0.28, 1046.5, decay=2.0)
    return out


def jackpot() -> list[float]:
    """Longer fanfare with shimmer."""
    out = []
    for f in (523.25, 659.25, 783.99, 1046.5, 1318.5, 1568.0):
        out += _note(f, 0.16)
    n = int(RATE * 0.5)
    rng = random.Random(11)
    for i in range(n):
        t = i / RATE
        shimmer = rng.uniform(-1, 1) * 0.08
        chord = sum(
            math.sin(2 * math.pi * f * t) * 0.2 for f in (1046.5, 1318.5, 1568.0)
        )
        out.append((chord + shimmer) * math.exp(-1.2 * t))
    return out


def lose() -> list[float]:
    """Soft descending two-tone."""
    out = _note(392.0, 0.18)
    out += _note(311.13, 0.34, gap=0.0)
    return out


def main() -> None:
    base = {
        "spin": (spin(), 0.45),
        "tick": (tick(), 0.5),
        "win": (win(), 0.5),
        "jackpot": (jackpot(), 0.5),
        "lose": (lose(), 0.5),
    }
    # three volume variants per sound: {name}.wav = high, _med = medium,
    # _low = low. The base files stay as the high-volume versions so the
    # old paths remain valid.
    levels = (("low", 0.35), ("med", 0.65), ("high", 1.0))
    for name, (samples, amp) in base.items():
        for suffix, factor in levels:
            fname = f"{name}.wav" if suffix == "high" else f"{name}_{suffix}.wav"
            _write(fname, samples, amp=amp * factor)


if __name__ == "__main__":
    main()
