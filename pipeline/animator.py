import json
import os
import shutil
import subprocess
import sys
import threading
import time

from pipeline import claude_client

SCRIPT_INPUT   = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TIMING_INPUT   = os.path.join(os.path.dirname(__file__), "..", "output", "narration_timing.json")
RETRIES_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "output", "animator_retries.json")
MANIM_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "manim_scripts", "scene.py")
OUTPUT_VIDEO   = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
MAX_RETRIES    = 3


class Spinner:
    """Shows a live spinner + elapsed time while a long operation runs."""
    CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, message: str):
        self.message = message
        self._stop = threading.Event()
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


def extract_python(raw: str) -> str:
    """
    Robustly extract only valid Python from Claude's response.
    Handles: plain code, ```python fences, mixed prose+code.
    Always returns something that starts with a Python import or config line.
    """
    # Strategy 1: extract from ```python ... ``` fence
    if "```python" in raw:
        code = raw.split("```python", 1)[1]
        code = code.split("```")[0]
        return code.strip()

    # Strategy 2: extract from generic ``` ... ``` fence
    if "```" in raw:
        parts = raw.split("```")
        for part in parts[1::2]:   # odd-indexed = inside fences
            stripped = part.strip()
            if stripped.startswith(("from ", "import ", "#", "config")):
                return stripped

    # Strategy 3: find the first line that looks like Python and take everything from there
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(("from manim", "import manim", "from manim import config", "config.pixel")):
            return "\n".join(lines[i:])

    # Strategy 4: return raw and let Manim surface the error
    return raw


def strip_markdown_artifacts(code: str) -> str:
    """Remove any stray markdown fences the LLM left inside the code."""
    lines = code.splitlines()
    cleaned = [ln for ln in lines if ln.strip() not in ("```", "```python", "```py")]
    return "\n".join(cleaned)


def _load_timing() -> dict:
    if os.path.exists(TIMING_INPUT):
        with open(TIMING_INPUT) as f:
            return json.load(f)
    return {}


def _timing_block(script: dict, timing: dict) -> str:
    """Build the VIDEO SCRIPT section of the prompt, with timecodes if available."""
    if not timing:
        bullets = "\n".join(f"  - {b}" for b in script["concept_bullets"])
        return (
            f"VIDEO SCRIPT:\n"
            f"  Hook    (0-5s):   {script['hook']}\n"
            f"  Concept (5-45s):\n{bullets}\n"
            f"  Takeaway (45-55s): {script['takeaway']}\n"
            f"  CTA      (55-60s): {script['cta']}\n"
        )

    def tc(key: str) -> str:
        t = timing.get(key, {})
        if t:
            return f"[{t['start']:.1f}s → {t['end']:.1f}s  dur={t['duration']:.1f}s]"
        return ""

    n = len(script["concept_bullets"])
    concept_lines = "\n".join(
        f"  - {tc(f'concept_{i+1}')} {b}"
        for i, b in enumerate(script["concept_bullets"])
    )
    total = sum(t.get("duration", 0) for t in timing.values())

    return (
        f"VIDEO SCRIPT WITH NARRATION TIMECODES (narration is pre-recorded — match these exactly):\n"
        f"  Hook    {tc('hook')}: {script['hook']}\n"
        f"  Concept:\n{concept_lines}\n"
        f"  Takeaway+CTA {tc('takeaway_cta')}: {script['takeaway']} / {script.get('cta', '')}\n"
        f"\n"
        f"CRITICAL SYNC REQUIREMENT:\n"
        f"  Total video duration must be exactly {total:.1f} seconds.\n"
        f"  Use self.wait() so that each section's animations START and END at the shown timecodes.\n"
        f"  The viewer hears narration for that section while watching its animation — they must align.\n"
    )


