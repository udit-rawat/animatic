from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_spec(path: str | Path) -> dict[str, Any]:
    spec_path = resolve_path(path)
    with spec_path.open() as f:
        spec = json.load(f)
    spec["_spec_path"] = str(spec_path)
    validate_spec(spec)
    return spec


def validate_spec(spec: dict[str, Any]) -> None:
    required = ["slug", "duration", "fps", "composition_dir", "output_file", "segments"]
    missing = [key for key in required if key not in spec]
    if missing:
        raise ValueError(f"spec missing required keys: {', '.join(missing)}")

    if not isinstance(spec["segments"], list) or not spec["segments"]:
        raise ValueError("spec.segments must be a non-empty list")

    duration = float(spec["duration"])
    if duration <= 0:
        raise ValueError("spec.duration must be positive")

    seen: set[str] = set()
    for index, segment in enumerate(spec["segments"], 1):
        for key in ["id", "start", "duration", "text"]:
            if key not in segment:
                raise ValueError(f"segment {index} missing {key}")
        sid = str(segment["id"])
        if sid in seen:
            raise ValueError(f"duplicate segment id: {sid}")
        seen.add(sid)
        start = float(segment["start"])
        seg_duration = float(segment["duration"])
        if start < 0 or seg_duration <= 0:
            raise ValueError(f"segment {sid} has invalid timing")
        if start + seg_duration > duration + 0.05:
            raise ValueError(f"segment {sid} exceeds total duration")


def composition_dir(spec: dict[str, Any]) -> Path:
    return resolve_path(spec["composition_dir"])


def output_file(spec: dict[str, Any]) -> Path:
    return resolve_path(spec["output_file"])


def cache_dir(spec: dict[str, Any], namespace: str) -> Path:
    return ROOT / "cache" / namespace / str(spec["slug"])
