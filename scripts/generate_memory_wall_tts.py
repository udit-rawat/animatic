#!/usr/bin/env python3
"""
Generate scene-locked narration for the Memory Wall reel using the repo's
existing Gemini TTS pipeline.

Each segment is fit into a fixed scene window so the rendered visuals can lock
to exact timings without guessing at the final spoken duration.
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

narrator_module.VOICE_NAME = "Kore"

SAMPLE_RATE = 24_000
SAMPLE_WIDTH = 2
CHANNELS = 1
LEAD_PAD = 0.14
TAIL_PAD = 0.28

OUT_WAV = ROOT / "output" / "memory_wall_narration_v3.wav"
OUT_TIMING = ROOT / "output" / "memory_wall_narration_timing_v3.json"
CHUNK_DIR = ROOT / "output" / "memory_wall_tts_chunks_v3"

SCENES = [
    {
        "key": "problem",
        "scene": "Problem",
        "target_start": 0.0,
        "target_end": 5.5,
        "text": ("You added a vector database, and the agent still makes things up."),
    },
    {
        "key": "isolation",
        "scene": "Isolation",
        "target_start": 5.5,
        "target_end": 12.5,
        "text": (
            "Because retrieval is not memory. "
            "It finds isolated chunks, but it misses the connection."
        ),
    },
    {
        "key": "connection",
        "scene": "Connection",
        "target_start": 12.5,
        "target_end": 19.0,
        "text": ("Production agents need context. " "Semantic memory. State memory."),
    },
    {
        "key": "intelligence",
        "scene": "Intelligence",
        "target_start": 19.0,
        "target_end": 25.5,
        "text": (
            "Who triggered it. " "What changed. When it happened. What else it touched."
        ),
    },
    {
        "key": "diagnosis",
        "scene": "Diagnosis",
        "target_start": 25.5,
        "target_end": 34.0,
        "text": (
            "So it can tell the difference between a harmless log "
            "and a three A M production incident."
        ),
    },
    {
        "key": "solution",
        "scene": "Solution",
        "target_start": 34.0,
        "target_end": 44.0,
        "text": (
            "That is what Mem0 is solving. "
            "The shift from flat recall to memory with structure."
        ),
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
    if raw_duration <= target_seconds:
        return pcm

    speed = raw_duration / target_seconds
    try:
        with tempfile.TemporaryDirectory(prefix="memory_wall_tts_") as td:
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


def _filter_pcm(pcm: bytes, filter_graph: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="memory_wall_filter_") as td:
        td_path = Path(td)
        raw_path = td_path / "raw.wav"
        out_path = td_path / "out.wav"
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
                filter_graph,
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                str(CHANNELS),
                "-c:a",
                "pcm_s16le",
                str(out_path),
            ],
            check=True,
        )
        return _read_wav_pcm(out_path)


def _trim_pcm(pcm: bytes) -> bytes:
    return pcm


def _overlay(base: bytearray, pcm: bytes, start_seconds: float) -> None:
    start_byte = int(round(start_seconds * SAMPLE_RATE)) * SAMPLE_WIDTH
    end_byte = min(len(base), start_byte + len(pcm))
    if start_byte >= len(base) or end_byte <= start_byte:
        return
    base[start_byte:end_byte] = pcm[: end_byte - start_byte]


def _master_wav(input_path: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="memory_wall_master_") as td:
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

    total_seconds = SCENES[-1]["target_end"]
    canvas = bytearray(b"\x00" * int(total_seconds * SAMPLE_RATE) * SAMPLE_WIDTH)
    timing: dict[str, dict[str, object]] = {}
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    OUT_WAV.parent.mkdir(parents=True, exist_ok=True)

    print("Generating Memory Wall narration")
    for scene in SCENES:
        key = scene["key"]
        text = scene["text"].strip()
        start = float(scene["target_start"])
        end = float(scene["target_end"])
        window = max(0.1, end - start)
        max_spoken = round(max(0.1, window - LEAD_PAD - TAIL_PAD), 3)
        spoken_start = round(start + LEAD_PAD, 3)
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
        trimmed_pcm = _trim_pcm(raw_pcm)
        trimmed_duration = _pcm_duration(trimmed_pcm)
        synced_pcm = _fit_pcm(trimmed_pcm, max_spoken)
        synced_duration = _pcm_duration(synced_pcm)
        _overlay(canvas, synced_pcm, spoken_start)

        timing[key] = {
            "scene": scene["scene"],
            "target_start": start,
            "target_end": end,
            "audio_start": round(spoken_start, 3),
            "raw_duration": round(raw_duration, 3),
            "trimmed_duration": round(trimmed_duration, 3),
            "duration": round(synced_duration, 3),
            "audio_end": round(spoken_start + synced_duration, 3),
            "text": text,
        }
        print(
            f" raw={raw_duration:.2f}s trimmed={trimmed_duration:.2f}s "
            f"synced={synced_duration:.2f}s"
        )

    raw_out = OUT_WAV.with_name(f"{OUT_WAV.stem}_raw.wav")
    _save_wav(bytes(canvas), raw_out)
    _master_wav(raw_out, OUT_WAV)
    with OUT_TIMING.open("w") as f:
        json.dump(timing, f, indent=2)

    print(f"Saved WAV    -> {OUT_WAV}")
    print(f"Saved timing -> {OUT_TIMING}")
    print(f"Total audio  -> {total_seconds:.1f}s")


if __name__ == "__main__":
    main()
