#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.reel_spec import cache_dir, composition_dir, load_spec, output_file


def _hyperframes_command() -> list[str]:
    hyperframes = shutil.which("hyperframes")
    if hyperframes:
        return [hyperframes, "render"]

    candidates = sorted(
        Path.home().glob(".npm/_npx/*/node_modules/hyperframes/dist/cli.js"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return ["node", str(candidates[0]), "render"]

    npx = shutil.which("npx")
    if npx:
        return [npx, "hyperframes", "render"]

    raise RuntimeError("HyperFrames CLI not found. Install or run it once through npx.")


def render(spec_path: str, dry_run: bool = False) -> Path:
    spec = load_spec(spec_path)
    comp_dir = composition_dir(spec)
    out_path = output_file(spec)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    render_cfg = spec.get("render", {})
    fps = int(spec["fps"])
    quality = str(render_cfg.get("quality", "high"))
    crf = int(render_cfg.get("crf", 6))
    workers = int(render_cfg.get("workers", 1))
    duration = str(float(spec["duration"])).rstrip("0").rstrip(".")
    work_dir = cache_dir(spec, "render_work")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    shutil.copytree(comp_dir, work_dir)

    index_path = work_dir / "index.html"
    html = index_path.read_text()
    html = re.sub(r'data-duration="[^"]+"', f'data-duration="{duration}"', html)
    audio_file = spec.get("audio_file")
    if audio_file:
        html = re.sub(r'src="narration_[ab]\.wav"', f'src="{audio_file}"', html)
        html = re.sub(r'src="narration\.wav"', f'src="{audio_file}"', html)
    index_path.write_text(html)

    command = [
        *_hyperframes_command(),
        str(work_dir),
        "-o",
        str(out_path),
        "-f",
        str(fps),
        "-q",
        quality,
        "--crf",
        str(crf),
        "--workers",
        str(workers),
    ]
    print("Running:", " ".join(command))
    if dry_run:
        print(f"Dry run only. Prepared workdir -> {work_dir}")
        return out_path
    subprocess.run(command, check=True)
    print(f"Rendered -> {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a HyperFrames reel from a spec.")
    parser.add_argument("--spec", default="reels/current/spec.json", help="Path to reel spec JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare and print the render command without running it.")
    args = parser.parse_args()
    render(args.spec, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