def build_manim_prompt(script: dict, previous_code: str = None, error: str = None) -> str:
    timing = _load_timing()
    script_block = _timing_block(script, timing)
    total_dur = int(sum(t.get("duration", 0) for t in timing.values())) if timing else 60

    base = f"""\
You are a Manim Community Edition expert. Generate a complete, runnable Manim Python script
for a 16-second portrait-format Instagram dopamine-loop video for AI engineers.

{script_block}
VISUAL IDENTITY — follow exactly:
  - Background: BLACK (#000000)
  - Primary color: Phosphor Green (#00FF41) — use for key terms, numbers, highlights
  - Secondary color: High-Contrast White (#FDFDFD) — use for body text
  - Accent: dim green (#007A1F) — use for grid lines, background elements
  - ALL text must use Text() with font="Monospace" — system terminal aesthetic
  - NO Tex(), NO MathTex(), NO LaTeX — only Text()

SCENE STRUCTURE — 4 beats, strict timing:
  Beat 1 — The Anomaly     (0s-10s):
    High-density chaotic dot cloud (blue/white dots scattered). Around 8s trigger a
    snap-collapse where all points flatten to a 2D plane in one sharp Transform.

  Beat 2 — The Collapse    (10s-25s):
    Show scattered random dots collapsing into a tight grid/matrix pattern using Transform.
    Text labels flash on screen for max 2.0 seconds then fade. No lingering text.

  Beat 3 — The Contrast    (25s-45s):
    Split screen using a vertical Line in center: LEFT side shows a rigid grid of dots
    with straight Line connectors (syntactic). RIGHT side shows curved arcs connecting
    clustered dots (semantic). Label LEFT "SYNTAX" and RIGHT "SEMANTICS" in phosphor
    green using FadeIn/FadeOut.

  Beat 4 — The Hook Loop   (45s-60s):
    Animate an Arrow moving left to right across the screen using GrowArrow.
    At 58s FadeOut everything, then FadeIn ONLY the Beat 1 opening Text object
    to create a seamless replay loop.

TECHNICAL REQUIREMENTS:
  - Portrait format at the TOP before imports:
      from manim import config
      config.pixel_width = 1080
      config.pixel_height = 1920
      config.frame_rate = 30
  - Total duration: exactly {total_dur} seconds
  - Class name: ContentScene (inherits from Scene)
  - Standard Manim CE imports + numpy only
  - Flash text rule: no Text object stays visible more than 1.2 seconds
  - All elements must stay within safe zone: x in [-2.5, 2.5], y in [-4.5, 4.5]
  - Use FadeIn, FadeOut, Transform, GrowArrow, Create, Write — no experimental methods
  - Valid edge constants: UP, DOWN, LEFT, RIGHT only — NEVER TOP or BOTTOM
  - BANNED classes (will crash): ParametricSurface, Surface, ThreeDScene, ThreeDAxes,
    Sphere, Cylinder, Torus, Cone — this is a 2D scene only, use Dot/Circle/Line/Arrow
  - BANNED patterns (will crash):
      self.camera.frame  — only works in MovingCameraScene, NOT Scene
      Rectangle(buff=...) — buff is not a Rectangle kwarg; use SurroundingRectangle(obj, buff=0.2)
      self.camera.animate — same, MovingCameraScene only
      obj.to_center() — does not exist; use obj.move_to(ORIGIN) or obj.center()
  - DO NOT zoom or move the camera — static camera only

CODE QUALITY:
  - Every line complete and runnable — no "# add animation here" placeholders
  - No external assets, no file I/O, no custom fonts beyond font="Monospace"
  - MANDATORY: every beat must have at least one self.play() call — self.wait() alone produces a
    static image, not a video. The scene MUST call self.play() multiple times.
  - self.wait() durations between animations must make the total sum to {total_dur}s
"""

    if previous_code and error:
        base += f"""
PREVIOUS ATTEMPT FAILED. Fix the error below and return the corrected complete script.

ERROR:
```
{error[:2000]}
```

PREVIOUS CODE:
```python
{previous_code}
```
"""

    base += (
        "\nReturn ONLY raw Python code. "
        "The very first character of your response must be the letter 'f' (from manim import config). "
        "No markdown, no fences, no explanations, no comments outside the code."
    )
    return base


