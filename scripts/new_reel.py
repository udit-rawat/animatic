#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.reel_spec import ROOT


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "new-reel"


def scaffold(title: str, slug: str | None, force: bool) -> None:
    reel_slug = _slugify(slug or title)
    current = ROOT / "reels" / "current"
    current.mkdir(parents=True, exist_ok=True)

    spec_path = current / "spec.json"
    index_path = current / "index.html"
    if not force and (spec_path.exists() or index_path.exists()):
        raise RuntimeError(
            "reels/current already exists. Pass --force to replace spec only."
        )

    if force and spec_path.exists():
        backup = ROOT / "cache" / "old_specs" / f"{reel_slug}.spec.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec_path, backup)
        print(f"Backed up old spec -> {backup}")

    spec = {
        "slug": reel_slug,
        "title": title,
        "duration": 20.0,
        "fps": 60,
        "voice": "Aoede",
        "tts_provider": "gemini",
        "composition_dir": "reels/current",
        "output_file": f"output/final/{reel_slug}.mp4",
        "render": {"quality": "high", "crf": 6, "workers": 1},
        "audio": {"sample_rate": 24000, "channels": 1, "mastering": True},
        "segments": [
            {
                "id": "hook",
                "start": 0.35,
                "duration": 3.2,
                "text": "Replace this with the hook.",
            },
            {
                "id": "explain",
                "start": 3.95,
                "duration": 7.5,
                "text": "Replace this with the main explanation.",
            },
            {
                "id": "payoff",
                "start": 11.8,
                "duration": 5.0,
                "text": "Replace this with the payoff.",
            },
            {
                "id": "cta",
                "start": 17.1,
                "duration": 2.4,
                "text": "Replace this with the call to action.",
            },
        ],
    }
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")
    print(f"Wrote spec -> {spec_path}")
    print(f"Edit composition -> {index_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a new reel spec in reels/current."
    )
    parser.add_argument("--title", required=True, help="Human-readable reel title.")
    parser.add_argument("--slug", help="Optional URL/file-safe slug.")
    parser.add_argument(
        "--force", action="store_true", help="Replace current spec after backing it up."
    )
    args = parser.parse_args()
    scaffold(args.title, args.slug, args.force)


if __name__ == "__main__":
    main()
