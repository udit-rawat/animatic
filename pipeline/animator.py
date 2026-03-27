"""
animator.py — Remotion rendering bridge.

Replaces the Manim-based renderer. No LLM involvement.

Flow:
  1. Load params.json + scene_plan.json + narration_timing.json
  2. Copy narration.wav → remotion/public/narration.wav (staticFile resolution)
  3. Write output/remotion_props.json (merged props for Remotion --props flag)
  4. Execute: npx remotion render src/index.ts VideoComposition <output> --props <props>
  5. Output lands at output/video.mp4 (same contract as before — notifier unchanged)
"""
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time

PARAMS_INPUT  = os.path.join(os.path.dirname(__file__), "..", "output", "params.json")
SCENE_PLAN    = os.path.join(os.path.dirname(__file__), "..", "output", "scene_plan.json")
TIMING_INPUT  = os.path.join(os.path.dirname(__file__), "..", "output", "narration_timing.json")
AUDIO_INPUT   = os.path.join(os.path.dirname(__file__), "..", "output", "narration.wav")
PROPS_PATH    = os.path.join(os.path.dirname(__file__), "..", "output", "remotion_props.json")
OUTPUT_VIDEO  = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
REMOTION_DIR  = os.path.join(os.path.dirname(__file__), "..", "remotion")

RENDER_TIMEOUT = 300   # seconds — Remotion is ~3-5× faster than Manim


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


# ── Props assembly ─────────────────────────────────────────────────────────────

def assemble_props(params: dict, scene_plan: dict, timing: dict) -> dict:
    """
    Merge pipeline outputs into the single RemotionProps object consumed by
    VideoComposition.tsx via --props.

    audioSrc is a filename (not a path) because Remotion resolves it via
    staticFile() against remotion/public/. The file is copied there before render.
    """
    # Total frames = last timing entry's end * 30fps
    total_dur = max(
        v.get("end", v.get("start", 0) + v.get("duration", 0))
        for v in timing.values()
    )
    total_frames = math.ceil(total_dur * 30)

    return {
        "beats":       scene_plan.get("beats", []),
        "params":      params,
        "timing":      timing,
        "audioSrc":    "narration.wav",   # resolved via staticFile() in remotion/public/
        "totalFrames": total_frames,
    }


# ── Remotion execution ─────────────────────────────────────────────────────────

def run_remotion(props_path: str, output_path: str) -> tuple[bool, str]:
    """
    Execute: npx remotion render src/index.ts VideoComposition <output> --props <props>
    cwd = remotion/ so that src/index.ts resolves correctly.
    """
    # Check npx is available
    if not shutil.which("npx"):
        return False, "npx not found — install Node.js 18+ (https://nodejs.org)"

    # Check node_modules are installed
    if not os.path.isdir(os.path.join(REMOTION_DIR, "node_modules", "remotion")):
        return False, (
            "remotion/node_modules not found. "
            "Run: cd remotion && npm install"
        )

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts",
        "VideoComposition",
        os.path.abspath(output_path),
        f"--props={os.path.abspath(props_path)}",
        "--concurrency=4",
        "--log=verbose",
    ]

    with Spinner("Remotion rendering"):
        try:
            result = subprocess.run(
                cmd,
                cwd=REMOTION_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=RENDER_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False, f"Remotion timed out after {RENDER_TIMEOUT}s"

    output = result.stdout or ""
    if result.returncode != 0:
        return False, output[-3000:]
    return True, output


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Load inputs ──────────────────────────────────────────────────────────
    with open(PARAMS_INPUT) as f:
        params = json.load(f)

    with open(SCENE_PLAN) as f:
        scene_plan = json.load(f)

    timing = {}
    if os.path.exists(TIMING_INPUT):
        with open(TIMING_INPUT) as f:
            timing = json.load(f)
    else:
        raise RuntimeError(f"narration_timing.json not found at {TIMING_INPUT}. Run narrator first.")

    # ── Copy audio to remotion/public/ (staticFile resolution) ───────────────
    if not os.path.exists(AUDIO_INPUT):
        raise RuntimeError(f"narration.wav not found at {AUDIO_INPUT}. Run narrator first.")

    public_dir = os.path.join(REMOTION_DIR, "public")
    os.makedirs(public_dir, exist_ok=True)
    shutil.copy2(AUDIO_INPUT, os.path.join(public_dir, "narration.wav"))
    print("✓ narration.wav → remotion/public/narration.wav")

    # ── Assemble props ────────────────────────────────────────────────────────
    props = assemble_props(params, scene_plan, timing)

    total_dur    = props["totalFrames"] / 30.0
    beat_templates = [b["template"] for b in props["beats"]]
    print(f"Video duration: {total_dur:.1f}s  ({props['totalFrames']} frames @ 30fps)")
    print(f"Scene plan:     {' → '.join(beat_templates)}")

    os.makedirs(os.path.dirname(PROPS_PATH), exist_ok=True)
    with open(PROPS_PATH, "w") as f:
        json.dump(props, f, indent=2)
    print(f"✓ Props written → {PROPS_PATH}")

    # ── Render ────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)
    success, log = run_remotion(PROPS_PATH, OUTPUT_VIDEO)

    if not success:
        raise RuntimeError(f"Remotion render failed:\n{log}")

    size_mb = os.path.getsize(OUTPUT_VIDEO) / 1_000_000
    print(f"\n✓ Video saved → {OUTPUT_VIDEO}  ({size_mb:.1f} MB)")
    return OUTPUT_VIDEO


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