def run_manim(script_path: str) -> tuple[bool, str]:
    """Run manim and stream its output live so the user sees frame progress."""
    process = subprocess.Popen(
        ["manim", "-qh", script_path, "ContentScene", "--format=mp4"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # merge stderr into stdout
        text=True,
        bufsize=1,
    )
    output_lines = []
    for line in process.stdout:
        print(line, end="", flush=True)
        output_lines.append(line)
    process.wait()

    full_output = "".join(output_lines)
    if process.returncode != 0:
        return False, full_output[-3000:]
    if "Played 0 animations" in full_output:
        return False, (
            "Scene rendered but played 0 animations — no self.play() calls were found.\n"
            "You MUST use self.play() to animate objects. self.wait() alone does NOT create video.\n"
            "Every beat requires at least one self.play() call (FadeIn, Transform, etc.)."
        )
    return True, ""


def find_rendered_mp4(script_path: str) -> str | None:
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    search_roots = [
        os.path.join(os.path.dirname(script_path), "media", "videos", script_name),
        os.path.join(os.getcwd(), "media", "videos", script_name),
    ]
    for root in search_roots:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith(".mp4"):
                    return os.path.join(dirpath, f)
    return None


def cleanup_manim_media(script_path: str):
    for search_root in [os.path.dirname(script_path), os.getcwd()]:
        media_dir = os.path.join(search_root, "media")
        if os.path.isdir(media_dir):
            shutil.rmtree(media_dir)


def main():
    with open(SCRIPT_INPUT) as f:
        script = json.load(f)

    os.makedirs(os.path.dirname(MANIM_SCRIPT_PATH), exist_ok=True)

    manim_code = None
    error = None

    for attempt in range(1, MAX_RETRIES + 1):
        # ── Step 1: Claude generates the Manim code ──────────────────────────
        with Spinner(f"Claude generating Manim scene (attempt {attempt}/{MAX_RETRIES})"):
            prompt = build_manim_prompt(script, previous_code=manim_code, error=error)
            manim_code = claude_client.call(prompt, stage="animator", max_tokens=8192)

        print(f"✓ Scene generated ({len(manim_code.splitlines())} lines)")

        manim_code = extract_python(manim_code)
        manim_code = strip_markdown_artifacts(manim_code)

        with open(MANIM_SCRIPT_PATH, "w") as f:
            f.write(manim_code)

        # ── Step 2: Manim renders the video (live output) ────────────────────
        print(f"\nRendering attempt {attempt}/{MAX_RETRIES} — frame progress below:")
        print("─" * 60)
        success, error = run_manim(MANIM_SCRIPT_PATH)
        print("─" * 60)

        if success:
            mp4 = find_rendered_mp4(MANIM_SCRIPT_PATH)
            if mp4:
                os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)
                shutil.copy2(mp4, OUTPUT_VIDEO)
                cleanup_manim_media(MANIM_SCRIPT_PATH)
                with open(RETRIES_OUTPUT, "w") as f:
                    json.dump({"attempts": attempt, "max_retries": MAX_RETRIES, "success": True}, f)
                print(f"\n✓ Video saved → {OUTPUT_VIDEO}")
                return OUTPUT_VIDEO
            error = "Manim exited 0 but no .mp4 found."

        print(f"\n✗ Attempt {attempt} failed. Last error:\n{error[:400]}\n")

    with open(RETRIES_OUTPUT, "w") as f:
        json.dump({"attempts": MAX_RETRIES, "max_retries": MAX_RETRIES, "success": False}, f)
    raise RuntimeError(f"Animator failed after {MAX_RETRIES} attempts.\nLast error:\n{error}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
