"""
brief_generator.py — Phase 2 of Path 2 animation pipeline.

Reads:
  output/params.json            — beat layouts (template per beat)
  output/narration_timing.json  — per-segment start/end/duration in seconds
  cue_definitions.json          — word-level animation triggers

Outputs:
  output/animation_brief.json   — per-beat animation spec (frames, primitives, rules)
  output/compositor_prompt.md   — ready-to-paste Claude prompt for this session

Hard rules enforced in code (not prompts):
  1. Beat 0 text at frame 1 — no intro, no logo, no blank screen
  2. Every beat has >= 2 animation events spaced 45-90 frames apart
  3. Winning side of ComparisonSplit always gets pulse_frames
  4. PipelineFlow steps light up sequentially timed to narration
  5. TerminalScene + PipelineFlow beat gets pulse on key command/step
  6. Last beat (TakeawayScene) CTA locks to one of 4 BRIEF_V4 options
  7. No beat exceeds its narration duration in frames
"""

import json
import os
import math
import re

from pipeline.video_spec import load_video_spec

_ROOT = os.path.join(os.path.dirname(__file__), "..")
PARAMS_PATH = os.path.join(_ROOT, "output", "params.json")
TIMING_PATH = os.path.join(_ROOT, "output", "narration_timing.json")
CUES_PATH = os.path.join(_ROOT, "cue_definitions.json")
TOPIC_PATH = os.path.join(_ROOT, "output", "topic.json")
SPOKEN_PATH = os.path.join(_ROOT, "output", "spoken_narration.json")
BRIEF_OUT = os.path.join(_ROOT, "output", "animation_brief.json")
PROMPT_OUT = os.path.join(_ROOT, "output", "compositor_prompt.md")
DROP_PATH_OUT = os.path.join(_ROOT, "output", "drop_path.txt")
HYPER_BRIEF_OUT = os.path.join(_ROOT, "output", "hyperframes_custom_brief.json")
HYPER_PROMPT_OUT = os.path.join(_ROOT, "output", "hyperframes_compositor_prompt.md")
HYPER_DROP_PATH_OUT = os.path.join(_ROOT, "output", "hyperframes_drop_path.txt")
HYPER_SCENE_SPEC_OUT = os.path.join(_ROOT, "output", "hyperframes_scene_spec.json")

FPS = 30

