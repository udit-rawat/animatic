from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime

VIDEO_SPEC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "output", "video_spec.json"
)
FPS = 30
WIDTH = 1080
HEIGHT = 1920

_SEGMENT_ORDER = ["hook", "concept_1", "concept_2", "takeaway_cta"]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80] or "video"


def _provider_name() -> str:
    return os.environ.get("FORCE_PROVIDER", "claude")


def _estimate_timing(spoken: dict, fps: int = FPS) -> dict:
    """
    Temporary timing before narrator.py writes exact durations.
    Estimate at ~1.4 words/s plus a small pause budget so downstream tools
    can already build a stable video_spec.json during content generation.
    """
    cursor = 0.0
    segments: dict[str, dict] = {}
    for key in _SEGMENT_ORDER:
        text = (spoken.get(key) or "").strip()
        words = len(text.split())
        duration = max(1.5, round((words / 1.4) + 0.35, 3))
        segments[key] = {
            "start": round(cursor, 3),
            "duration": duration,
            "end": round(cursor + duration, 3),
            "text": text,
        }
        cursor += duration
    total_frames = math.ceil(cursor * fps) + fps
    return {
        "segments": segments,
        "total_duration_seconds": round(cursor, 3),
        "total_frames": total_frames,
    }


def _segment_ref_for_beat(index: int, total_beats: int) -> str:
    if index == 1:
        return "hook"
    if index == total_beats:
        return "takeaway_cta"
    return f"concept_{index - 1}"


def _scene_for_beat(beat_id: str, payload: dict) -> dict:
    data = payload.get("data", {})
    return {
        "kind": "template",
        "template_id": data.get("layout", "MetricFocus"),
        "config": payload,
    }


def _beat_text_frame(index: int, payload: dict) -> int:
    data = payload.get("data", {})
    layout = data.get("layout", "")
    if index == 1:
        return 1
    if layout == "TakeawayScene":
        return 1
    if payload.get("animate_in") == "fade":
        return 6
    return 8


def build_video_spec(
    *,
    topic: dict,
    script: dict,
    spoken: dict,
    params: dict,
    scene_plan: dict,
    cues: dict,
    timing: dict | None = None,
    audio_src: str = "",
) -> dict:
    timing_block = (
        _estimate_timing(spoken)
        if timing is None
        else {
            "segments": timing,
            "total_duration_seconds": round(
                max((v.get("end", 0) for v in timing.values()), default=0), 3
            ),
            "total_frames": math.ceil(
                max((v.get("end", 0) for v in timing.values()), default=0) * FPS
            )
            + FPS,
        }
    )

    beats_cfg = scene_plan.get("beats", [])
    total_beats = len(beats_cfg)
    beats: list[dict] = []

    for beat_meta in beats_cfg:
        index = int(beat_meta["beat"])
        beat_id = f"beat_{index}"
        payload = params.get(beat_id, {})
        segment_ref = _segment_ref_for_beat(index, total_beats)
        timing_entry = timing_block["segments"].get(
            segment_ref, {"start": 0, "duration": 3, "end": 3}
        )
        beats.append(
            {
                "id": beat_id,
                "index": index,
                "segment_ref": segment_ref,
                "start_frame": round(timing_entry["start"] * FPS),
                "duration_frames": max(1, round(timing_entry["duration"] * FPS)),
                "text_frame": _beat_text_frame(index, payload),
                "layout_mode": "full_scene",
                "scene": _scene_for_beat(beat_id, payload),
                "cue_labels": (
                    [f"{segment_ref}_start"]
                    if segment_ref != "takeaway_cta"
                    else ["takeaway_start"]
                ),
                "notes": [f"legacy_template={beat_meta.get('template', 'unknown')}"],
            }
        )

    return {
        "version": "1.0",
        "meta": {
            "project": "adamax-content-engine",
            "pipeline_mode": "custom",
            "renderer_target": "neutral",
            "generator_provider": _provider_name(),
            "fps": FPS,
            "width": WIDTH,
            "height": HEIGHT,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "topic_slug": _slugify(topic.get("title", "video")),
        },
        "topic": {
            "title": topic.get("title", ""),
            "summary": topic.get("summary", ""),
            "source": topic.get("source", "custom"),
            "url": topic.get("url", ""),
            "why_picked": topic.get("why_picked", ""),
        },
        "narration": {
            "segments": spoken,
            "tone": os.environ.get("NARRATOR_TONE_OVERRIDE", ""),
            "caption": script.get("caption", ""),
            "hashtags": script.get("hashtags", []),
        },
        "timing": timing_block,
        "cues": cues,
        "beats": beats,
        "delivery": {
            "notify": True,
            "telegram": True,
        },
        "assets": {
            "audio_src": audio_src,
            "voice_name": os.environ.get("TTS_VOICE", "Aoede"),
            "external_clips": [],
        },
        "notes": [
            "Phase 1 dual-write contract.",
            "Remotion artifacts are currently derived from this spec.",
        ],
    }


def write_video_spec(spec: dict, path: str = VIDEO_SPEC_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)


def load_video_spec(path: str = VIDEO_SPEC_PATH) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def update_video_spec_timing(
    timing: dict,
    *,
    audio_src: str = "narration.wav",
    path: str = VIDEO_SPEC_PATH,
) -> dict | None:
    spec = load_video_spec(path)
    if not spec:
        return None

    spec["timing"] = {
        "segments": timing,
        "total_duration_seconds": round(
            max((v.get("end", 0) for v in timing.values()), default=0), 3
        ),
        "total_frames": math.ceil(
            max((v.get("end", 0) for v in timing.values()), default=0) * FPS
        )
        + FPS,
    }

    spec.setdefault("assets", {})
    spec["assets"]["audio_src"] = audio_src

    for beat in spec.get("beats", []):
        seg = beat.get("segment_ref")
        if seg in timing:
            beat["start_frame"] = round(timing[seg]["start"] * FPS)
            beat["duration_frames"] = max(1, round(timing[seg]["duration"] * FPS))

    write_video_spec(spec, path)
    return spec
