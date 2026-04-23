#!/usr/bin/env python3
"""
Generate 60-second TTS narration for the OpenSRE reel.
Uses the repo's Gemini TTS pipeline (pipeline.narrator).
Output: output/hyperframes_custom/2026-04-22_opensre-reel/narration.wav
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pipeline.narrator as narrator_module
narrator_module.VOICE_NAME = "Kore"  # More dramatic female voice for this content

from pipeline.narrator import call_tts_with_rotation, _get_tts_keys

OUT_DIR  = ROOT / "output" / "hyperframes_custom" / "2026-04-22_opensre-reel"
OUT_WAV  = OUT_DIR / "narration.wav"
CHUNK_DIR = ROOT / "output" / "opensre_tts_chunks"

SAMPLE_RATE  = 24_000
SAMPLE_WIDTH = 2
CHANNELS     = 1
TOTAL_SECONDS = 60.0
HEADROOM      = 0.90  # occupy 90% of each window, leaving natural pause edges

SEGMENTS = [
    {
        "key": "s1_hook",
        "text": "SWE-bench gave AI the ability to write code. But what happens when that code crashes production?",
        "start": 0.0,
        "end": 5.0,
    },
    {
        "key": "s2_chaos",
        "text": "Right now, you have ten tabs open. Datadog, AWS, traces... it is a massive context-switching nightmare.",
        "start": 5.0,
        "end": 11.0,
    },
    {
        "key": "s3_reveal",
        "text": "Enter OpenSRE. The world's first open-source framework for building AI SRE agents.",
        "start": 11.0,
        "end": 17.0,
    },
    {
        "key": "s4_arch",
        "text": "This is not a wrapper. OpenSRE runs directly on your infrastructure, connecting to over sixty cloud tools.",
        "start": 17.0,
        "end": 25.0,
    },
    {
        "key": "s5_deep",
        "text": "It uses Rust and eBPF to monitor your Linux kernel with barely a two percent overhead. If an app stalls, it creates synthetic logs out of thin air.",
        "start": 25.0,
        "end": 34.0,
    },
    {
        "key": "s6_context",
        "text": "When something breaks, it does not just wake you up. It reads your runbooks, investigates the root cause, and drops a fully contextualized analysis directly into Slack.",
        "start": 34.0,
        "end": 44.0,
    },
    {
        "key": "s7_resolution",
        "text": "They are building the SWE-bench for infrastructure failures, training agents on real-world cloud crashes.",
        "start": 44.0,
        "end": 52.0,
    },
    {
        "key": "s8_cta",
        "text": "Stop babysitting dashboards. It is fully open source. Go clone OpenSRE from Tracer Cloud today.",
        "start": 52.0,
        "end": 60.0,
    },
]


def _pcm_duration(pcm: bytes) -> float:
    return len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH)


def _read_wav_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wf:
        return wf.readframes(wf.getnframes())


def _save_wav(pcm: bytes, path: Path) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def _atempo_filter(speed: float) -> str:
    factors: list[float] = []
    remaining = speed
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    factors.append(remaining)
    return ",".join(f"atempo={f:.6f}" for f in factors)


def _fit_pcm(pcm: bytes, target_seconds: float) -> bytes:
    raw_duration = _pcm_duration(pcm)
    if raw_duration <= 0 or abs(raw_duration - target_seconds) < 0.01:
        return pcm
    speed = raw_duration / target_seconds
    try:
        with tempfile.TemporaryDirectory(prefix="opensre_tts_") as td:
            td_path = Path(td)
            raw_path = td_path / "raw.wav"
            fit_path = td_path / "fit.wav"
            _save_wav(pcm, raw_path)
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(raw_path),
                    "-af", _atempo_filter(speed),
                    "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
                    "-c:a", "pcm_s16le", str(fit_path),
                ],
                check=True,
            )
            return _read_wav_pcm(fit_path)
    except Exception as e:
        print(f" [ffmpeg failed: {e}]", end="", flush=True)
        return pcm


def _overlay(base: bytearray, pcm: bytes, start_seconds: float) -> None:
    start_byte = int(round(start_seconds * SAMPLE_RATE)) * SAMPLE_WIDTH
    end_byte   = min(len(base), start_byte + len(pcm))
    if start_byte >= len(base) or end_byte <= start_byte:
        return
    base[start_byte:end_byte] = pcm[: end_byte - start_byte]


def main() -> None:
    load_dotenv(ROOT / ".env")
    keys = _get_tts_keys()
    if not keys:
        raise RuntimeError("GEMINI_API_KEY or GEMINI_API_KEYS required.")

    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    canvas = bytearray(b"\x00" * int(TOTAL_SECONDS * SAMPLE_RATE) * SAMPLE_WIDTH)

    print(f"Generating OpenSRE narration ({TOTAL_SECONDS:.0f}s, voice=Kore)")
    for seg in SEGMENTS:
        window      = seg["end"] - seg["start"]
        spoken_dur  = round(window * HEADROOM, 3)
        spoken_start = seg["start"] + round((window - spoken_dur) / 2, 3)
        chunk_path  = CHUNK_DIR / f"{seg['key']}.wav"

        print(f"  {seg['key']}: {len(seg['text'].split())} words ...", end="", flush=True)
        if chunk_path.exists():
            raw_pcm = _read_wav_pcm(chunk_path)
            print(" (cached)", end="", flush=True)
        else:
            raw_pcm = call_tts_with_rotation(seg["text"], keys)
            _save_wav(raw_pcm, chunk_path)

        fitted = _fit_pcm(raw_pcm, spoken_dur)
        _overlay(canvas, fitted, spoken_start)
        print(f" raw={_pcm_duration(raw_pcm):.2f}s → fit={_pcm_duration(fitted):.2f}s @ t={spoken_start:.1f}s")

    _save_wav(bytes(canvas), OUT_WAV)
    print(f"\nSaved: {OUT_WAV}")


if __name__ == "__main__":
    main()
