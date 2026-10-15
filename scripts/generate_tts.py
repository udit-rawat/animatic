#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from scripts.reel_spec import cache_dir, composition_dir, load_spec

SAMPLE_WIDTH = 2


def _pcm_duration(pcm: bytes, sample_rate: int) -> float:
    return len(pcm) / (sample_rate * SAMPLE_WIDTH)


def _save_wav(pcm: bytes, path: Path, sample_rate: int, channels: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def _read_wav_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wf:
        return wf.readframes(wf.getnframes())


def _resize_pcm_linear(pcm: bytes, target_seconds: float, sample_rate: int) -> bytes:
    if target_seconds <= 0:
        return b""
    target_samples = max(1, int(round(target_seconds * sample_rate)))
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


def _fit_pcm(
    pcm: bytes,
    target_seconds: float,
    sample_rate: int,
    channels: int,
    tmp_prefix: str,
    stretch_short: bool = False,
) -> bytes:
    raw_duration = _pcm_duration(pcm, sample_rate)
    if raw_duration <= 0:
        return _resize_pcm_linear(pcm, target_seconds, sample_rate)
    if raw_duration <= target_seconds + 0.03 and not stretch_short:
        return pcm

    speed = raw_duration / target_seconds
    with tempfile.TemporaryDirectory(prefix=tmp_prefix) as td:
        td_path = Path(td)
        raw_path = td_path / "raw.wav"
        fit_path = td_path / "fit.wav"
        _save_wav(pcm, raw_path, sample_rate, channels)
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
                str(sample_rate),
                "-ac",
                str(channels),
                "-c:a",
                "pcm_s16le",
                str(fit_path),
            ],
            check=True,
        )
        fitted = _read_wav_pcm(fit_path)
        return _resize_pcm_linear(fitted, target_seconds, sample_rate)


def _overlay(
    base: bytearray, pcm: bytes, start_seconds: float, sample_rate: int
) -> None:
    start_byte = int(round(start_seconds * sample_rate)) * SAMPLE_WIDTH
    end_byte = min(len(base), start_byte + len(pcm))
    if start_byte >= len(base) or end_byte <= start_byte:
        return
    base[start_byte:end_byte] = pcm[: end_byte - start_byte]


def _master_wav(
    input_path: Path, output_path: Path, sample_rate: int, channels: int, enabled: bool
) -> None:
    if not enabled:
        output_path.write_bytes(input_path.read_bytes())
        return

    with tempfile.TemporaryDirectory(prefix="reel_master_") as td:
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
                str(sample_rate),
                "-ac",
                str(channels),
                "-c:a",
                "pcm_s16le",
                str(tmp_path),
            ],
            check=True,
        )
        output_path.write_bytes(tmp_path.read_bytes())


def generate(spec_path: str, validate_only: bool = False) -> None:
    load_dotenv(ROOT / ".env")
    spec = load_spec(spec_path)
    narrator_module.VOICE_NAME = str(spec.get("voice", "Aoede"))
    if spec.get("tts_model"):
        narrator_module.TTS_MODELS[0] = str(spec["tts_model"])

    if validate_only:
        print(f"Spec valid -> {spec['_spec_path']}")
        print(f"Segments   -> {len(spec['segments'])}")
        print(f"Duration   -> {spec['duration']}s")
        return

    keys = _get_tts_keys()
    if not keys:
        raise RuntimeError(
            "GEMINI_API_KEY or GEMINI_API_KEYS is required for Gemini TTS."
        )

    audio_cfg = spec.get("audio", {})
    sample_rate = int(audio_cfg.get("sample_rate", 24_000))
    channels = int(audio_cfg.get("channels", 1))
    mastering = bool(audio_cfg.get("mastering", True))

    comp_dir = composition_dir(spec)
    comp_dir.mkdir(parents=True, exist_ok=True)
    out_wav = comp_dir / "narration.wav"
    timing_path = comp_dir / "narration_timing.json"
    chunk_dir = cache_dir(spec, "tts") / narrator_module.VOICE_NAME
    chunk_dir.mkdir(parents=True, exist_ok=True)

    duration = float(spec["duration"])
    canvas = bytearray(b"\x00" * int(duration * sample_rate) * SAMPLE_WIDTH)
    timing: dict[str, dict[str, object]] = {}

    print(f"Generating Gemini TTS for {spec['slug']}")
    for segment in spec["segments"]:
        sid = str(segment["id"])
        text = str(segment["text"])
        raw_path = chunk_dir / f"{sid}.wav"
        print(f"  {sid}: {len(text.split())} words...", end="", flush=True)

        if raw_path.exists():
            raw_pcm = _read_wav_pcm(raw_path)
            print(" cached", end="", flush=True)
        else:
            raw_pcm = call_tts_with_rotation(text, keys)
            _save_wav(raw_pcm, raw_path, sample_rate, channels)

        raw_duration = _pcm_duration(raw_pcm, sample_rate)
        target_duration = float(segment["duration"])
        synced_pcm = _fit_pcm(
            raw_pcm,
            target_duration,
            sample_rate,
            channels,
            f"{spec['slug']}_tts_",
            stretch_short=bool(audio_cfg.get("stretch_short_segments", False)),
        )
        synced_duration = _pcm_duration(synced_pcm, sample_rate)
        start = float(segment["start"])
        _overlay(canvas, synced_pcm, start, sample_rate)

        timing[sid] = {
            "audio_start": start,
            "duration": round(synced_duration, 3),
            "audio_end": round(start + synced_duration, 3),
            "raw_duration": round(raw_duration, 3),
            "text": text,
            "voice": narrator_module.VOICE_NAME,
            "provider": "gemini",
        }
        print(f" raw={raw_duration:.2f}s synced={synced_duration:.2f}s")

    raw_out = cache_dir(spec, "tts") / "narration_raw.wav"
    _save_wav(bytes(canvas), raw_out, sample_rate, channels)
    _master_wav(raw_out, out_wav, sample_rate, channels, mastering)

    timing_path.write_text(
        json.dumps(
            {
                "duration": duration,
                "provider": "gemini",
                "voice": narrator_module.VOICE_NAME,
                "segments": [{"id": key, **payload} for key, payload in timing.items()],
            },
            indent=2,
        )
    )

    print(f"Saved WAV    -> {out_wav}")
    print(f"Saved timing -> {timing_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Gemini TTS from a reel spec."
    )
    parser.add_argument(
        "--spec", required=True, help="Path to reel spec JSON (reels/current/spec_<slug>_v1.json)."
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the spec without calling TTS.",
    )
    args = parser.parse_args()
    generate(args.spec, validate_only=args.validate_only)


if __name__ == "__main__":
    main()
