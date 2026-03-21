import json
import os
import shutil
import subprocess
import sys
import threading
import time

from pipeline import claude_client

SCRIPT_INPUT = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
MANIM_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "manim_scripts", "scene.py")
OUTPUT_VIDEO = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
MAX_RETRIES = 3


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


def build_manim_prompt(script: dict, previous_code: str = None, error: str = None) -> str:
    bullets = "\n".join(f"  - {b}" for b in script["concept_bullets"])
    base = f"""\
You are a Manim Community Edition expert. Generate a complete, runnable Manim Python script
for a 60-second portrait-format explainer video for AI engineers.

VIDEO SCRIPT:
  Hook    (0-5s):   {script['hook']}
  Concept (5-45s):
{bullets}
  Takeaway (45-55s): {script['takeaway']}
  CTA      (55-60s): {script['cta']}

TECHNICAL REQUIREMENTS:
  - Set portrait format at the TOP of the file, before any imports take effect:
      from manim import config
      config.pixel_width = 1080
      config.pixel_height = 1920
      config.frame_rate = 30
  - Background: BLACK
  - Total scene duration: approximately 60 seconds
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
  - Use self.play() and self.wait() properly to hit the 60-second target
  - Prefer FadeIn, Write, Transform — avoid experimental or version-sensitive methods
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
            manim_code = claude_client.call(prompt, stage="animator", max_tokens=8096)

        print(f"✓ Scene generated ({len(manim_code.splitlines())} lines)")

        manim_code = extract_python(manim_code)

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
