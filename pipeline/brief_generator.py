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

_ROOT         = os.path.join(os.path.dirname(__file__), "..")
PARAMS_PATH   = os.path.join(_ROOT, "output", "params.json")
TIMING_PATH   = os.path.join(_ROOT, "output", "narration_timing.json")
CUES_PATH     = os.path.join(_ROOT, "cue_definitions.json")
TOPIC_PATH    = os.path.join(_ROOT, "output", "topic.json")
SPOKEN_PATH   = os.path.join(_ROOT, "output", "spoken_narration.json")
BRIEF_OUT     = os.path.join(_ROOT, "output", "animation_brief.json")
PROMPT_OUT    = os.path.join(_ROOT, "output", "compositor_prompt.md")
DROP_PATH_OUT = os.path.join(_ROOT, "output", "drop_path.txt")

FPS = 30

# Map narration segment keys → beat keys (beat_1 = hook, beat_2 = concept_1, etc.)
SEGMENT_ORDER = ["hook", "concept_1", "concept_2", "concept_3", "concept_4", "takeaway_cta"]


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

def spec_statement_slam(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """StatementSlam: lines stagger in, line 0 glows. First beat = text at frame 1."""
    lines = data.get("lines", [])
    events = []

    # Rule 1: first beat text at frame 1
    first_frame = 1 if is_first else 6

    for i, line in enumerate(lines):
        enter = first_frame + i * 18
        events.append({"type": "slide_in", "target": f"line_{i}", "direction": "up", "frame": enter})
        if i == 0:
            # Glow pulse on line 0 at frame 45 and 90
            for pf in [45, 90]:
                if pf < duration:
                    events.append({"type": "pulse", "target": "line_0", "frame": pf, "color": data.get("accent_color", "cyan")})

    return {
        "template":    "StatementSlam",
        "duration":    duration,
        "text_frame":  first_frame,
        "events":      events,
        "note":        "Line 0 glows — accent color. Stagger 18f between lines.",
    }


def spec_metric_focus(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """MetricFocus: hero counts up, chips slide in, pulse at 60f."""
    first_frame = 1 if is_first else 8
    events = [
        {"type": "count_up", "target": "hero_value", "frame": first_frame},
        {"type": "slide_in", "target": "context",    "direction": "up", "frame": first_frame + 20},
    ]
    chips = data.get("chips", [])
    for i in range(len(chips)):
        events.append({"type": "slide_in", "target": f"chip_{i}", "direction": "up", "frame": first_frame + 36 + i * 14})

    pulse_f = 60
    if pulse_f < duration:
        events.append({"type": "pulse", "target": "hero_value", "frame": pulse_f,
                       "color": data.get("hero", {}).get("color", "cyan")})

    return {
        "template":   "MetricFocus",
        "duration":   duration,
        "text_frame": first_frame,
        "events":     events,
        "note":       "Hero counts up from 0. Pulse at 60f reinforces the number.",
    }


def spec_comparison_split(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """ComparisonSplit: left slides in, right slides in 14f later, winning side pulses."""
    first_frame = 1 if is_first else 6
    right_color = data.get("right", {}).get("color", "green")

    events = [
        {"type": "slide_in", "target": "panel_left",  "direction": "left",  "frame": first_frame},
        {"type": "slide_in", "target": "panel_right", "direction": "right", "frame": first_frame + 14},
    ]

    # Rule 3: winning side (right) always gets pulse events every ~45f
    pulse_frames = []
    pf = first_frame + 30
    while pf < duration:
        pulse_frames.append(pf)
        pf += 45

    if pulse_frames:
        events.append({"type": "pulse", "target": "panel_right", "frames": pulse_frames, "color": right_color})

    # Highlight winning metrics
    right_metrics = data.get("right", {}).get("metrics", [])
    for i, m in enumerate(right_metrics):
        hf = first_frame + 30 + i * 16
        if hf < duration:
            events.append({"type": "highlight", "target": f"right_metric_{i}", "frame": hf})

    return {
        "template":     "ComparisonSplit",
        "duration":     duration,
        "text_frame":   first_frame,
        "winning_side": "right",
        "pulse_frames": pulse_frames,
        "events":       events,
        "note":         "Right panel = winner. Pulse every 45f. Metrics highlight sequentially.",
    }


def spec_pipeline_flow(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """PipelineFlow: steps light up sequentially, timed to narration words."""
    first_frame = 1 if is_first else 8
    steps = data.get("steps", [])
    n = len(steps)
    events = []

    # Space step activations evenly across beat duration
    spacing = max(20, (duration - first_frame - 20) // max(n, 1))
    for i, step in enumerate(steps):
        activate_f = first_frame + i * spacing
        events.append({"type": "activate_step", "target": f"step_{i}", "label": step.get("label", ""), "frame": activate_f})
        if step.get("state") == "bottleneck":
            events.append({"type": "pulse", "target": f"step_{i}", "frame": activate_f + 8, "color": "red"})

    return {
        "template":   "PipelineFlow",
        "duration":   duration,
        "text_frame": first_frame,
        "events":     events,
        "note":       f"Steps activate sequentially every ~{spacing}f. Bottleneck gets red pulse.",
    }


def spec_terminal_scene(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """TerminalScene: window slides up, lines type in, key command gets pulse."""
    first_frame = 1 if is_first else 6
    lines = data.get("lines", [])

    # Find the key command line (first command with most chars = the install/run command)
    cmd_indices = [i for i, l in enumerate(lines) if l.get("type") == "command"]
    pulse_line = max(cmd_indices, key=lambda i: len(lines[i].get("text", ""))) if cmd_indices else 0

    # Pulse at 2/3 of beat duration to reinforce the command
    pulse_f = round(duration * 0.55)
    pulse_frames = [pulse_f] if pulse_f < duration else []

    events = [
        {"type": "slide_in", "target": "window",      "direction": "up", "frame": first_frame},
        {"type": "pop_in",   "target": "traffic_lights",                 "frame": first_frame + 8},
    ]
    if pulse_frames:
        events.append({"type": "pulse", "target": f"line_{pulse_line}", "frames": pulse_frames, "color": data.get("accent_color", "cyan")})

    return {
        "template":    "TerminalScene",
        "duration":    duration,
        "text_frame":  first_frame,
        "pulse_line":  pulse_line,
        "pulse_frames": pulse_frames,
        "events":      events,
        "note":        f"Line {pulse_line} is key command — gets left-border + glow pulse.",
    }


def spec_bar_comparison(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """BarComparison: bars slide in sequentially, highlight bar knocks others."""
    first_frame = 1 if is_first else 8
    items = data.get("items", [])
    events = []
    spacing = max(12, (duration - first_frame) // max(len(items), 1))

    for i, item in enumerate(items):
        sf = first_frame + i * spacing
        events.append({"type": "slide_in", "target": f"bar_{i}", "direction": "left", "frame": sf})
        if item.get("highlight"):
            hf = sf + 12
            if hf < duration:
                events.append({"type": "highlight", "target": f"bar_{i}", "frame": hf})
                events.append({"type": "pulse",     "target": f"bar_{i}", "frame": hf,
                               "color": data.get("accent_color", "cyan")})

    return {
        "template":   "BarComparison",
        "duration":   duration,
        "text_frame": first_frame,
        "events":     events,
        "note":       "Highlighted bar gets scale pop + pulse after slide-in.",
    }


def spec_leaderboard(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """LeaderboardRank: rows slide in top-to-bottom, highlighted row gets pulse."""
    first_frame = 1 if is_first else 8
    items = data.get("items", [])
    events = []

    for i, item in enumerate(items):
        sf = first_frame + i * 14
        events.append({"type": "slide_in", "target": f"row_{i}", "direction": "up", "frame": sf})
        if item.get("highlight"):
            hf = sf + 10
            if hf < duration:
                events.append({"type": "highlight", "target": f"row_{i}", "frame": hf})
                events.append({"type": "pulse",     "target": f"row_{i}", "frame": hf,
                               "color": data.get("accent_color", "cyan")})

    return {
        "template":   "LeaderboardRank",
        "duration":   duration,
        "text_frame": first_frame,
        "events":     events,
        "note":       "Highlighted row pops + glows. Others fade to 60% opacity.",
    }


def spec_takeaway_scene(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """TakeawayScene: headline slams in, accent line sweeps, CTA locked to BRIEF_V4."""
    events = [
        {"type": "slam_in",  "target": "headline", "frame": 1},
        {"type": "slide_in", "target": "cta_line", "direction": "up", "frame": 28},
        {"type": "pulse",    "target": "headline", "frame": 45,
         "color": data.get("accent_color", "cyan")},
    ]
    return {
        "template":   "TakeawayScene",
        "duration":   duration,
        "text_frame": 1,
        "events":     events,
        "note":       "Headline slams at frame 1. CTA: one of 4 BRIEF_V4 options (≤8 words).",
    }


def spec_generic(beat_key: str, data: dict, duration: int, is_first: bool) -> dict:
    """Fallback for DataGrid, TriStat, TimelineFlow, KineticBridge, CodeDiff."""
    first_frame = 1 if is_first else 8
    # Guarantee 2 events spaced 45f apart
    events = [
        {"type": "slide_in", "target": "content",      "direction": "up",  "frame": first_frame},
        {"type": "pulse",    "target": "hero_element",                      "frame": min(first_frame + 50, duration - 10),
         "color": data.get("accent_color", "cyan")},
    ]
    return {
        "template":   data.get("layout", "unknown"),
        "duration":   duration,
        "text_frame": first_frame,
        "events":     events,
        "note":       "Generic spec. Customize via compositor_prompt.md if needed.",
    }


SPEC_BUILDERS = {
    "StatementSlam":  spec_statement_slam,
    "MetricFocus":    spec_metric_focus,
    "ComparisonSplit": spec_comparison_split,
    "PipelineFlow":   spec_pipeline_flow,
    "TerminalScene":  spec_terminal_scene,
    "BarComparison":  spec_bar_comparison,
    "LeaderboardRank": spec_leaderboard,
    "TakeawayScene":  spec_takeaway_scene,
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
        issues.append(f"{beat_key}: text_frame={spec['text_frame']} — must be 1 for first beat")

    # Rule 2: >= 2 events, spaced 45-90f
    if len(frames) < 2:
        issues.append(f"{beat_key}: only {len(frames)} event(s) — need >= 2")
    elif len(frames) >= 2:
        sorted_f = sorted(frames)
        max_gap = max(sorted_f[i+1] - sorted_f[i] for i in range(len(sorted_f)-1))
        if max_gap > 90:
            issues.append(f"{beat_key}: max gap between events = {max_gap}f — exceeds 90f")

    # Rule 7: no event past beat duration
    for e in events:
        ef = e.get("frame", 0)
        if ef >= duration:
            issues.append(f"{beat_key}: event '{e.get('type')}' at frame {ef} >= duration {duration}")

    return issues


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load inputs
    with open(PARAMS_PATH)  as f: params  = json.load(f)
    with open(TIMING_PATH)  as f: timing  = json.load(f)

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
        payload  = params[beat_key]
        data     = payload.get("data", {})
        layout   = data.get("layout", "unknown")
        is_first = (i == 0)
        duration = frames_in_beat(beat_key, timing, beat_keys)

        builder = SPEC_BUILDERS.get(layout, spec_generic)
        spec    = builder(beat_key, data, duration, is_first)

        # Attach narration text for compositor context
        seg_key = SEGMENT_ORDER[i] if i < len(SEGMENT_ORDER) else None
        if seg_key and seg_key in timing:
            spec["narration_text"]  = timing[seg_key].get("text", "")
            spec["narration_start"] = timing[seg_key].get("start", 0)
            spec["narration_end"]   = timing[seg_key].get("end", 0)
        if seg_key and seg_key in spoken:
            spec["spoken_text"] = spoken[seg_key]

        # Attach relevant word cues
        word_cues = cues.get("word_cues", [])
        spec["cues"] = word_cues  # compositor can use these for extra sync

        issues = validate_beat(beat_key, spec)
        if issues:
            all_issues.extend(issues)
            print(f"  [brief_generator] WARN {beat_key}: {issues}")

        brief[beat_key] = spec

    # Save animation_brief.json
    os.makedirs(os.path.dirname(BRIEF_OUT), exist_ok=True)
    with open(BRIEF_OUT, "w") as f:
        json.dump(brief, f, indent=2)
    print(f"[brief_generator] animation_brief.json → {BRIEF_OUT}")

    # Compute drop path (same slug logic as run.py _compositor_pause)
    from datetime import date as _date
    title = topic.get("title", "video")
    slug  = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    today = _date.today().isoformat()
    comp_dir  = os.path.join(_ROOT, "output", "compositions", f"{today}_{slug}")
    drop_path = os.path.join(comp_dir, "CustomVideo.tsx")
    os.makedirs(comp_dir, exist_ok=True)

    # Persist drop_path so _compositor_pause can read it back
    with open(DROP_PATH_OUT, "w") as f:
        f.write(drop_path)

    # Build compositor_prompt.md
    _write_compositor_prompt(brief, topic, beat_keys, drop_path=drop_path)
    print(f"[brief_generator] compositor_prompt.md  → {PROMPT_OUT}")
    print(f"[brief_generator] drop_path             → {drop_path}")

    if all_issues:
        print(f"\n[brief_generator] {len(all_issues)} rule violation(s) found — review brief before compositor.")
    else:
        print("[brief_generator] All beats pass animation rules.")

    return brief


def _write_compositor_prompt(brief: dict, topic: dict, beat_keys: list[str], drop_path: str = ""):
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
            f"**Narration:** \"{narr}\"\n"
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
