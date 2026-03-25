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
for a 60-second portrait-format Instagram video for AI engineers.

{script_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COPY THESE CONSTANTS VERBATIM — do not rename or change values:

  # Script text (rendered large on screen — not stage directions)
  HOOK_TEXT      = "{hook_text}"
  CONCEPT_1_TEXT = "{concept_1_text}"
  CONCEPT_2_TEXT = "{concept_2_text}"
  TAKEAWAY_TEXT  = "{takeaway_text}"

  # Colors
  C_WHITE  = "#FDFDFD"
  C_GREEN  = "#00FF41"
  C_CYAN   = "#00E5FF"
  C_YELLOW = "#FFD600"

  # Font sizes — use these names, never numeric literals
  FS_HOOK    = 64
  FS_CONCEPT = 56
  FS_LABEL   = 52
  FS_TAKEWAY = 60

  # Y anchors — portrait frame is 7.1 wide × 12.6 tall
  Y_TOP    =  5.2
  Y_UPPER  =  2.8
  Y_CENTER =  0.0
  Y_LOWER  = -2.8
  Y_BOTTOM = -5.2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DESIGN PHILOSOPHY — read before writing a single line:
  The animation must be TOPIC-SPECIFIC. Look at the script content above.
  Design visuals that make sense for THAT topic — not a generic dot grid.

  Examples of topic-driven visuals:
    memory leak topic   → a bar chart that grows unbounded, then flatlines after the fix
    attention mechanism → a matrix with highlighted cells showing attention weights
    gradient descent    → a loss curve descending, animated step by step
    tokenization        → words splitting into sub-word tokens, color-coded
    model compression   → a large shape shrinking while keeping its structure
    benchmark results   → two bars side by side, one clearly taller

  EVERY BEAT must use a different visual primitive — do not repeat the same shape.
  Use the FULL vertical canvas: place elements at Y_TOP, Y_UPPER, Y_CENTER, Y_LOWER, Y_BOTTOM.
  Beat 3 (contrast) MUST show a BEFORE/AFTER or OLD/NEW split — left=C_CYAN, right=C_GREEN,
  labels in C_YELLOW.

BEAT STRUCTURE — timing must match narration timecodes above:
  Beat 1 (hook):     Large HOOK_TEXT at Y_TOP in C_WHITE. Topic-specific visual below it.
  Beat 2 (mechanism): CONCEPT_1_TEXT at Y_UPPER in C_YELLOW. Animate the mechanism.
  Beat 3 (contrast):  Split screen — BEFORE (left, C_CYAN) vs AFTER (right, C_GREEN).
                      CONCEPT_2_TEXT at Y_LOWER in C_WHITE.
  Beat 4 (takeaway):  Clear screen. TAKEAWAY_TEXT at Y_UPPER in C_WHITE. One strong visual.

TECHNICAL REQUIREMENTS:
  - Portrait config (copy verbatim, BEFORE any other import):
      from manim import config
      config.pixel_width  = 1080
      config.pixel_height = 1920
      config.frame_rate   = 30
  - Total duration: exactly {total_dur} seconds
  - Class name: ContentScene(Scene)
  - Imports: from manim import * and import numpy as np only
  - x safe zone: [-2.8, 2.8]   y safe zone: [-5.5, 5.5]
  - Valid directions: UP, DOWN, LEFT, RIGHT — never TOP, BOTTOM, FRONT, BACK
  - ALL text: Text(font="Monospace") — NO Tex(), NO MathTex(), NO LaTeX

BANNED (crashes Manim CE 0.20 — do not use):
  ParametricSurface, Surface, ThreeDScene, ThreeDAxes, Sphere, Cylinder
  self.camera.frame, self.camera.animate
  Rectangle(buff=...)  → use SurroundingRectangle(obj, buff=0.2)
  obj.to_center()      → use obj.move_to(ORIGIN)
  obj.scale_to_fit_width() → use obj.scale(factor)

MANDATORY:
  - Every beat ≥ 3 self.play() calls — self.wait() alone = static PNG, not video
  - Use FS_HOOK / FS_CONCEPT / FS_LABEL / FS_TAKEWAY — never raw numbers for font_size
  - Use C_WHITE / C_GREEN / C_CYAN / C_YELLOW — never raw hex strings
  - Complete runnable code — no placeholders, no ellipsis, no TODO comments
  - No file I/O, no external assets
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
    """Run manim with a single progress bar — one bar across all animations."""
    import re
    process = subprocess.Popen(
        ["manim", "-qh", script_path, "ContentScene", "--format=mp4"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_lines = []
    total = None
    current = 0

    bar_width = 40
    def _draw(n, t, label=""):
        filled = int(bar_width * n / t) if t else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        pct = int(100 * n / t) if t else 0
        sys.stdout.write(f"\r  Rendering  [{bar}]  {pct}%  anim {n}/{t}  {label[:30]:<30}")
        sys.stdout.flush()

    for line in process.stdout:
        output_lines.append(line)
        # Manim prints "Animation N :" lines — use them to drive the bar
        m = re.search(r"Animation\s+(\d+)\s*:", line)
        if m:
            current = int(m.group(1))
            # First time we see an animation number, peek ahead for total from
            # "Played N animations" — but we don't have it yet, so use current
            # as a lower bound and show indeterminate if total unknown
            if total is None:
                total = current + 5   # optimistic placeholder
            total = max(total, current)
            _draw(current, total)
        # "Played N animations" appears at the end — use for final bar
        m2 = re.search(r"Played\s+(\d+)\s+animations", line)
        if m2:
            total = int(m2.group(1))
            _draw(total, total, "done")

    process.wait()
    sys.stdout.write("\n")
    sys.stdout.flush()

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

        # ── Step 2: Manim renders the video ──────────────────────────────────
        print(f"\nRendering attempt {attempt}/{MAX_RETRIES}...")
        success, error = run_manim(MANIM_SCRIPT_PATH)

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
