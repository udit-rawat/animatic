#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import wave
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pipeline.narrator as narrator_module
from pipeline.narrator import _get_tts_keys, call_tts_with_rotation

SAMPLE_RATE = 24_000
CHANNELS = 1
SAMPLE_WIDTH = 2

VOICE_NOTES = {
    "Aoede": "current baseline; calm, clean, precise",
    "Kore": "firmer, more dramatic technical narration",
    "Leda": "younger, brighter delivery",
    "Callirrhoe": "smooth explanatory tone",
    "Autonoe": "bright and quick",
    "Despina": "smooth, warmer read",
    "Erinome": "clear, crisp articulation",
    "Laomedeia": "upbeat but still technical",
    "Achernar": "softer, lower-energy option",
    "Pulcherrima": "forward and present",
    "Vindemiatrix": "gentler, controlled read",
    "Sulafat": "warm, rounded narration",
    "Zephyr": "airy, bright hook voice",
    "Schedar": "even, measured delivery",
}


def save_wav(pcm: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def to_mp3(wav_path: Path, mp3_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(mp3_path),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Gemini TTS voice audition files."
    )
    parser.add_argument(
        "--text",
        default=(
            "PagedAttention does not make the model smaller. "
            "It makes the KV cache stop wasting GPU memory."
        ),
        help="Two-sentence audition text.",
    )
    parser.add_argument(
        "--out",
        default="output/voice_auditions/paged_attention_2026-07-01",
        help="Output directory.",
    )
    parser.add_argument(
        "--voices",
        default=",".join(VOICE_NOTES.keys()),
        help="Comma-separated Gemini prebuilt voice names.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    keys = _get_tts_keys()
    if not keys:
        raise RuntimeError("GEMINI_API_KEY or GEMINI_API_KEYS is required.")

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    voices = [voice.strip() for voice in args.voices.split(",") if voice.strip()]

    index_lines = [
        "# Gemini TTS voice audition",
        "",
        f"Sample text: {args.text}",
        "",
        "| Voice | Duration | Notes | File |",
        "| --- | ---: | --- | --- |",
    ]
    failures: list[tuple[str, str]] = []

    for idx, voice in enumerate(voices, start=1):
        narrator_module.VOICE_NAME = voice
        safe_name = f"{idx:02d}_{voice}"
        wav_path = out_dir / f"{safe_name}.wav"
        mp3_path = out_dir / f"{safe_name}.mp3"
        print(f"{voice}: generating...", end="", flush=True)
        try:
            pcm = call_tts_with_rotation(args.text, keys)
            save_wav(pcm, wav_path)
            to_mp3(wav_path, mp3_path)
            duration = wav_duration(wav_path)
            print(f" {duration:.2f}s")
            index_lines.append(
                f"| {voice} | {duration:.2f}s | {VOICE_NOTES.get(voice, '')} | `{mp3_path.name}` |"
            )
        except Exception as exc:
            print(f" failed: {exc}")
            failures.append((voice, str(exc)))

    if failures:
        index_lines.extend(["", "## Failed voices", ""])
        for voice, err in failures:
            index_lines.append(f"- `{voice}`: {err}")

    (out_dir / "README.md").write_text("\n".join(index_lines) + "\n")
    print(f"\nSaved audition pack -> {out_dir}")


if __name__ == "__main__":
    main()
