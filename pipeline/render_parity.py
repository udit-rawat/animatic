from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
VIDEO_SPEC = OUTPUT_DIR / "video_spec.json"
PRIMARY_OUTPUT = OUTPUT_DIR / "video.mp4"
REMOTION_OUTPUT = OUTPUT_DIR / "video_remotion.mp4"
HYPERFRAMES_OUTPUT = OUTPUT_DIR / "video_hyperframes.mp4"
PARITY_REPORT = OUTPUT_DIR / "render_parity_report.json"
PARITY_FRAMES = OUTPUT_DIR / "render_parity_frames"


@contextmanager
def _temporary_env(updates: dict[str, str | None]):
    original = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _load_spec_duration() -> float:
    with VIDEO_SPEC.open() as f:
        spec = json.load(f)
    return float(spec.get("timing", {}).get("total_duration_seconds", 0) or 0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ffprobe_duration(path: Path) -> float | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def _extract_sample_frames(label: str, video_path: Path, duration: float) -> list[dict]:
    if not shutil.which("ffmpeg") or duration <= 0 or not video_path.exists():
        return []

    PARITY_FRAMES.mkdir(parents=True, exist_ok=True)
    sample_points = [
        ("early", max(0.1, duration * 0.2)),
        ("mid", max(0.1, duration * 0.5)),
        ("late", max(0.1, duration * 0.8)),
    ]
    outputs: list[dict] = []
    for suffix, point in sample_points:
        frame_path = PARITY_FRAMES / f"{label}_{suffix}.jpg"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{point:.3f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    str(frame_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError:
            continue
        outputs.append(
            {
                "label": suffix,
                "time_seconds": round(point, 3),
                "path": str(frame_path),
                "sha256": _sha256(frame_path),
            }
        )
    return outputs


def _backend_summary(name: str, path: Path, spec_duration: float) -> dict:
    duration = _ffprobe_duration(path)
    return {
        "backend": name,
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "duration_seconds": duration,
        "duration_delta_vs_spec": (
            None if duration is None else round(duration - spec_duration, 3)
        ),
        "sha256": _sha256(path) if path.exists() else "",
        "sample_frames": _extract_sample_frames(name, path, duration or 0),
    }


def _render_remotion(target: Path) -> str:
    from pipeline.animator import main as remotion_main

    with _temporary_env(
        {
            "RENDER_BACKEND": "remotion",
            "ANIMATOR_OUTPUT_PATH": str(target),
            "COMPOSITOR_FILE": os.environ.get("COMPOSITOR_FILE"),
        }
    ):
        artifact = Path(str(remotion_main()))
    if artifact.suffix.lower() != ".mp4" or not artifact.exists():
        raise RuntimeError(f"Remotion parity render did not produce an MP4: {artifact}")
    return str(artifact)


def _render_hyperframes(target: Path, workdir: Path) -> str:
    from pipeline.hyper_animator import main as hyper_main

    with _temporary_env(
        {
            "ANIMATOR_OUTPUT_PATH": str(target),
            "HYPERFRAMES_WORKDIR": str(workdir),
            "HYPERFRAMES_CUSTOM_COMPOSITION": os.environ.get(
                "HYPERFRAMES_CUSTOM_COMPOSITION"
            ),
        }
    ):
        artifact = Path(str(hyper_main()))
    if artifact.suffix.lower() != ".mp4" or not artifact.exists():
        raise RuntimeError(
            f"HyperFrames parity render did not produce an MP4: {artifact}"
        )
    return str(artifact)


def main():
    if not VIDEO_SPEC.exists():
        raise RuntimeError(
            f"video_spec.json not found at {VIDEO_SPEC}. Run content_generator first."
        )

    spec_duration = _load_spec_duration()
    REMOTION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    print("[parity] Rendering Remotion output...")
    remotion_path = Path(_render_remotion(REMOTION_OUTPUT))

    print("[parity] Rendering HyperFrames output...")
    hyperframes_path = Path(
        _render_hyperframes(HYPERFRAMES_OUTPUT, OUTPUT_DIR / "hyperframes_build_parity")
    )

    remotion_summary = _backend_summary("remotion", remotion_path, spec_duration)
    hyperframes_summary = _backend_summary(
        "hyperframes", hyperframes_path, spec_duration
    )

    primary_backend = (
        os.environ.get("PARITY_PRIMARY_RENDERER", "hyperframes").strip().lower()
        or "hyperframes"
    )
    primary_path = (
        hyperframes_path if primary_backend == "hyperframes" else remotion_path
    )
    shutil.copy2(primary_path, PRIMARY_OUTPUT)

    report = {
        "spec_duration_seconds": spec_duration,
        "primary_backend": primary_backend,
        "primary_output_path": str(PRIMARY_OUTPUT),
        "backends": {
            "remotion": remotion_summary,
            "hyperframes": hyperframes_summary,
        },
        "comparisons": {
            "duration_delta_seconds": (
                None
                if remotion_summary["duration_seconds"] is None
                or hyperframes_summary["duration_seconds"] is None
                else round(
                    remotion_summary["duration_seconds"]
                    - hyperframes_summary["duration_seconds"],
                    3,
                )
            ),
            "size_delta_bytes": remotion_summary["size_bytes"]
            - hyperframes_summary["size_bytes"],
        },
    }

    with PARITY_REPORT.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"[parity] Report written → {PARITY_REPORT}")
    print(f"[parity] Primary video copied → {PRIMARY_OUTPUT}")
    return str(PARITY_REPORT)


if __name__ == "__main__":
    main()
