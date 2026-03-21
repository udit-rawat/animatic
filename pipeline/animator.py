import json
import os
import shutil
import subprocess

from pipeline import claude_client

SCRIPT_INPUT = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
MANIM_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "manim_scripts", "scene.py")
OUTPUT_VIDEO = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
MAX_RETRIES = 3


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

    base += "\nReturn ONLY the Python code. No markdown fences, no explanations."
    return base


def run_manim(script_path: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["manim", "-qh", script_path, "ContentScene", "--format=mp4"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, result.stderr + "\n" + result.stdout
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
    """Remove the manim-generated media/ folder to keep only video.mp4."""
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
        print(f"Generating Manim scene (attempt {attempt}/{MAX_RETRIES})...")
        prompt = build_manim_prompt(script, previous_code=manim_code, error=error)
        manim_code = claude_client.call(prompt, stage="animator", max_tokens=8096)

        # Strip markdown fences if Claude wrapped the code anyway
        if "```" in manim_code:
            lines = manim_code.splitlines()
            manim_code = "\n".join(l for l in lines if not l.startswith("```"))

        with open(MANIM_SCRIPT_PATH, "w") as f:
            f.write(manim_code)

        print(f"Rendering (attempt {attempt})...")
        success, error = run_manim(MANIM_SCRIPT_PATH)

        if success:
            mp4 = find_rendered_mp4(MANIM_SCRIPT_PATH)
            if mp4:
                os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)
                shutil.copy2(mp4, OUTPUT_VIDEO)
                cleanup_manim_media(MANIM_SCRIPT_PATH)
                print(f"Video saved → {OUTPUT_VIDEO}")
                return OUTPUT_VIDEO
            error = "Manim exited 0 but no .mp4 found."

        print(f"Attempt {attempt} failed:\n{error[:400]}")

    raise RuntimeError(f"Animator failed after {MAX_RETRIES} attempts.\nLast error:\n{error}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
