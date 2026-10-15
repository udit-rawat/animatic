#!/usr/bin/env python3
"""Scaffold a new reel: a spec in reels/current/ and a blank composition.

The composition is deliberately empty (stage, caption row, registered timeline,
narration track). Animation is authored per topic, never from a shared kit.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.reel_spec import ROOT

# Meta Reels safe zone at 1080x1920: keep the top 14%, bottom 35% and 6% of each
# side free of text and key visuals.
SAFE_AREA = {"x": 65, "y": 270, "width": 950, "height": 978}

INDEX_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  @font-face {{ font-family: "Schibsted Grotesk"; src: url("fonts/SchibstedGrotesk.ttf") format("truetype"); font-weight: 400 900; }}
  @font-face {{ font-family: "Martian Mono"; src: url("fonts/MartianMono.ttf") format("truetype"); font-weight: 100 800; }}
  :root {{
    --bg: #0a0a0c; --ink: #f5f5f7; --muted: #9ba0a6; --faint: #6e7378; --accent: #ffb340;
  }}
  html, body {{ margin: 0; background: var(--bg); }}
  #root {{
    position: relative; width: 1080px; height: 1920px; overflow: hidden;
    background: var(--bg); color: var(--ink); font-family: "Schibsted Grotesk", sans-serif;
  }}
  /* everything that must be read stays inside the safe area */
  #stage {{ position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; }}
  #captions {{
    position: absolute; left: {x}px; width: {w}px; top: {cap_top}px;
    font-size: 54px; font-weight: 700; line-height: 1.15; text-align: center;
  }}
  code, .mono {{ font-family: "Martian Mono", monospace; }}
</style>
</head>
<body>
<div id="root" data-composition-id="{slug}" data-start="0" data-duration="{duration}"
     data-width="1080" data-height="1920">
  <div id="stage"></div>
  <div id="captions"></div>
  <audio id="vo" src="narration.wav" data-start="0" data-duration="{duration}" data-track-index="1"></audio>
</div>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script>
  // Seek-safe rules: no Math.random (use h1), no callback-driven DOM mutation,
  // hidden initial states via gsap.set, every beat keyed to a transcript word.
  const fract = x => x - Math.floor(x);
  const h1 = i => fract(Math.sin(i * 127.1) * 43758.5453);

  const tl = gsap.timeline({{ paused: true }});

  // Frame 0 must already be non-empty and moving (hook gate).

  window.__timelines = window.__timelines || {{}};
  window.__timelines["{slug}"] = tl;
</script>
</body>
</html>
"""


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "new-reel"


def build_spec(title: str, slug: str, duration: float, comp_dir: str, out: str) -> dict:
    return {
        "slug": f"{slug}-v1",
        "title": title,
        "duration": duration,
        "fps": 60,
        "voice": "Sulafat",
        "tts_provider": "gemini",
        "tts_model": "gemini-3.1-flash-tts-preview",
        "composition_dir": comp_dir,
        "output_file": out,
        "render": {"quality": "high", "crf": 10, "workers": 1},
        "audio": {"sample_rate": 24000, "channels": 1, "mastering": True},
        "layout": {
            "canvas": {"width": 1080, "height": 1920},
            "safe_area": SAFE_AREA,
            "check": {"theme": "dark", "max_outside_pixels": 0},
        },
        "gate": {
            "lane": "",
            "keywords": [],
            "mechanism": "One sentence: the hidden mechanism the reel reveals.",
            "ending": "The named technique the viewer can go and use.",
            "kind": "tool",
            "opening": "Opening structure label; must differ from the last 3 reels.",
            "hook": {"frame0": "", "claim_word": "", "captions": True},
            "motion": {"soul": "What the mechanism looks like when it moves.", "families": [], "allow": {}},
        },
        # One segment for the whole read: per-segment TTS calls reset prosody.
        "segments": [
            {
                "id": "vo",
                "start": 0.1,
                "duration": round(duration - 0.3, 2),
                "text": "Replace with the full narration, written as one read.",
            }
        ],
    }


def scaffold(title: str, slug: str | None, duration: float, force: bool) -> None:
    reel_slug = _slugify(slug or title)
    today = date.today().isoformat()
    comp_rel = f"output/hyperframes_custom/{today}_{reel_slug}"
    spec_path = ROOT / "reels" / "current" / f"spec_{reel_slug}_v1.json"
    comp_dir = ROOT / comp_rel
    index_path = comp_dir / "index.html"

    if not force and (spec_path.exists() or index_path.exists()):
        raise SystemExit(f"{spec_path.name} or {comp_rel}/index.html exists. Pass --force to overwrite.")

    spec = build_spec(title, reel_slug, duration, comp_rel, f"output/final/{reel_slug}.mp4")
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")

    sa = SAFE_AREA
    (comp_dir / "fonts").mkdir(parents=True, exist_ok=True)
    for font in (ROOT / "assets" / "fonts").glob("*.ttf"):
        shutil.copy2(font, comp_dir / "fonts" / font.name)
    index_path.write_text(
        INDEX_HTML.format(
            slug=spec["slug"], duration=duration, x=sa["x"], y=sa["y"], w=sa["width"],
            h=sa["height"] - 160, cap_top=sa["y"] + sa["height"] - 140,
        )
    )
    print(f"spec        -> {spec_path.relative_to(ROOT)}")
    print(f"composition -> {comp_rel}/index.html")
    print(f"next        -> python3 scripts/reel_gate.py topic --spec {spec_path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a reel spec and a blank composition.")
    parser.add_argument("--title", required=True, help="Human-readable reel title.")
    parser.add_argument("--slug", help="Optional file-safe slug (defaults to the title).")
    parser.add_argument("--duration", type=float, default=40.0, help="Seconds (deep reels: 35 to 45).")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing spec and composition.")
    args = parser.parse_args()
    scaffold(args.title, args.slug, args.duration, args.force)


if __name__ == "__main__":
    main()
