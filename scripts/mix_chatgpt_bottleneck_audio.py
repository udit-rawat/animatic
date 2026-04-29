#!/usr/bin/env python3
from __future__ import annotations

import array
import math
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP_DIR = ROOT / "output" / "hyperframes_custom" / "2026-04-28_chatgpt-typing-bottleneck-hf"
SRC = COMP_DIR / "narration.wav"
OUT_A = COMP_DIR / "narration_a.wav"
OUT_B = COMP_DIR / "narration_b.wav"
SR = 24_000
MAX_I16 = 32767


def read_wav(path: Path) -> array.array:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        pcm = array.array("h")
        pcm.frombytes(wf.readframes(wf.getnframes()))
    if sample_rate != SR:
        raise RuntimeError(f"Expected {SR}Hz narration, got {sample_rate}Hz")
    if channels == 1:
        return pcm
    mono = array.array("h")
    for i in range(0, len(pcm), channels):
        mono.append(int(sum(pcm[i : i + channels]) / channels))
    return mono


def write_wav(path: Path, samples: array.array) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(samples.tobytes())


def ensure_len(samples: array.array, seconds: float) -> array.array:
    target = int(seconds * SR)
    if len(samples) >= target:
        return array.array("h", samples[:target])
    out = array.array("h", samples)
    out.extend([0] * (target - len(out)))
    return out


def clamp(v: float) -> int:
    return max(-MAX_I16, min(MAX_I16, int(v)))


def add(samples: array.array, t: float, value: float) -> None:
    i = int(t * SR)
    if 0 <= i < len(samples):
        samples[i] = clamp(samples[i] + value)


def sine_mix(samples: array.array, start: float, duration: float, freq: float, amp: float, fade: float = 0.01) -> None:
    n0 = int(start * SR)
    count = int(duration * SR)
    fade_n = max(1, int(fade * SR))
    for n in range(count):
        idx = n0 + n
        if idx >= len(samples):
            break
        env = min(1.0, n / fade_n, (count - n) / fade_n)
        add(samples, idx / SR, math.sin(2 * math.pi * freq * n / SR) * amp * env)


def click(samples: array.array, start: float, amp: float, freq: float = 2400.0, duration: float = 0.018) -> None:
    n0 = int(start * SR)
    count = int(duration * SR)
    for n in range(count):
        idx = n0 + n
        if idx >= len(samples):
            break
        env = math.exp(-n / max(1, count * 0.22))
        tone = math.sin(2 * math.pi * freq * n / SR)
        snap = 1.0 if n % 7 < 3 else -0.4
        samples[idx] = clamp(samples[idx] + amp * env * (0.7 * tone + 0.3 * snap))


def thud(samples: array.array, start: float, amp: float = 5200.0) -> None:
    n0 = int(start * SR)
    count = int(0.3 * SR)
    for n in range(count):
        idx = n0 + n
        if idx >= len(samples):
            break
        env = math.exp(-n / (SR * 0.075))
        tone = math.sin(2 * math.pi * 40 * n / SR)
        samples[idx] = clamp(samples[idx] + amp * env * tone)


def duck(samples: array.array, start: float, duration: float, gain: float) -> None:
    n0 = int(start * SR)
    n1 = min(len(samples), n0 + int(duration * SR))
    for idx in range(n0, n1):
        samples[idx] = clamp(samples[idx] * gain)


def vacuum(samples: array.array, center: float) -> None:
    start = center - 0.075
    for n in range(int(0.15 * SR)):
        t = n / SR
        idx = int((start + t) * SR)
        if idx < 0 or idx >= len(samples):
            continue
        if t < 0.05:
            gain = math.exp(-72 * t)
        elif t < 0.10:
            gain = 0.032
        else:
            gain = 0.032 + (1.0 - 0.032) * (1.0 - math.exp(-72 * (t - 0.10)))
        samples[idx] = clamp(samples[idx] * gain)


def resample_segment(samples: array.array, start: float, end: float, target_duration: float) -> array.array:
    src = samples[int(start * SR) : int(end * SR)]
    target = max(1, int(target_duration * SR))
    if not src:
        return array.array("h", [0] * target)
    out = array.array("h")
    scale = (len(src) - 1) / max(1, target - 1)
    for i in range(target):
        pos = i * scale
        left = int(pos)
        right = min(left + 1, len(src) - 1)
        frac = pos - left
        out.append(clamp(src[left] * (1 - frac) + src[right] * frac))
    return out


def build_b(samples: array.array) -> array.array:
    head = array.array("h", samples[: int(39 * SR)])
    tail = resample_segment(samples, 39, 47, 5)
    head.extend(tail)
    return ensure_len(head, 44)


def mix(samples: array.array, seconds: float, final_thud_at: float) -> array.array:
    out = ensure_len(samples, seconds)

    # Constant premium low computer bed, low enough to sit under narration.
    sine_mix(out, 0, seconds, 80, 450, fade=0.25)
    sine_mix(out, 0, seconds, 145, 150, fade=0.25)

    for t in [0.0, 0.34, 0.7, 1.05, 1.4, 1.78, 2.16, 2.55, 2.95, 3.35, 3.74, 4.15, 4.58, 5.0]:
        click(out, t, 1700, 2800, 0.014)
    for t in [3.05, 3.85, 4.65, 5.45]:
        click(out, t, 950, 920, 0.025)

    vacuum(out, 6.0)
    thud(out, 6.16, amp=3600)

    for t in [9.46, 9.72, 9.98, 10.24, 10.5, 10.78]:
        click(out, t, 1350, 1500, 0.018)
    for t in [12.4, 13.1, 13.8, 14.5, 15.2, 15.9, 16.6, 17.3, 18.0]:
        click(out, t, 800, 3300, 0.012)

    for t in [19.35 + i * 0.3 for i in range(16)]:
        click(out, t, 760, 1150, 0.02)
    sine_mix(out, 24.0, 1.6, 120, 1100, fade=0.18)
    for t in [25.12, 25.36, 25.60]:
        click(out, t, 1600, 1800, 0.018)

    for t in [30.5, 32.1, 34.7]:
        sine_mix(out, t, 0.16, 190, 1600, fade=0.02)
        click(out, t, 1100, 850, 0.024)
    for t in [30.0, 31.2, 32.4, 33.6, 34.8, 36.0, 37.2, 38.4]:
        click(out, t, 1050, 620, 0.03)

    duck(out, 39.0, 0.2, 0.2)
    sine_mix(out, 40.65, 3.0 if seconds > 45 else 1.7, 220, 520, fade=0.12)
    thud(out, final_thud_at, amp=4200)
    return out


def main() -> None:
    narration = read_wav(SRC)
    mixed_a = mix(narration, 47, 45.0)
    write_wav(OUT_A, mixed_a)
    mixed_b = mix(build_b(narration), 44, 42.0)
    write_wav(OUT_B, mixed_b)
    print(f"Wrote {OUT_A}")
    print(f"Wrote {OUT_B}")


if __name__ == "__main__":
    main()
