import json
import os
import shutil
import subprocess
import sys
import threading
import time

from pipeline import claude_client

SCRIPT_INPUT  = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TIMING_INPUT  = os.path.join(os.path.dirname(__file__), "..", "output", "narration_timing.json")
MANIM_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "manim_scripts", "scene.py")
OUTPUT_VIDEO  = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
MAX_RETRIES   = 3


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
        f"  Takeaway+CTA {tc('takeaway_cta')}: {script['takeaway']} / {script['cta']}\n"
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
for a portrait-format explainer video for AI engineers.

{script_block}
TECHNICAL REQUIREMENTS:
  - Set portrait format at the TOP of the file, before any imports take effect:
      from manim import config
      config.pixel_width = 1080
      config.pixel_height = 1920
      config.frame_rate = 30
  - Background: BLACK
  - Total scene duration: approximately {total_dur} seconds (match narration length)
  - Class name: ContentScene (inherits from Scene)
  - Use only standard Manim CE imports (manim, numpy)
  - ONLY use Text() for all text — never use Tex(), MathTex(), or any LaTeX-based objects
  - Clean typography: large readable text, generous spacing, no overcrowding
  - Minimal, purposeful animations — no gratuitous effects
  - Each section of the script gets its own visual segment
  - All text must fit within safe margins for portrait (avoid edges)

CODE QUALITY:
  - Every line must be complete and runnable — no placeholder comments like "# add animation here"
  - No external assets, no custom fonts, no file I/O
  - Use self.play() and self.wait() properly to hit the {total_dur}-second target
  - Prefer FadeIn, Write, Transform — avoid experimental or version-sensitive methods
  - Valid edge constants: UP, DOWN, LEFT, RIGHT — NEVER use TOP or BOTTOM (they don't exist in Manim)
  - to_edge() accepts UP/DOWN/LEFT/RIGHT only
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

    if process.returncode != 0:
        return False, "".join(output_lines[-60:])
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
            manim_code = claude_client.call(prompt, stage="animator", max_tokens=4096)

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
                print(f"\n✓ Video saved → {OUTPUT_VIDEO}")
                return OUTPUT_VIDEO
            error = "Manim exited 0 but no .mp4 found."

        print(f"\n✗ Attempt {attempt} failed. Last error:\n{error[:400]}\n")

    raise RuntimeError(f"Animator failed after {MAX_RETRIES} attempts.\nLast error:\n{error}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
