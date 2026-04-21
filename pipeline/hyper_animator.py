"""
hyper_animator.py — HyperFrames execution bridge.

Phase 4 behavior:
  1. Load output/video_spec.json
  2. Build a standalone HyperFrames composition bundle
  3. If HYPERFRAMES_RENDER_CMD is configured, execute it
  4. Otherwise leave a ready-to-render package in output/hyperframes_build/

This does not replace the live Remotion backend by default.
"""

from __future__ import annotations

import os
from pathlib import Path

from renderers.hyperframes.runner import HyperFramesRenderConfig, render

_ROOT = Path(__file__).resolve().parent.parent
VIDEO_SPEC = _ROOT / "output" / "video_spec.json"
OUTPUT_VIDEO = _ROOT / "output" / "video.mp4"
WORKDIR = _ROOT / "output" / "hyperframes_build"


def main():
    if not VIDEO_SPEC.exists():
        raise RuntimeError(
            f"video_spec.json not found at {VIDEO_SPEC}. Run content_generator first."
        )

    mode = os.environ.get("HYPERFRAMES_MODE", "auto").strip() or "auto"
    render_command = os.environ.get("HYPERFRAMES_RENDER_CMD", "").strip()
    output_video = Path(os.environ.get("ANIMATOR_OUTPUT_PATH", str(OUTPUT_VIDEO)))
    working_dir = Path(os.environ.get("HYPERFRAMES_WORKDIR", str(WORKDIR)))
    custom_entry = os.environ.get("HYPERFRAMES_CUSTOM_COMPOSITION", "").strip()
    config = HyperFramesRenderConfig(
        spec_path=VIDEO_SPEC,
        output_path=output_video,
        working_dir=working_dir,
        mode=mode,
        render_command=render_command,
        entry_html_path=Path(custom_entry) if custom_entry else None,
    )
    artifact = render(config)

    if artifact.suffix.lower() == ".mp4":
        size_mb = artifact.stat().st_size / 1_000_000 if artifact.exists() else 0
        print(f"✓ HyperFrames video saved → {artifact}  ({size_mb:.1f} MB)")
        return str(artifact)

    print(f"✓ HyperFrames package written → {working_dir}")
    print(f"  Entrypoint: {artifact}")
    if not render_command:
        print("  No HYPERFRAMES_RENDER_CMD configured — package mode only.")
        print("  Set HYPERFRAMES_RENDER_CMD with placeholders like:")
        print("    {html}   HTML entrypoint")
        print("    {output} output video path")
        print("    {workdir} package dir")
        print("    {spec}   video_spec path")
    return str(artifact)


if __name__ == "__main__":
    main()
