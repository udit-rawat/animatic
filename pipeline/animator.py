"""
animator.py — assembles a Manim scene from fixed templates + extracted params.

No LLM code generation. Templates are deterministic Python functions that
generate code strings. Variable data comes from:
  params.json       — per-beat extracted params (from param_extractor.py)
  scene_plan.json   — which template each beat uses (from scene_planner.py)
  narration_timing.json — real TTS durations (from narrator.py)

Flow:
  1. Load scene_plan.json + params.json + narration_timing.json
  2. Dispatch each beat to its assigned template with real duration
  3. Assemble into a single ContentScene script
  4. Run Manim, copy output video
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time

PARAMS_INPUT     = os.path.join(os.path.dirname(__file__), "..", "output", "params.json")
SCENE_PLAN_INPUT = os.path.join(os.path.dirname(__file__), "..", "output", "scene_plan.json")
TIMING_INPUT     = os.path.join(os.path.dirname(__file__), "..", "output", "narration_timing.json")
MANIM_SCRIPT     = os.path.join(os.path.dirname(__file__), "..", "manim_scripts", "scene.py")
OUTPUT_VIDEO     = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")

MANIM_TIMEOUT = 480


# ── Spinner ───────────────────────────────────────────────────────────────────

class Spinner:
    CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, message: str):
        self.message = message
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        i = 0
        start = time.time()
        while not self._stop.is_set():
            elapsed = int(time.time() - start)
            sys.stdout.write(f"\r{self.CHARS[i % len(self.CHARS)]}  {self.message} ({elapsed}s elapsed)  ")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * 70 + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *args):
        self._stop.set()
        self._thread.join()


# ── Script assembly ───────────────────────────────────────────────────────────

MANIM_HEADER = """\
from manim import config
config.pixel_width  = 1080
config.pixel_height = 1920
config.frame_rate   = 30
from manim import *
import numpy as np

# ── Palette ───────────────────────────────────────────────────────────────────
C_WHITE  = "#FDFDFD"
C_GREEN  = "#00FF41"
C_CYAN   = "#00E5FF"
C_YELLOW = "#FFD600"
C_RED    = "#FF4444"

# ── Font sizes ────────────────────────────────────────────────────────────────
# Portrait frame = 25.3 Manim units tall (1080x1920).
# 1 unit ≈ 76px. At font_size=48 ≈ 0.5 units ≈ 38px (tiny on phone).
# These sizes are tuned so text occupies 8-20% of screen height.
FS_STAT     = 300  # hook key number — hero element, dominates screen
FS_HOOK     = 120  # hook phrase (short, 5-8 words)
FS_CONCEPT  = 100  # concept header (short, 5-7 words)
FS_LABEL    = 80   # panel section titles
FS_DETAIL   = 68   # panel content text
FS_TAKEAWAY = 160  # closing takeaway — big, bold, impactful

# ── Zone constants (portrait frame: 14.2w × 25.3h, y-safe ±11) ──────────────
# TEXT ZONE  : y ≥ 6    (top ~35% of frame — concept headers only)
# BUFFER     : y = 2–6  (breathing room — nothing lives here)
# ANIM ZONE  : y ≤ 2    (bottom ~60% — all visual elements)

"""


def assemble_scene(params: dict, timing: dict, scene_plan: dict) -> str:
    from pipeline.templates import (
        beat1_hook, beat2_pipeline, beat3_before_after, beat4_takeaway,
        beat_stats_grid, beat_timeline,
    )

    TEMPLATE_MAP = {
        "hook":       beat1_hook,
        "pipeline":   beat2_pipeline,
        "comparison": beat3_before_after,
        "stats_grid": beat_stats_grid,
        "timeline":   beat_timeline,
        "takeaway":   beat4_takeaway,
    }

    # Timing key mapping: beat 1 → "hook", last → "takeaway_cta", middles → "concept_1", "concept_2", ...
    beats = scene_plan.get("beats", [])
    total = len(beats)

    def beat_duration(beat_num: int) -> float:
        if beat_num == 1:
            key = "hook"
        elif beat_num == total:
            key = "takeaway_cta"
        else:
            middle_idx = beat_num - 2  # 0-indexed among middle beats
            key = f"concept_{middle_idx + 1}"
        return timing.get(key, {}).get("duration", 12.0)

    beat_blocks = []
    for beat in beats:
        beat_num = beat["beat"]
        template = beat["template"]
        module   = TEMPLATE_MAP[template]
        beat_params = params.get(f"beat_{beat_num}", params)  # fallback to flat for safety
        duration    = beat_duration(beat_num)
        beat_blocks.append(module.generate(beat_params, duration))

    body = (
        MANIM_HEADER
        + "class ContentScene(Scene):\n"
        + "    def construct(self):\n"
        + "\n".join(beat_blocks) + "\n"
    )
    return body


# ── Manim execution ───────────────────────────────────────────────────────────

def run_manim(script_path: str) -> tuple[bool, str]:
    with Spinner("Manim rendering"):
        try:
            result = subprocess.run(
                ["manim", "-qh", script_path, "ContentScene", "--format=mp4"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=MANIM_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False, f"Manim timed out after {MANIM_TIMEOUT}s"

    output = result.stdout or ""
    if result.returncode != 0:
        return False, output[-3000:]
    if "Played 0 animations" in output:
        return False, "Scene played 0 animations — all beats need at least one self.play() call."
    return True, ""


def find_rendered_mp4(script_path: str) -> str | None:
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    roots = [
        os.path.join(os.path.dirname(script_path), "media", "videos", script_name),
        os.path.join(os.getcwd(), "media", "videos", script_name),
    ]
    for root in roots:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith(".mp4"):
                    return os.path.join(dirpath, f)
    return None


def cleanup_manim_media(script_path: str):
    for root in [os.path.dirname(script_path), os.getcwd()]:
        media = os.path.join(root, "media")
        if os.path.isdir(media):
            shutil.rmtree(media)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load inputs
    with open(PARAMS_INPUT) as f:
        params = json.load(f)

    with open(SCENE_PLAN_INPUT) as f:
        scene_plan = json.load(f)

    timing = {}
    if os.path.exists(TIMING_INPUT):
        with open(TIMING_INPUT) as f:
            timing = json.load(f)

    total_dur = sum(v.get("duration", 0) for v in timing.values())
    beats = scene_plan.get("beats", [])
    templates = [b["template"] for b in beats]
    print(f"Video duration from narration: {total_dur:.1f}s")
    print(f"Scene plan: {' → '.join(templates)}")

    # Assemble Manim script
    scene_code = assemble_scene(params, timing, scene_plan)
    os.makedirs(os.path.dirname(MANIM_SCRIPT), exist_ok=True)
    with open(MANIM_SCRIPT, "w") as f:
        f.write(scene_code)
    print(f"✓ Manim script written ({len(scene_code.splitlines())} lines) → {MANIM_SCRIPT}")

    # Render
    success, error = run_manim(MANIM_SCRIPT)
    if not success:
        raise RuntimeError(f"Manim render failed:\n{error}")

    mp4 = find_rendered_mp4(MANIM_SCRIPT)
    if not mp4:
        raise RuntimeError("Manim exited 0 but no .mp4 found.")

    os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)
    shutil.copy2(mp4, OUTPUT_VIDEO)
    cleanup_manim_media(MANIM_SCRIPT)
    print(f"\n✓ Video saved → {OUTPUT_VIDEO}")
    return OUTPUT_VIDEO


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