# Map narration segment keys → beat keys (beat_1 = hook, beat_2 = concept_1, etc.)
SEGMENT_ORDER = [
    "hook",
    "concept_1",
    "concept_2",
    "concept_3",
    "concept_4",
    "takeaway_cta",
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def sec_to_frames(sec: float) -> int:
    return round(sec * FPS)


def frames_in_beat(beat_key: str, timing: dict, beat_keys: list[str]) -> int:
    """Duration of this beat in frames from narration_timing.json."""
    idx = beat_keys.index(beat_key)
    seg = SEGMENT_ORDER[idx] if idx < len(SEGMENT_ORDER) else None
    if seg and seg in timing:
        return sec_to_frames(timing[seg]["duration"])
    # Fallback: 90 frames (3s)
    return 90


def global_frame_start(beat_key: str, beat_keys: list[str], timing: dict) -> int:
    """Absolute frame where this beat starts (sum of all prior beat durations)."""
    idx = beat_keys.index(beat_key)
    total = 0
    for i in range(idx):
        total += frames_in_beat(beat_keys[i], timing, beat_keys)
    return total


# ── Per-layout animation spec builders ───────────────────────────────────────


def spec_statement_slam(
    beat_key: str, data: dict, duration: int, is_first: bool
) -> dict:
    """StatementSlam: lines stagger in, line 0 glows. First beat = text at frame 1."""
    lines = data.get("lines", [])
    events = []

    # Rule 1: first beat text at frame 1
    first_frame = 1 if is_first else 6

    for i, line in enumerate(lines):
        enter = first_frame + i * 18
        events.append(
            {
                "type": "slide_in",
                "target": f"line_{i}",
                "direction": "up",
                "frame": enter,
            }
        )
        if i == 0:
            # Glow pulse on line 0 at frame 45 and 90
            for pf in [45, 90]:
                if pf < duration:
                    events.append(
                        {
                            "type": "pulse",
                            "target": "line_0",
                            "frame": pf,
                            "color": data.get("accent_color", "cyan"),
                        }
                    )

    return {
        "template": "StatementSlam",
        "duration": duration,
        "text_frame": first_frame,
        "events": events,
        "note": "Line 0 glows — accent color. Stagger 18f between lines.",
    }


def spec_metric_focus(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """MetricFocus: hero counts up, chips slide in, pulse at 60f."""
    first_frame = 1 if is_first else 8
    events = [
        {"type": "count_up", "target": "hero_value", "frame": first_frame},
        {
            "type": "slide_in",
            "target": "context",
            "direction": "up",
            "frame": first_frame + 20,
        },
    ]
    chips = data.get("chips", [])
    for i in range(len(chips)):
        events.append(
            {
                "type": "slide_in",
                "target": f"chip_{i}",
                "direction": "up",
                "frame": first_frame + 36 + i * 14,
            }
        )

    pulse_f = 60
    if pulse_f < duration:
        events.append(
            {
                "type": "pulse",
                "target": "hero_value",
                "frame": pulse_f,
                "color": data.get("hero", {}).get("color", "cyan"),
            }
        )

    return {
        "template": "MetricFocus",
        "duration": duration,
        "text_frame": first_frame,
        "events": events,
        "note": "Hero counts up from 0. Pulse at 60f reinforces the number.",
    }


def spec_comparison_split(
    beat_key: str, data: dict, duration: int, is_first: bool
) -> dict:
    """ComparisonSplit: left slides in, right slides in 14f later, winning side pulses."""
    first_frame = 1 if is_first else 6
    right_color = data.get("right", {}).get("color", "green")

    events = [
        {
            "type": "slide_in",
            "target": "panel_left",
            "direction": "left",
            "frame": first_frame,
        },
        {
            "type": "slide_in",
            "target": "panel_right",
            "direction": "right",
            "frame": first_frame + 14,
        },
    ]

    # Rule 3: winning side (right) always gets pulse events every ~45f
    pulse_frames = []
    pf = first_frame + 30
    while pf < duration:
        pulse_frames.append(pf)
        pf += 45

    if pulse_frames:
        events.append(
            {
                "type": "pulse",
                "target": "panel_right",
                "frames": pulse_frames,
                "color": right_color,
            }
        )

    # Highlight winning metrics
    right_metrics = data.get("right", {}).get("metrics", [])
    for i, m in enumerate(right_metrics):
        hf = first_frame + 30 + i * 16
        if hf < duration:
            events.append(
                {"type": "highlight", "target": f"right_metric_{i}", "frame": hf}
            )

    return {
        "template": "ComparisonSplit",
        "duration": duration,
        "text_frame": first_frame,
        "winning_side": "right",
        "pulse_frames": pulse_frames,
        "events": events,
        "note": "Right panel = winner. Pulse every 45f. Metrics highlight sequentially.",
    }


def spec_pipeline_flow(
    beat_key: str, data: dict, duration: int, is_first: bool
) -> dict:
    """PipelineFlow: steps light up sequentially, timed to narration words."""
    first_frame = 1 if is_first else 8
    steps = data.get("steps", [])
    n = len(steps)
    events = []

    # Space step activations evenly across beat duration
    spacing = max(20, (duration - first_frame - 20) // max(n, 1))
    for i, step in enumerate(steps):
        activate_f = first_frame + i * spacing
        events.append(
            {
                "type": "activate_step",
                "target": f"step_{i}",
                "label": step.get("label", ""),
                "frame": activate_f,
            }
        )
        if step.get("state") == "bottleneck":
            events.append(
                {
                    "type": "pulse",
                    "target": f"step_{i}",
                    "frame": activate_f + 8,
                    "color": "red",
                }
            )

    return {
        "template": "PipelineFlow",
        "duration": duration,
        "text_frame": first_frame,
        "events": events,
        "note": f"Steps activate sequentially every ~{spacing}f. Bottleneck gets red pulse.",
    }


def spec_terminal_scene(
    beat_key: str, data: dict, duration: int, is_first: bool
) -> dict:
    """TerminalScene: window slides up, lines type in, key command gets pulse."""
    first_frame = 1 if is_first else 6
    lines = data.get("lines", [])

    # Find the key command line (first command with most chars = the install/run command)
    cmd_indices = [i for i, l in enumerate(lines) if l.get("type") == "command"]
    pulse_line = (
        max(cmd_indices, key=lambda i: len(lines[i].get("text", "")))
        if cmd_indices
        else 0
    )

    # Pulse at 2/3 of beat duration to reinforce the command
    pulse_f = round(duration * 0.55)
    pulse_frames = [pulse_f] if pulse_f < duration else []

    events = [
        {
            "type": "slide_in",
            "target": "window",
            "direction": "up",
            "frame": first_frame,
        },
        {"type": "pop_in", "target": "traffic_lights", "frame": first_frame + 8},
    ]
    if pulse_frames:
        events.append(
            {
                "type": "pulse",
                "target": f"line_{pulse_line}",
                "frames": pulse_frames,
                "color": data.get("accent_color", "cyan"),
            }
        )

    return {
        "template": "TerminalScene",
        "duration": duration,
        "text_frame": first_frame,
        "pulse_line": pulse_line,
        "pulse_frames": pulse_frames,
        "events": events,
        "note": f"Line {pulse_line} is key command — gets left-border + glow pulse.",
    }


def spec_bar_comparison(
    beat_key: str, data: dict, duration: int, is_first: bool
) -> dict:
    """BarComparison: bars slide in sequentially, highlight bar knocks others."""
    first_frame = 1 if is_first else 8
    items = data.get("items", [])
    events = []
    spacing = max(12, (duration - first_frame) // max(len(items), 1))

    for i, item in enumerate(items):
        sf = first_frame + i * spacing
        events.append(
            {"type": "slide_in", "target": f"bar_{i}", "direction": "left", "frame": sf}
        )
        if item.get("highlight"):
            hf = sf + 12
            if hf < duration:
                events.append({"type": "highlight", "target": f"bar_{i}", "frame": hf})
                events.append(
                    {
                        "type": "pulse",
                        "target": f"bar_{i}",
                        "frame": hf,
                        "color": data.get("accent_color", "cyan"),
                    }
                )

    return {
        "template": "BarComparison",
        "duration": duration,
        "text_frame": first_frame,
        "events": events,
        "note": "Highlighted bar gets scale pop + pulse after slide-in.",
    }


def spec_leaderboard(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """LeaderboardRank: rows slide in top-to-bottom, highlighted row gets pulse."""
    first_frame = 1 if is_first else 8
    items = data.get("items", [])
    events = []

    for i, item in enumerate(items):
        sf = first_frame + i * 14
        events.append(
            {"type": "slide_in", "target": f"row_{i}", "direction": "up", "frame": sf}
        )
        if item.get("highlight"):
            hf = sf + 10
            if hf < duration:
                events.append({"type": "highlight", "target": f"row_{i}", "frame": hf})
                events.append(
                    {
                        "type": "pulse",
                        "target": f"row_{i}",
                        "frame": hf,
                        "color": data.get("accent_color", "cyan"),
                    }
                )

    return {
        "template": "LeaderboardRank",
        "duration": duration,
        "text_frame": first_frame,
        "events": events,
        "note": "Highlighted row pops + glows. Others fade to 60% opacity.",
    }


def spec_takeaway_scene(
    beat_key: str, data: dict, duration: int, is_first: bool
) -> dict:
    """TakeawayScene: headline slams in, accent line sweeps, CTA locked to BRIEF_V4."""
    events = [
        {"type": "slam_in", "target": "headline", "frame": 1},
        {"type": "slide_in", "target": "cta_line", "direction": "up", "frame": 28},
        {
            "type": "pulse",
            "target": "headline",
            "frame": 45,
            "color": data.get("accent_color", "cyan"),
        },
    ]
    return {
        "template": "TakeawayScene",
        "duration": duration,
        "text_frame": 1,
        "events": events,
        "note": "Headline slams at frame 1. CTA: one of 4 BRIEF_V4 options (≤8 words).",
    }


def spec_generic(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """Fallback for DataGrid, TriStat, TimelineFlow, KineticBridge, CodeDiff."""
    first_frame = 1 if is_first else 8
    # Guarantee 2 events spaced 45f apart
    events = [
        {
            "type": "slide_in",
            "target": "content",
            "direction": "up",
            "frame": first_frame,
        },
        {
            "type": "pulse",
            "target": "hero_element",
            "frame": min(first_frame + 50, duration - 10),
            "color": data.get("accent_color", "cyan"),
        },
    ]
    return {
        "template": data.get("layout", "unknown"),
        "duration": duration,
        "text_frame": first_frame,
        "events": events,
        "note": "Generic spec. Customize via compositor_prompt.md if needed.",
    }


SPEC_BUILDERS = {
    "StatementSlam": spec_statement_slam,
    "MetricFocus": spec_metric_focus,
    "ComparisonSplit": spec_comparison_split,
    "PipelineFlow": spec_pipeline_flow,
    "TerminalScene": spec_terminal_scene,
    "BarComparison": spec_bar_comparison,
    "LeaderboardRank": spec_leaderboard,
    "TakeawayScene": spec_takeaway_scene,
}


# ── Validation ────────────────────────────────────────────────────────────────


def validate_beat(beat_key: str, spec: dict) -> list[str]:
    """Return list of rule violations."""
    issues = []
    events = spec.get("events", [])
    frames = [e["frame"] for e in events if "frame" in e]
    duration = spec.get("duration", 90)

    # Rule 1: first beat text at frame 1
    if beat_key == "beat_1" and spec.get("text_frame", 0) > 1:
        issues.append(
            f"{beat_key}: text_frame={spec['text_frame']} — must be 1 for first beat"
        )

    # Rule 2: >= 2 events, spaced 45-90f
    if len(frames) < 2:
        issues.append(f"{beat_key}: only {len(frames)} event(s) — need >= 2")
    elif len(frames) >= 2:
        sorted_f = sorted(frames)
        max_gap = max(sorted_f[i + 1] - sorted_f[i] for i in range(len(sorted_f) - 1))
        if max_gap > 90:
            issues.append(
                f"{beat_key}: max gap between events = {max_gap}f — exceeds 90f"
            )

    # Rule 7: no event past beat duration
    for e in events:
        ef = e.get("frame", 0)
        if ef >= duration:
            issues.append(
                f"{beat_key}: event '{e.get('type')}' at frame {ef} >= duration {duration}"
            )

    return issues


def _build_hyperframes_scene_spec(
    *,
    source_spec: dict | None,
    brief: dict,
    beat_keys: list[str],
    topic: dict,
    params: dict,
    timing: dict,
    spoken: dict,
) -> dict:
    total_frames = sum(brief[bk]["duration"] for bk in beat_keys)
    total_seconds = round(total_frames / FPS, 3)
    source_beats = {}
    if source_spec:
        source_beats = {beat.get("id"): beat for beat in source_spec.get("beats", [])}

    beats = []
    cursor = 0
    for i, beat_key in enumerate(beat_keys):
        animation_spec = brief[beat_key]
        payload = params.get(beat_key, {})
        data = payload.get("data", {})
        source_beat = source_beats.get(beat_key, {})
        segment_ref = source_beat.get("segment_ref") or (
            SEGMENT_ORDER[i] if i < len(SEGMENT_ORDER) else beat_key
        )
        segment_timing = timing.get(segment_ref, {})
        beats.append(
            {
                "id": beat_key,
                "index": i + 1,
                "segment_ref": segment_ref,
                "start_frame": cursor,
                "duration_frames": animation_spec["duration"],
                "start_seconds": round(cursor / FPS, 3),
                "duration_seconds": round(animation_spec["duration"] / FPS, 3),
                "template": animation_spec["template"],
                "layout_mode": "full_scene",
                "narration_text": spoken.get(segment_ref)
                or animation_spec.get("spoken_text")
                or animation_spec.get("narration_text", ""),
                "narration_start": segment_timing.get("start", round(cursor / FPS, 3)),
                "narration_end": segment_timing.get(
                    "end", round((cursor + animation_spec["duration"]) / FPS, 3)
                ),
                "text_frame": animation_spec.get("text_frame", 1),
                "events": animation_spec.get("events", []),
                "note": animation_spec.get("note", ""),
                "scene_data": data,
            }
        )
        cursor += animation_spec["duration"]

    meta = source_spec.get("meta", {}) if source_spec else {}
    narration_meta = source_spec.get("narration", {}) if source_spec else {}
    assets = source_spec.get("assets", {}) if source_spec else {}

    return {
        "version": "1.0",
        "meta": {
            "project": meta.get("project", "adamax-content-engine"),
            "generator_provider": meta.get("generator_provider", ""),
            "topic_slug": meta.get("topic_slug", ""),
            "fps": meta.get("fps", FPS),
            "width": meta.get("width", 1080),
            "height": meta.get("height", 1920),
        },
        "topic": topic,
        "visual_direction": {
            "style": "builder-focused dark technical explainer",
            "palette": {
                "background": "#06070a",
                "panel": "rgba(255,255,255,0.06)",
                "accent_primary": "#00e5ff",
                "accent_secondary": "#10b981",
                "text": "#f8fafc",
                "muted": "rgba(248,250,252,0.72)",
            },
            "guidance": [
                "Use the full 1080x1920 canvas.",
                "Keep compositions center-weighted, not tiny top-left fragments.",
                "Preserve strong contrast and save/share optimized hierarchy.",
                "Treat each beat as a full-scene reveal, not a sparse dashboard.",
            ],
        },
        "composition": {
            "id": f"adamax-custom-{meta.get('topic_slug', 'video') or 'video'}",
            "duration_frames": total_frames,
            "duration_seconds": total_seconds,
            "width": meta.get("width", 1080),
            "height": meta.get("height", 1920),
            "audio_src": assets.get("audio_src", "narration.wav"),
        },
        "delivery": {
            "caption": narration_meta.get("caption", ""),
            "hashtags": narration_meta.get("hashtags", []),
        },
        "beats": beats,
    }


def _write_hyperframes_starter(drop_dir: str, scene_spec: dict) -> tuple[str, str]:
    scene_spec_path = os.path.join(drop_dir, "scene-spec.json")
    starter_path = os.path.join(drop_dir, "index.starter.html")
    live_path = os.path.join(drop_dir, "index.html")

    with open(scene_spec_path, "w") as f:
        json.dump(scene_spec, f, indent=2)

    composition = scene_spec["composition"]
    beats_json = json.dumps(scene_spec["beats"], indent=2)
    starter_html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={composition['width']}, height={composition['height']}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
    <style>
      :root {{
        --bg: #05070b;
        --panel: rgba(255,255,255,0.06);
        --panel-strong: rgba(255,255,255,0.1);
        --border: rgba(255,255,255,0.12);
        --text: #f8fafc;
        --muted: rgba(248,250,252,0.72);
        --cyan: #00e5ff;
        --green: #10b981;
        --yellow: #f59e0b;
        --shadow: 0 24px 100px rgba(0,0,0,0.35);
      }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html, body {{
        width: {composition['width']}px;
        height: {composition['height']}px;
        overflow: hidden;
        background: var(--bg);
        color: var(--text);
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      }}
      #root {{
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background:
          radial-gradient(circle at 18% 12%, rgba(0,229,255,0.16), transparent 24%),
          radial-gradient(circle at 82% 24%, rgba(16,185,129,0.12), transparent 26%),
          radial-gradient(circle at 50% 100%, rgba(14,165,233,0.08), transparent 34%),
          linear-gradient(180deg, rgba(15,23,42,0.98), rgba(3,7,18,1));
      }}
      .global-grid {{
        position: absolute;
        inset: 0;
        background-image:
          linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
        background-size: 100% 96px, 96px 100%;
        mask-image: linear-gradient(180deg, rgba(255,255,255,0.8), rgba(255,255,255,0.18));
        opacity: 0.22;
        pointer-events: none;
      }}
      .scene {{
        position: absolute;
        inset: 0;
        padding: 82px 58px 74px;
      }}
      .scene-shell {{
        position: relative;
        width: 100%;
        height: 100%;
        border-radius: 38px;
        border: 1px solid var(--border);
        background:
          linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)),
          linear-gradient(180deg, rgba(8,12,20,0.72), rgba(3,7,18,0.82));
        box-shadow: var(--shadow);
        overflow: hidden;
      }}
      .scene-shell::before {{
        content: "";
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 18% 18%, rgba(0,229,255,0.1), transparent 22%),
          radial-gradient(circle at 78% 18%, rgba(16,185,129,0.08), transparent 24%);
        pointer-events: none;
      }}
      .scene-inner {{
        position: relative;
        height: 100%;
        padding: 54px 52px 50px;
        display: grid;
        grid-template-rows: auto 1fr auto;
        gap: 28px;
      }}
      .scene-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 20px;
      }}
      .eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 12px;
        color: var(--cyan);
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-size: 17px;
        font-weight: 800;
      }}
      .eyebrow::before {{
        content: "";
        width: 18px;
        height: 2px;
        border-radius: 999px;
        background: currentColor;
      }}
      .meta {{
        font-size: 12px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: rgba(248,250,252,0.48);
      }}
      .scene-main {{
        display: grid;
        align-content: start;
        gap: 22px;
      }}
      .hero-grid {{
        display: grid;
        grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr);
        gap: 24px;
        align-items: stretch;
      }}
      .hero-copy {{
        display: grid;
        align-content: start;
        gap: 20px;
      }}
      .metric-card, .info-card, .narration-card {{
        border-radius: 30px;
        border: 1px solid var(--border);
        background: rgba(255,255,255,0.045);
        backdrop-filter: blur(10px);
      }}
      .metric-card {{
        padding: 28px 28px 24px;
        display: grid;
        align-content: start;
        gap: 12px;
      }}
      .metric {{
        font-size: clamp(94px, 12vw, 168px);
        line-height: 0.88;
        color: var(--cyan);
        font-weight: 900;
        letter-spacing: -0.07em;
        text-shadow: 0 0 28px rgba(0,229,255,0.18);
      }}
      .metric-label {{
        font-size: 23px;
        color: var(--muted);
      }}
      .headline {{
        max-width: 880px;
        font-size: clamp(54px, 6vw, 108px);
        line-height: 0.95;
        letter-spacing: -0.055em;
        font-weight: 850;
      }}
      .body {{
        max-width: 860px;
        font-size: 30px;
        line-height: 1.28;
        color: rgba(248,250,252,0.86);
      }}
      .chips {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
      }}
      .chip {{
        padding: 10px 16px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.06);
        color: rgba(248,250,252,0.9);
        font-size: 15px;
      }}
      .kpi-grid {{
        display: grid;
        gap: 16px;
      }}
      .kpi {{
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.04);
        padding: 22px 22px 20px;
        display: grid;
        gap: 8px;
      }}
      .kpi-label {{
        font-size: 13px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: rgba(248,250,252,0.55);
      }}
      .kpi-value {{
        font-size: 44px;
        line-height: 0.95;
        font-weight: 850;
        letter-spacing: -0.04em;
      }}
      .bar-list {{
        display: grid;
        gap: 24px;
        margin-top: 12px;
      }}
      .bar-row {{
        display: grid;
        gap: 12px;
      }}
      .bar-topline {{
        display: flex;
        justify-content: space-between;
        gap: 16px;
        font-size: 22px;
        color: rgba(248,250,252,0.9);
      }}
      .bar-track {{
        height: 26px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(255,255,255,0.08);
      }}
      .bar-fill {{
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--cyan), var(--green));
        box-shadow: 0 0 28px rgba(0,229,255,0.14);
        transform-origin: left center;
      }}
      .statement-list {{
        display: grid;
        gap: 18px;
      }}
      .statement {{
        font-size: clamp(50px, 5.8vw, 92px);
        line-height: 0.98;
        font-weight: 850;
        letter-spacing: -0.05em;
      }}
      .statement.is-primary {{
        color: var(--cyan);
      }}
      .takeaway-layout {{
        display: grid;
        align-content: center;
        gap: 24px;
        min-height: 100%;
      }}
      .accent-line {{
        width: 240px;
        height: 5px;
        border-radius: 999px;
        background: linear-gradient(90deg, var(--cyan), rgba(0,229,255,0.06));
      }}
      .footer {{
        display: grid;
        gap: 14px;
      }}
      .narration-card {{
        padding: 18px 20px;
      }}
      .narration-label {{
        font-size: 12px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: rgba(248,250,252,0.54);
        margin-bottom: 10px;
      }}
      .narration-copy {{
        font-size: 22px;
        line-height: 1.34;
        color: rgba(248,250,252,0.92);
      }}
      .beat-badge {{
        justify-self: start;
        padding: 10px 16px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.04);
        font-size: 13px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: rgba(248,250,252,0.62);
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="{composition['id']}"
      data-start="0"
      data-duration="{composition['duration_seconds']}"
      data-width="{composition['width']}"
      data-height="{composition['height']}"
    >
      <div class="global-grid"></div>
    </div>
    <audio
      id="narration-audio"
      src="{composition['audio_src']}"
      data-start="0"
      data-duration="{composition['duration_seconds']}"
      data-track-index="{len(scene_spec['beats']) + 1}"
      data-volume="1"
    ></audio>
    <script id="scene-spec" type="application/json">{json.dumps(scene_spec)}</script>
    <script>
      window.__timelines = window.__timelines || {{}};

      const sceneSpec = JSON.parse(document.getElementById("scene-spec").textContent);
      const root = document.getElementById("root");
      const beats = {beats_json};

      const esc = (value) => String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");

      const joinChips = (chips = []) =>
        chips.map((chip) => `<span class="chip" data-anim="chip">${{esc(chip)}}</span>`).join("");

      const renderFooter = (beat) => `
        <div class="footer">
          <div class="narration-card" data-anim="footer-card">
            <div class="narration-label">Narration</div>
            <div class="narration-copy">${{esc(beat.narration_text || beat.note || "")}}</div>
          </div>
          <div class="beat-badge" data-anim="footer-badge">${{esc(beat.id)}} · ${{esc(beat.template)}}</div>
        </div>
      `;

      const renderMetricFocus = (beat, data) => `
        <div class="scene-head">
          <div class="eyebrow" data-anim="eyebrow">${{esc(data.section_label || "Hook")}}</div>
          <div class="meta">${{esc(beat.id)}} · ${{esc(beat.segment_ref)}}</div>
        </div>
        <div class="scene-main">
          <div class="hero-grid">
            <div class="hero-copy">
              <div class="metric-card" data-anim="metric-card">
                <div class="metric" data-anim="metric-value">${{esc(data.hero?.value || beat.narration_text)}}</div>
                <div class="metric-label" data-anim="metric-label">${{esc(data.hero?.label || "Key metric")}}</div>
              </div>
              <div class="headline" data-anim="headline">${{esc(data.context || beat.narration_text)}}</div>
              <div class="chips" data-anim="chips">${{joinChips(data.chips || [])}}</div>
            </div>
            <div class="kpi-grid">
              <div class="kpi" data-anim="kpi-a">
                <div class="kpi-label">Problem</div>
                <div class="kpi-value">Paid</div>
                <div class="body">Cloud orchestration burn compounds monthly.</div>
              </div>
              <div class="kpi" data-anim="kpi-b">
                <div class="kpi-label">Shift</div>
                <div class="kpi-value">Local</div>
                <div class="body">Move the agent runtime onto your own machine.</div>
              </div>
            </div>
          </div>
        </div>
        ${{renderFooter(beat)}}
      `;

      const renderBarComparison = (beat, data) => `
        <div class="scene-head">
          <div class="eyebrow" data-anim="eyebrow">${{esc(data.section_label || "Comparison")}}</div>
          <div class="meta">${{esc(beat.id)}} · ${{esc(beat.segment_ref)}}</div>
        </div>
        <div class="scene-main">
          <div class="headline" data-anim="headline">The pricing gap is the story.</div>
          <div class="body" data-anim="body">${{esc(beat.narration_text)}}</div>
          <div class="bar-list">
            ${{(data.items || []).map((item, index) => `
              <div class="bar-row" data-anim="bar-row-${{index}}">
                <div class="bar-topline">
                  <span>${{esc(item.label)}}</span>
                  <span>${{esc(item.value)}}${{esc(item.unit || "")}}</span>
                </div>
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    data-anim="bar-fill-${{index}}"
                    style="width: ${{item.highlight ? 100 : 6}}%;"
                  ></div>
                </div>
              </div>
            `).join("")}}
          </div>
        </div>
        ${{renderFooter(beat)}}
      `;

      const renderStatementSlam = (beat, data) => `
        <div class="scene-head">
          <div class="eyebrow" data-anim="eyebrow">${{esc(data.section_label || "Insight")}}</div>
          <div class="meta">${{esc(beat.id)}} · ${{esc(beat.segment_ref)}}</div>
        </div>
        <div class="scene-main">
          <div class="statement-list">
            ${{(data.lines || []).map((line, index) => `
              <div class="statement ${{index === 0 ? "is-primary" : ""}}" data-anim="statement-${{index}}">
                ${{esc(line)}}
              </div>
            `).join("")}}
          </div>
        </div>
        ${{renderFooter(beat)}}
      `;

      const renderTakeaway = (beat, data) => `
        <div class="scene-head">
          <div class="eyebrow" data-anim="eyebrow">Takeaway</div>
          <div class="meta">${{esc(beat.id)}} · ${{esc(beat.segment_ref)}}</div>
        </div>
        <div class="scene-main takeaway-layout">
          <div class="accent-line" data-anim="accent-line"></div>
          <div class="headline" data-anim="headline">${{esc(data.headline || beat.narration_text)}}</div>
          <div class="body" data-anim="body">Save it. Reuse it. Run it locally.</div>
        </div>
        ${{renderFooter(beat)}}
      `;

      const renderGeneric = (beat, data) => `
        <div class="scene-head">
          <div class="eyebrow" data-anim="eyebrow">${{esc(data.section_label || beat.template)}}</div>
          <div class="meta">${{esc(beat.id)}} · ${{esc(beat.segment_ref)}}</div>
        </div>
        <div class="scene-main">
          <div class="headline" data-anim="headline">${{esc(beat.narration_text)}}</div>
          <div class="body" data-anim="body">${{esc(beat.note || "")}}</div>
        </div>
        ${{renderFooter(beat)}}
      `;

      const renderBeatInner = (beat) => {{
        const data = beat.scene_data || {{}};
        if (beat.template === "MetricFocus") return renderMetricFocus(beat, data);
        if (beat.template === "BarComparison") return renderBarComparison(beat, data);
        if (beat.template === "StatementSlam") return renderStatementSlam(beat, data);
        if (beat.template === "TakeawayScene") return renderTakeaway(beat, data);
        return renderGeneric(beat, data);
      }};

      const renderBeat = (beat) => {{
        const scene = document.createElement("section");
        scene.className = "scene clip";
        scene.id = beat.id;
        scene.dataset.start = String(beat.start_seconds);
        scene.dataset.duration = String(beat.duration_seconds);
        scene.dataset.trackIndex = String(beat.index - 1);
        scene.dataset.template = beat.template;

        scene.innerHTML = `
          <div class="scene-shell">
            <div class="scene-inner">
              ${{renderBeatInner(beat)}}
            </div>
          </div>
        `;
        root.appendChild(scene);
      }};

      beats.forEach(renderBeat);

      const tl = gsap.timeline({{ paused: true }});

      beats.forEach((beat) => {{
        const base = beat.start_seconds;
        const sceneSelector = `#${{beat.id}}`;
        const inside = (name) => `${{sceneSelector}} [data-anim="${{name}}"]`;

        tl.from(sceneSelector, {{
          opacity: 0,
          scale: 0.985,
          duration: 0.38,
          ease: "power2.out"
        }}, base);

        tl.from(inside("eyebrow"), {{
          opacity: 0,
          x: -28,
          duration: 0.34,
          ease: "power2.out"
        }}, base + 0.02);

        tl.from(inside("headline"), {{
          opacity: 0,
          y: 42,
          duration: 0.45,
          ease: "power2.out"
        }}, base + 0.08);

        tl.from(inside("body"), {{
          opacity: 0,
          y: 28,
          duration: 0.34,
          ease: "power2.out"
        }}, base + 0.16);

        tl.from(inside("metric-card"), {{
          opacity: 0,
          y: 32,
          duration: 0.36,
          ease: "power2.out"
        }}, base + 0.06);

        tl.from(inside("metric-value"), {{
          opacity: 0,
          scale: 0.92,
          duration: 0.42,
          ease: "back.out(1.3)"
        }}, base + 0.14);

        tl.from([inside("kpi-a"), inside("kpi-b")], {{
          opacity: 0,
          x: 26,
          stagger: 0.08,
          duration: 0.34,
          ease: "power2.out"
        }}, base + 0.2);

        tl.from(inside("chip"), {{
          opacity: 0,
          y: 18,
          stagger: 0.06,
          duration: 0.24,
          ease: "power2.out"
        }}, base + 0.24);

        tl.from([inside("bar-row-0"), inside("bar-row-1"), inside("bar-row-2")], {{
          opacity: 0,
          y: 18,
          stagger: 0.08,
          duration: 0.26,
          ease: "power2.out"
        }}, base + 0.18);

        tl.from([inside("bar-fill-0"), inside("bar-fill-1"), inside("bar-fill-2")], {{
          scaleX: 0,
          stagger: 0.1,
          duration: 0.42,
          ease: "power2.out",
          transformOrigin: "left center"
        }}, base + 0.22);

        tl.from([inside("statement-0"), inside("statement-1"), inside("statement-2")], {{
          opacity: 0,
          y: 34,
          stagger: 0.12,
          duration: 0.3,
          ease: "power2.out"
        }}, base + 0.1);

        tl.from(inside("accent-line"), {{
          scaleX: 0,
          duration: 0.34,
          ease: "power2.out",
          transformOrigin: "left center"
        }}, base + 0.06);

        tl.from([inside("footer-card"), inside("footer-badge")], {{
          opacity: 0,
          y: 18,
          stagger: 0.08,
          duration: 0.26,
          ease: "power2.out"
        }}, base + 0.28);
      }});

      window.__timelines["{composition['id']}"] = tl;
    </script>
  </body>
</html>
"""

    with open(starter_path, "w") as f:
        f.write(starter_html)

    if not os.path.exists(live_path):
        with open(live_path, "w") as f:
            f.write(starter_html)

    return scene_spec_path, starter_path


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    # Load inputs — Phase 1 prefers video_spec.json as the source of truth.
    source_spec = load_video_spec()
    if source_spec:
        print("[brief_generator] Using video_spec.json as primary input")
        topic = source_spec.get("topic", {})
        spoken = source_spec.get("narration", {}).get("segments", {})
        timing = source_spec.get("timing", {}).get("segments", {})
        cues = source_spec.get("cues", {})
        beats = sorted(source_spec.get("beats", []), key=lambda b: b.get("index", 0))
        params = {}
        beat_keys = []
        for beat in beats:
            beat_id = beat.get("id")
            scene = beat.get("scene", {})
            if scene.get("kind") == "template":
                params[beat_id] = scene.get("config", {})
            else:
                params[beat_id] = {
                    "data": {
                        "layout": "StatementSlam",
                        "section_label": "CUSTOM",
                        "lines": ["Custom scene"],
                    }
                }
            beat_keys.append(beat_id)
    else:
        source_spec = None
        with open(PARAMS_PATH) as f:
            params = json.load(f)
        with open(TIMING_PATH) as f:
            timing = json.load(f)

        cues = {}
        if os.path.exists(CUES_PATH):
            with open(CUES_PATH) as f:
                cues = json.load(f)

        topic = {}
        if os.path.exists(TOPIC_PATH):
            with open(TOPIC_PATH) as f:
                topic = json.load(f)

        spoken = {}
        if os.path.exists(SPOKEN_PATH):
            with open(SPOKEN_PATH) as f:
                spoken = json.load(f)

        beat_keys = sorted(params.keys())  # beat_1, beat_2, ...

    brief = {}
    all_issues = []

    for i, beat_key in enumerate(beat_keys):
        payload = params[beat_key]
        data = payload.get("data", {})
        layout = data.get("layout", "unknown")
        is_first = i == 0
        duration = frames_in_beat(beat_key, timing, beat_keys)

        builder = SPEC_BUILDERS.get(layout, spec_generic)
        beat_spec = builder(beat_key, data, duration, is_first)

        # Attach narration text for compositor context
        seg_key = SEGMENT_ORDER[i] if i < len(SEGMENT_ORDER) else None
        if seg_key and seg_key in timing:
            beat_spec["narration_text"] = timing[seg_key].get("text", "")
            beat_spec["narration_start"] = timing[seg_key].get("start", 0)
            beat_spec["narration_end"] = timing[seg_key].get("end", 0)
        if seg_key and seg_key in spoken:
            beat_spec["spoken_text"] = spoken[seg_key]

        # Attach relevant word cues
        word_cues = cues.get("word_cues", [])
        beat_spec["cues"] = word_cues  # compositor can use these for extra sync

        issues = validate_beat(beat_key, beat_spec)
        if issues:
            all_issues.extend(issues)
            print(f"  [brief_generator] WARN {beat_key}: {issues}")

        brief[beat_key] = beat_spec

    # Save animation_brief.json
    os.makedirs(os.path.dirname(BRIEF_OUT), exist_ok=True)
    with open(BRIEF_OUT, "w") as f:
        json.dump(brief, f, indent=2)
    print(f"[brief_generator] animation_brief.json → {BRIEF_OUT}")

    # Compute drop path (same slug logic as run.py _compositor_pause)
    from datetime import date as _date

    title = topic.get("title", "video")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    today = _date.today().isoformat()
    comp_dir = os.path.join(_ROOT, "output", "compositions", f"{today}_{slug}")
    drop_path = os.path.join(comp_dir, "CustomVideo.tsx")
    os.makedirs(comp_dir, exist_ok=True)
    hyper_dir = os.path.join(_ROOT, "output", "hyperframes_custom", f"{today}_{slug}")
    hyper_drop_path = os.path.join(hyper_dir, "index.html")
    os.makedirs(hyper_dir, exist_ok=True)

    # Persist drop_path so _compositor_pause can read it back
    with open(DROP_PATH_OUT, "w") as f:
        f.write(drop_path)
    with open(HYPER_DROP_PATH_OUT, "w") as f:
        f.write(hyper_drop_path)

    hyper_scene_spec = _build_hyperframes_scene_spec(
        source_spec=source_spec,
        brief=brief,
        beat_keys=beat_keys,
        topic=topic,
        params=params,
        timing=timing,
        spoken=spoken,
    )
    with open(HYPER_SCENE_SPEC_OUT, "w") as f:
        json.dump(hyper_scene_spec, f, indent=2)
    scene_spec_path, starter_path = _write_hyperframes_starter(
        hyper_dir, hyper_scene_spec
    )

    # Build compositor_prompt.md
    _write_compositor_prompt(brief, topic, beat_keys, drop_path=drop_path)
    _write_hyperframes_prompt(
        brief,
        topic,
        beat_keys,
        drop_path=hyper_drop_path,
        scene_spec_path=scene_spec_path,
        starter_path=starter_path,
    )
    with open(HYPER_BRIEF_OUT, "w") as f:
        json.dump(brief, f, indent=2)
    print(f"[brief_generator] compositor_prompt.md  → {PROMPT_OUT}")
    print(f"[brief_generator] drop_path             → {drop_path}")
    print(f"[brief_generator] hyperframes prompt    → {HYPER_PROMPT_OUT}")
    print(f"[brief_generator] hyperframes drop_path → {hyper_drop_path}")

    if all_issues:
        print(
            f"\n[brief_generator] {len(all_issues)} rule violation(s) found — review brief before compositor."
        )
    else:
        print("[brief_generator] All beats pass animation rules.")

    return brief


def _write_compositor_prompt(
    brief: dict, topic: dict, beat_keys: list[str], drop_path: str = ""
):
    title = topic.get("title", "Video")

    # Build beat summary for the prompt
    beat_lines = []
    for bk in beat_keys:
        spec = brief[bk]
        narr = spec.get("spoken_text") or spec.get("narration_text", "")
        events_summary = ", ".join(
            f"{e['type']}({e.get('target','?')}@{e.get('frame', e.get('frames','?'))}f)"
            for e in spec.get("events", [])
        )
        beat_lines.append(
            f"### {bk} — {spec['template']}  ({spec['duration']}f / {spec['duration']//30}s)\n"
            f'**Narration:** "{narr}"\n'
            f"**text_frame:** {spec['text_frame']}  ← first visible text at this frame\n"
            f"**Events:** {events_summary}\n"
            f"**Note:** {spec.get('note','')}\n"
        )

    beat_block = "\n".join(beat_lines)

    # Available templates list
    templates = ", ".join(sorted({brief[bk]["template"] for bk in beat_keys}))

    prompt = f"""# Compositor Brief — {title}

Read `output/animation_brief.json` for the full per-beat spec.
Write `CustomVideo.tsx` to the path printed by the pipeline.

---

## Your job

Implement the animation spec exactly. Do NOT invent structure.
The brief is the creative decision. You are the coder.

---

## Hard rules (enforced — do not break)

1. **Frame 1 has text** — beat_1 must render visible text at frame 1. No intro. No logo. No blank screen.
2. **Every beat has >= 2 animation events** spaced 45–90 frames apart — already in the brief.
3. **ComparisonSplit winning side pulses** — use `usePulseAt` from `_shared.tsx` on the right panel.
4. **PipelineFlow steps activate sequentially** — use frame offsets from brief, not all at once.
5. **TerminalScene key command gets pulse** — `pulse_line` + `pulse_frames` are in the brief.
6. **TakeawayScene CTA ≤ 8 words** — use one of 4 BRIEF_V4 options. No "what do you think?" endings.
7. **No beat exceeds its duration** — `duration` field in brief is the hard cap in frames.

---

## Available animation primitives (import from `./_shared`)

```ts
usePulseAt(frame, pulseFrames: number[], color, radius?)  // boxShadow string
useSlideIn(frame, direction, startFrame, distance?)        // {{ opacity, transform }}
useHighlightAt(frame, highlightFrame)                      // {{ scale, active, opacity }}
countUp(value, progress)                                   // formatted string for hero numbers
useBreath(frame, fps)                                      // {{ scale, opacityShift }}
```

---

## Beat specs

{beat_block}
---

## Templates used in this video

{templates}

All templates live in `remotion/src/layouts/`. Import and use them.
Each template accepts a `data` prop typed from `SceneData` in `types.ts`.

---

## Output

Write ONE self-contained `CustomVideo.tsx`.
- No external props — all data hardcoded from the brief above.
- Import from `remotion`, `react`, and `./layouts/` only.
- `useCurrentFrame()` + `useVideoConfig()` for frame/fps.
- Wrap each beat in a `<Sequence from={{beatStartFrame}} durationInFrames={{duration}}>`.
- Beat start frames (cumulative): {_beat_start_summary(brief, beat_keys)}

When done, drop the file at this exact path and press Enter in the pipeline terminal:

```
{drop_path}
```
"""

    with open(PROMPT_OUT, "w") as f:
        f.write(prompt)


def _write_hyperframes_prompt(
    brief: dict,
    topic: dict,
    beat_keys: list[str],
    drop_path: str = "",
    scene_spec_path: str = "",
    starter_path: str = "",
):
    title = topic.get("title", "Video")
    total_duration = sum(brief[bk]["duration"] for bk in beat_keys) / FPS

    beat_lines = []
    cursor = 0
    for bk in beat_keys:
        spec = brief[bk]
        narr = spec.get("spoken_text") or spec.get("narration_text", "")
        start_seconds = round(cursor / FPS, 3)
        duration_seconds = round(spec["duration"] / FPS, 3)
        beat_lines.append(
            f"### {bk} — {spec['template']}\n"
            f"- start: {start_seconds}s\n"
            f"- duration: {duration_seconds}s\n"
            f'- narration: "{narr}"\n'
            f"- note: {spec.get('note','')}\n"
        )
        cursor += spec["duration"]

    beat_block = "\n".join(beat_lines)

    prompt = f"""# HyperFrames Custom Compositor Brief — {title}

Write a native HyperFrames composition to this exact file:

```
{drop_path}
```

## Goal

Create one `index.html` that renders the whole short-form video in HyperFrames.
This is a custom composition path. Do not write React. Do not write Remotion.

## Files already prepared for you

- structured scene spec: `{scene_spec_path}`
- starter scaffold: `{starter_path}`

## Hard requirements

1. Root element must include:
   - `data-composition-id`
   - `data-start="0"`
   - `data-duration="{round(total_duration, 3)}"`
   - `data-width="1080"`
   - `data-height="1920"`
2. Every timed visible element must use:
   - `class="clip"`
   - `data-start`
   - `data-duration`
   - `data-track-index`
3. Register a paused GSAP timeline:
   - `window.__timelines = window.__timelines || {{}};`
   - `window.__timelines["<composition-id>"] = gsap.timeline({{ paused: true }});`
4. No React. No imports from this repo. Plain HTML/CSS/JS only.
5. No `Date.now()`, no `performance.now()`, no `requestAnimationFrame`, no randomness.
6. `narration.wav` is available beside `index.html`. Add an `<audio>` element for it.
7. Design for `1080x1920` portrait. Use the full frame. Avoid tiny top-left layouts.

## Available timing plan

{beat_block}

## Visual direction

- builder-focused AI reel
- dark technical background
- cyan/green accents
- bold typography
- strong center-weighted composition
- use more of the vertical canvas

## Suggested structure

- one full-frame background layer
- one timed scene group per beat
- one audio track for narration
- one GSAP timeline that:
  - reveals each beat at its scheduled time
  - animates text/metrics/bars in deterministic ways
  - hides each beat after its duration

## Output contract

- write only the final `index.html`
- self-contained except CDN GSAP and local `narration.wav`
- no placeholders, no TODOs
"""

    with open(HYPER_PROMPT_OUT, "w") as f:
        f.write(prompt)


def _beat_start_summary(brief: dict, beat_keys: list[str]) -> str:
    starts = []
    cursor = 0
    for bk in beat_keys:
        starts.append(f"{bk}=frame {cursor}")
        cursor += brief[bk]["duration"]
    return ", ".join(starts)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()
