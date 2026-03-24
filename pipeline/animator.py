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
            f"  Takeaway (45-60s): {script['takeaway']}\n"
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
        f"  Takeaway {tc('takeaway_cta')}: {script['takeaway']}\n"
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

    hook_text      = script.get("hook", "")[:80]
    concept_1_text = script["concept_bullets"][0][:80] if script.get("concept_bullets") else ""
    concept_2_text = script["concept_bullets"][1][:80] if len(script.get("concept_bullets", [])) > 1 else ""
    takeaway_text  = script.get("takeaway", "")[:80]

    base = f"""\
You are a Manim Community Edition expert. Generate a complete, runnable Manim Python script
for a portrait-format Instagram dopamine-loop video for AI engineers.

{script_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COPY THESE CONSTANTS VERBATIM at the top of your script, inside the class or before it:

  # --- Script content ---
  HOOK_TEXT      = "{hook_text}"
  CONCEPT_1_TEXT = "{concept_1_text}"
  CONCEPT_2_TEXT = "{concept_2_text}"
  TAKEAWAY_TEXT  = "{takeaway_text}"

  # --- Color palette (DO NOT change these hex values) ---
  C_WHITE  = "#FDFDFD"   # hook text, takeaway text, body copy
  C_GREEN  = "#00FF41"   # AFTER side dots/lines, highlights, arrow
  C_CYAN   = "#00E5FF"   # BEFORE side dots/lines
  C_YELLOW = "#FFD600"   # section labels (BEFORE / AFTER), concept headers

  # --- Font sizes (DO NOT use numeric literals — always use these names) ---
  FS_HOOK     = 64   # hook text
  FS_CONCEPT  = 56   # concept bullets
  FS_LABEL    = 52   # BEFORE / AFTER labels
  FS_TAKEWAY  = 60   # takeaway text

  # --- Exact Y anchors (portrait frame: 7.1 wide x 12.6 tall) ---
  Y_TOP    =  5.2   # hook text baseline
  Y_UPPER  =  2.8   # concept 1 text / BEFORE-AFTER labels
  Y_CENTER =  0.0   # divider line / dot grid center
  Y_LOWER  = -2.8   # concept 2 text
  Y_BOTTOM = -5.2   # takeaway text baseline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALL text: Text(font="Monospace") — NO Tex(), NO MathTex(), NO LaTeX
Background: BLACK (#000000)

SCENE STRUCTURE — beat by beat:

  Beat 1 — Hook (0s–10s):
    • self.play(FadeIn(Text(HOOK_TEXT, font_size=FS_HOOK, color=C_WHITE,
        font="Monospace", width=6.0).move_to(UP * Y_TOP)))
    • Simultaneously FadeIn ~60 Dot objects (radius=0.09, color=C_GREEN) scattered
      randomly: x in [-2.5, 2.5], y in [-2.5, 2.5] (CENTER zone only — keep top clear for text)
    • self.wait(4)
    • self.play(Transform all dots → ordered 8×8 grid centered at [0, Y_CENTER])
    • self.play(FadeOut hook text)   ← separate play call

  Beat 2 — Collapse (10s–25s):
    • self.play(FadeIn(Text(CONCEPT_1_TEXT, font_size=FS_CONCEPT, color=C_YELLOW,
        font="Monospace", width=5.5).move_to(UP * Y_UPPER)))
    • self.play(Transform dot grid → tighter 6×6 grid, scale each dot by 0.7)
    • self.wait(3)
    • self.play(Create 3 Line objects connecting grid dots, stroke_width=3, color=C_GREEN)
    • self.play(FadeOut concept text)

  Beat 3 — Contrast (25s–45s):
    • self.play(FadeOut all remaining dots and lines)
    • self.play(Create(Line(start=UP*5.0, end=DOWN*5.0, color=C_WHITE, stroke_width=2).move_to(ORIGIN)))
    • LEFT side (x < 0): self.play(FadeIn ~12 Dots in a 3×4 rigid grid, color=C_CYAN,
        x in [-2.5, -0.3], y in [-2.0, 2.0], then Create 4 straight Lines between them, color=C_CYAN)
    • RIGHT side (x > 0): self.play(FadeIn ~12 Dots in loose positions, color=C_GREEN,
        x in [0.3, 2.5], y in [-2.0, 2.0], then Create 3 ArcBetweenPoints arcs, color=C_GREEN)
    • BEFORE label: self.play(FadeIn(Text("BEFORE", font_size=FS_LABEL, color=C_YELLOW,
        font="Monospace").move_to(LEFT*1.5 + UP*Y_UPPER)))
    • AFTER label:  self.play(FadeIn(Text("AFTER",  font_size=FS_LABEL, color=C_YELLOW,
        font="Monospace").move_to(RIGHT*1.5 + UP*Y_UPPER)))
    • self.play(FadeIn(Text(CONCEPT_2_TEXT, font_size=FS_CONCEPT, color=C_WHITE,
        font="Monospace", width=5.5).move_to(UP * Y_LOWER)))
    • self.wait(4)

  Beat 4 — Takeaway (45s–{total_dur}s):
    • self.play(FadeOut *everything* on screen)
    • self.play(FadeIn(Text(TAKEAWAY_TEXT, font_size=FS_TAKEWAY, color=C_WHITE,
        font="Monospace", width=5.8).move_to(UP * 1.5)))
    • self.play(GrowArrow(Arrow(LEFT*2.5, RIGHT*2.5, color=C_GREEN, stroke_width=8)
        .move_to(UP * Y_CENTER)))
    • self.wait(5)
    • self.play(FadeOut *everything*)

TECHNICAL REQUIREMENTS:
  - Portrait config (copy verbatim, before any other import):
      from manim import config
      config.pixel_width  = 1080
      config.pixel_height = 1920
      config.frame_rate   = 30
  - Total duration: exactly {total_dur} seconds
  - Class name: ContentScene(Scene)
  - Imports: from manim import * and import numpy as np only
  - x safe zone: [-2.8, 2.8]   y safe zone: [-5.5, 5.5]
  - Valid directions: UP, DOWN, LEFT, RIGHT — never TOP, BOTTOM, FRONT, BACK

BANNED (will crash — do not use):
  ParametricSurface, Surface, ThreeDScene, ThreeDAxes, Sphere, Cylinder
  self.camera.frame, self.camera.animate  (MovingCameraScene only)
  Rectangle(buff=...)  (use SurroundingRectangle(obj, buff=0.2) instead)
  obj.to_center()      (use obj.move_to(ORIGIN) or obj.center() instead)
  obj.scale_to_fit_width()  (use obj.width = X or obj.scale(X) instead)

MANDATORY RULES:
  - Every beat MUST have ≥ 3 self.play() calls — self.wait() alone = static PNG not video
  - NEVER use numeric literals for font_size — always use FS_HOOK, FS_CONCEPT, FS_LABEL, FS_TAKEWAY
  - NEVER use "#00FF41" directly — always use C_GREEN, C_CYAN, C_YELLOW, C_WHITE
  - Every line must be complete and runnable — no placeholders, no ellipsis
  - No file I/O, no external assets, no custom fonts beyond font="Monospace"
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
