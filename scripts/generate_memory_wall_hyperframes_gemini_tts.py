#!/usr/bin/env python3
"""
Generate Gemini TTS for the HyperFrames Memory Wall reel without changing the
composition timing.

This reuses the repo's existing Gemini narrator client and fits each generated
chunk into the currently approved HyperFrames scene windows.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pipeline.narrator as narrator_module
from pipeline.narrator import _get_tts_keys, call_tts_with_rotation

narrator_module.VOICE_NAME = "Aoede"

PROJECT_DIR = ROOT / "output" / "hyperframes_custom" / "2026-04-24_memory-wall-hf"
TIMING_PATH = PROJECT_DIR / "narration_timing.json"
OUT_WAV = PROJECT_DIR / "narration.wav"
CHUNK_DIR = PROJECT_DIR / "gemini_tts_chunks_aoede_v3_longform"

SAMPLE_RATE = 24_000
SAMPLE_WIDTH = 2
CHANNELS = 1
TOTAL_SECONDS = 33.8

SEGMENTS = [
    {
        "key": "problem",
        "audio_start": 0.4,
        "duration": 4.8,
        "text": "You added a vector database, and the agent still hallucinates.",
    },
    {
        "key": "retrieval",
        "audio_start": 5.0,
        "duration": 5.4,
        "text": "It can retrieve a relevant chunk, but it still misses the situation around it.",
    },
    {
        "key": "bridge",
        "audio_start": 10.72,
        "duration": 3.78,
        "text": "And in production, that missing context is the whole problem.",
    },
    {
        "key": "context",
        "audio_start": 15.12,
        "duration": 6.42,
        "text": "Production agents need the surrounding context: what changed, who triggered it, when it happened, and what it touched.",
    },
    {
        "key": "diagnosis",
        "audio_start": 22.06,
        "duration": 4.84,
        "text": "That is how it separates a harmless log from a real three A M incident.",
    },
    {
        "key": "resolution",
        "audio_start": 27.4,
        "duration": 5.74,
        "text": "Mem0 turns flat recall into memory with structure, so the agent stops guessing and starts remembering.",
    },
]


def _pcm_duration(pcm: bytes) -> float:
    return len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH)


def _save_wav(pcm: bytes, path: Path) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def _read_wav_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != CHANNELS or wf.getsampwidth() != SAMPLE_WIDTH:
            raise RuntimeError(f"Unexpected WAV format in {path}")
        return wf.readframes(wf.getnframes())


def _resize_pcm_linear(pcm: bytes, target_seconds: float) -> bytes:
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
        return array.array("h", [src[0]] * target_samples).tobytes()

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
    return ",".join(f"atempo={factor:.6f}" for factor in factors)


def _fit_pcm(pcm: bytes, target_seconds: float) -> bytes:
    raw_duration = _pcm_duration(pcm)
    if raw_duration <= 0:
        return _resize_pcm_linear(pcm, target_seconds)
    if raw_duration <= target_seconds + 0.03:
        return pcm

    speed = raw_duration / target_seconds
    try:
        with tempfile.TemporaryDirectory(prefix="memory_wall_hf_gemini_") as td:
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
            return _resize_pcm_linear(fitted, target_seconds)
    except Exception as exc:
        print(f" [ffmpeg fit failed: {exc}; using resample]", end="", flush=True)
        return _resize_pcm_linear(pcm, target_seconds)


def _overlay(base: bytearray, pcm: bytes, start_seconds: float) -> None:
    start_byte = int(round(start_seconds * SAMPLE_RATE)) * SAMPLE_WIDTH
    end_byte = min(len(base), start_byte + len(pcm))
    if start_byte >= len(base) or end_byte <= start_byte:
        return
    base[start_byte:end_byte] = pcm[: end_byte - start_byte]


def _master_wav(input_path: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="memory_wall_hf_master_") as td:
        tmp_path = Path(td) / "mastered.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(input_path),
                "-af",
                (
                    "highpass=f=90,"
                    "lowpass=f=11000,"
                    "acompressor=threshold=-18dB:ratio=2.2:attack=8:release=80:makeup=1.5,"
                    "loudnorm=I=-16:TP=-1.5:LRA=7"
                ),
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                str(CHANNELS),
                "-c:a",
                "pcm_s16le",
                str(tmp_path),
            ],
            check=True,
        )
        output_path.write_bytes(tmp_path.read_bytes())


def main() -> None:
    load_dotenv(ROOT / ".env")
    keys = _get_tts_keys()
    if not keys:
        raise RuntimeError(
            "GEMINI_API_KEY or GEMINI_API_KEYS is required for Gemini TTS."
        )

    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    canvas = bytearray(b"\x00" * int(TOTAL_SECONDS * SAMPLE_RATE) * SAMPLE_WIDTH)
    timing: dict[str, dict[str, object]] = {}

    print("Generating Gemini TTS for HyperFrames Memory Wall")
    for segment in SEGMENTS:
        key = segment["key"]
        text = segment["text"]
        raw_path = CHUNK_DIR / f"{key}.wav"

        print(f"  {key}: {len(text.split())} words...", end="", flush=True)
        if raw_path.exists():
            raw_pcm = _read_wav_pcm(raw_path)
            print(" cached", end="", flush=True)
        else:
            raw_pcm = call_tts_with_rotation(text, keys)
            _save_wav(raw_pcm, raw_path)

        raw_duration = _pcm_duration(raw_pcm)
        synced_pcm = _fit_pcm(raw_pcm, segment["duration"])
        synced_duration = _pcm_duration(synced_pcm)
        _overlay(canvas, synced_pcm, segment["audio_start"])

        timing[key] = {
            "audio_start": segment["audio_start"],
            "duration": round(synced_duration, 3),
            "audio_end": round(segment["audio_start"] + synced_duration, 3),
            "raw_duration": round(raw_duration, 3),
            "text": text,
            "voice": narrator_module.VOICE_NAME,
            "provider": "gemini",
        }
        print(f" raw={raw_duration:.2f}s synced={synced_duration:.2f}s")

    raw_out = PROJECT_DIR / "narration_gemini_raw.wav"
    _save_wav(bytes(canvas), raw_out)
    _master_wav(raw_out, OUT_WAV)

    TIMING_PATH.write_text(
        json.dumps(
            {
                "duration": TOTAL_SECONDS,
                "provider": "gemini",
                "voice": narrator_module.VOICE_NAME,
                "segments": [{"id": key, **value} for key, value in timing.items()],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Saved WAV    -> {OUT_WAV}")
    print(f"Saved timing -> {TIMING_PATH}")


if __name__ == "__main__":
    main()
