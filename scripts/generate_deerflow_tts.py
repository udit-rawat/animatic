#!/usr/bin/env python3
"""
Generate scene-synced DeerFlow narration with the repo's existing Gemini TTS path.

This intentionally imports pipeline.narrator instead of adding another TTS client.
Each Gemini-generated PCM chunk is placed into the matching GSAP scene window so
the final WAV is exactly 30 seconds at 24 kHz mono.
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

from pipeline.narrator import call_tts_with_rotation, _get_tts_keys

PREVIEW_PATH = ROOT / "output" / "deerflow_narration_preview.json"
OUT_WAV = ROOT / "output" / "deerflow_narration_30s.wav"
OUT_TIMING = ROOT / "output" / "deerflow_narration_30s_timing.json"
CHUNK_DIR = ROOT / "output" / "deerflow_tts_chunks"

SAMPLE_RATE = 24_000
SAMPLE_WIDTH = 2
CHANNELS = 1
TOTAL_SECONDS = 30.0
HEADROOM = 0.92


def _pcm_duration(pcm: bytes) -> float:
    return len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH)


def _resize_pcm_linear(pcm: bytes, target_seconds: float) -> bytes:
    """Resample int16 mono PCM to an exact duration with simple linear interpolation."""
    if target_seconds <= 0:
        return b""

    target_samples = max(1, int(round(target_seconds * SAMPLE_RATE)))
    source_samples = len(pcm) // SAMPLE_WIDTH
    if source_samples <= 0:
        return b"\x00" * target_samples * SAMPLE_WIDTH
    if source_samples == target_samples:
        return pcm

    import array

    src = array.array("h")
    src.frombytes(pcm)

    if source_samples == 1:
        dst = array.array("h", [src[0]] * target_samples)
        return dst.tobytes()

    dst = array.array("h")
    scale = (source_samples - 1) / max(1, target_samples - 1)
    for i in range(target_samples):
        pos = i * scale
        left = int(pos)
        right = min(left + 1, source_samples - 1)
        frac = pos - left
        sample = int(src[left] * (1.0 - frac) + src[right] * frac)
        dst.append(sample)
    return dst.tobytes()


def _read_wav_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != CHANNELS or wf.getsampwidth() != SAMPLE_WIDTH:
            raise RuntimeError(f"Unexpected WAV format in {path}")
        return wf.readframes(wf.getnframes())


def _atempo_filter(speed: float) -> str:
    """Build an atempo chain. FFmpeg atempo supports 0.5..100; keep links tame."""
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
    """
    Time-fit with FFmpeg atempo when available so pitch stays natural.
    Fall back to linear resampling only if FFmpeg fails.
    """
    raw_duration = _pcm_duration(pcm)
    if raw_duration <= 0:
        return _resize_pcm_linear(pcm, target_seconds)

    speed = raw_duration / target_seconds
    try:
        with tempfile.TemporaryDirectory(prefix="deerflow_tts_") as td:
            td_path = Path(td)
            raw_path = td_path / "raw.wav"
            fit_path = td_path / "fit.wav"
            _save_wav(pcm, raw_path)
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(raw_path),
                    "-af",
                    _atempo_filter(speed),
                    "-ar",
                    str(SAMPLE_RATE),
                    "-ac",
                    str(CHANNELS),
                    "-c:a",
                    "pcm_s16le",
                    str(fit_path),
                ],
                check=True,
            )
            fitted = _read_wav_pcm(fit_path)
            # atempo can land a few samples off; correct only the tiny remainder.
            return _resize_pcm_linear(fitted, target_seconds)
    except Exception as e:
        print(f" [ffmpeg fit failed: {e}; using resample]", end="", flush=True)
        return _resize_pcm_linear(pcm, target_seconds)


def _overlay(base: bytearray, pcm: bytes, start_seconds: float) -> None:
    start_byte = int(round(start_seconds * SAMPLE_RATE)) * SAMPLE_WIDTH
    end_byte = min(len(base), start_byte + len(pcm))
    if start_byte >= len(base) or end_byte <= start_byte:
        return
    base[start_byte:end_byte] = pcm[: end_byte - start_byte]


def _save_wav(pcm: bytes, path: Path) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def main() -> None:
    load_dotenv(ROOT / ".env")
    keys = _get_tts_keys()
    if not keys:
        raise RuntimeError(
            "GEMINI_API_KEY or GEMINI_API_KEYS is required for Gemini TTS."
        )

    with PREVIEW_PATH.open() as f:
        preview = json.load(f)

    canvas = bytearray(b"\x00" * int(TOTAL_SECONDS * SAMPLE_RATE) * SAMPLE_WIDTH)
    timing: dict[str, dict[str, object]] = {}
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating Gemini TTS from {PREVIEW_PATH}")
    for scene in preview["scene_sync"]:
        key = scene["segment_key"]
        text = scene["text"].strip()
        start = float(scene["target_start"])
        end = float(scene["target_end"])
        window = max(0.1, end - start)
        target_spoken = round(window * HEADROOM, 3)
        spoken_start = start + round((window - target_spoken) / 2, 3)
        raw_path = CHUNK_DIR / f"{key}.wav"

        print(
            f"  {scene['scene']} / {key}: {len(text.split())} words...",
            end="",
            flush=True,
        )
        if raw_path.exists():
            raw_pcm = _read_wav_pcm(raw_path)
            print(" cached", end="", flush=True)
        else:
            raw_pcm = call_tts_with_rotation(text, keys)
            _save_wav(raw_pcm, raw_path)
        raw_duration = _pcm_duration(raw_pcm)
        synced_pcm = _fit_pcm(raw_pcm, target_spoken)
        synced_duration = _pcm_duration(synced_pcm)
        _overlay(canvas, synced_pcm, spoken_start)

        timing[key] = {
            "scene": scene["scene"],
            "target_start": start,
            "target_end": end,
            "audio_start": round(spoken_start, 3),
            "raw_duration": round(raw_duration, 3),
            "duration": round(synced_duration, 3),
            "audio_end": round(spoken_start + synced_duration, 3),
            "text": text,
        }
        print(f" raw={raw_duration:.2f}s synced={synced_duration:.2f}s")

    OUT_WAV.parent.mkdir(parents=True, exist_ok=True)
    _save_wav(bytes(canvas), OUT_WAV)
    with OUT_TIMING.open("w") as f:
        json.dump(timing, f, indent=2)

    print(f"Saved WAV    -> {OUT_WAV}")
    print(f"Saved timing -> {OUT_TIMING}")
    print(f"Total audio  -> {TOTAL_SECONDS:.1f}s")


if __name__ == "__main__":
    main()
