"""
param_extractor.py — extracts per-beat visual LayoutNode trees from the scene plan.

Motion Design v2 (Phase 2): output format is BeatLayout JSON, not flat template fields.

Reads:
  output/script.json     — narration script
  output/topic.json      — topic metadata
  output/scene_plan.json — which template each beat uses (still used as content hint)

Output: output/params.json

Format (new):
  {
    "beat_1": { "animate_in": "spring_scale", "layout": { "type": "column", ... } },
    "beat_2": { "animate_in": "spring_in",    "layout": { ... } },
    ...
  }

Fallback (Option A from TDD): if LLM output fails validation 3×, substitutes the
STATIC_FALLBACK_TREES for each failed beat — video always renders.
"""
import json
import os
import re

from pipeline import claude_client

SCRIPT_PATH     = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TOPIC_PATH      = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
SCENE_PLAN_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "scene_plan.json")
OUTPUT_PATH     = os.path.join(os.path.dirname(__file__), "..", "output", "params.json")


# ── LayoutNode validation (shared with Phase 0 schema foundation) ─────────────

_ALLOWED_NODE_TYPES = {
    "column", "row", "grid",
    "TerminalPrompt", "TerminalText",
    "StatBox", "LabelValueCard",
    "CodeBlock", "Chip",
    "Divider", "Spacer",
}
_CONTAINER_TYPES = {"column", "row", "grid"}
_ALLOWED_COLORS  = {"green", "cyan", "yellow", "red", "white"}
_ALLOWED_ANIMATE_IN = {
    "spring_in", "spring_scale", "typewriter", "fade", "slide_up", "none",
}


def _validate_layout_node(node: dict, depth: int = 0) -> list[str]:
    """Recursive validator for a LayoutNode tree. Returns list of error strings."""
    if depth > 4:
        return ["Layout tree too deep (max 4 levels)"]

    errors: list[str] = []
    node_type = node.get("type")

    if node_type not in _ALLOWED_NODE_TYPES:
        errors.append(f"Unknown node type: {node_type!r}")
        return errors

    is_container = node_type in _CONTAINER_TYPES
    children = node.get("children", [])

    if is_container and not children:
        errors.append(f"Container '{node_type}' has no children")
    if not is_container and children:
        errors.append(f"Leaf node '{node_type}' must not have children")

    if node_type == "grid":
        cols = node.get("columns")
        if cols not in (2, 3):
            errors.append(f"grid.columns must be 2 or 3, got {cols!r}")

    for field, allowed in (("color", _ALLOWED_COLORS), ("border_color", _ALLOWED_COLORS)):
        val = node.get(field)
        if val and val not in allowed:
            errors.append(f"Invalid {field} {val!r} in node '{node_type}'")

    delay = node.get("delay")
    if delay is not None and (not isinstance(delay, (int, float)) or delay < 0):
        errors.append(f"delay must be non-negative number, got {delay!r}")

    text = node.get("text", "")
    if text and len(text) > 120:
        errors.append(f"text too long ({len(text)} chars) in node '{node_type}'")

    for child in children:
        if not isinstance(child, dict):
            errors.append(f"Child of '{node_type}' must be an object, got {type(child).__name__}")
            continue
        errors += _validate_layout_node(child, depth + 1)

    return errors


def _validate_beat_layout(beat_layout: dict) -> list[str]:
    """Validate a BeatLayout dict: { animate_in, layout }."""
    errors: list[str] = []
    animate_in = beat_layout.get("animate_in")
    if animate_in not in _ALLOWED_ANIMATE_IN:
        errors.append(f"Invalid animate_in {animate_in!r}")
    if "layout" not in beat_layout:
        errors.append("Missing 'layout' field")
        return errors
    errors += _validate_layout_node(beat_layout["layout"])
    return errors


# ── Static fallback trees (Option A — always renders) ─────────────────────────

STATIC_FALLBACK_TREES: dict[str, dict] = {
    "hook": {
        "animate_in": "spring_scale",
        "layout": {
            "type": "column", "gap": 0, "justify": "flex-start", "padding": 50,
            "children": [
                {"type": "TerminalPrompt", "text": "user@adamax:~$"},
                {"type": "Spacer", "size": 620},
                {"type": "StatBox", "value": "N/A", "label": "stat", "color": "green",
                 "animate": "spring_in", "delay": 0},
                {"type": "Spacer", "size": 240},
                {"type": "TerminalText", "text": "Data unavailable.", "size": "lg",
                 "color": "white", "typewriter": True, "cursor": True, "delay": 36},
            ],
        },
    },
    "stats_grid": {
        "animate_in": "spring_in",
        "layout": {
            "type": "column", "gap": 48, "padding": 50,
            "children": [
                {"type": "TerminalText", "text": "Key stats", "size": "md", "color": "yellow"},
                {"type": "grid", "columns": 2, "gap": 24, "children": [
                    {"type": "LabelValueCard", "label": "N/A", "value": "N/A",
                     "border_color": "cyan", "delay": 15},
                    {"type": "LabelValueCard", "label": "N/A", "value": "N/A",
                     "border_color": "cyan", "delay": 21},
                ]},
            ],
        },
    },
    "pipeline": {
        "animate_in": "slide_up",
        "layout": {
            "type": "column", "gap": 32, "padding": 50,
            "children": [
                {"type": "TerminalText", "text": "Pipeline", "size": "md", "color": "cyan"},
                {"type": "LabelValueCard", "label": "Step 1", "value": "N/A",
                 "border_color": "cyan", "delay": 8},
                {"type": "LabelValueCard", "label": "Step 2", "value": "N/A",
                 "border_color": "cyan", "delay": 16},
                {"type": "LabelValueCard", "label": "Step 3", "value": "N/A",
                 "border_color": "cyan", "delay": 24},
            ],
        },
    },
    "comparison": {
        "animate_in": "fade",
        "layout": {
            "type": "column", "gap": 48, "padding": 50,
            "children": [
                {"type": "TerminalText", "text": "Before vs After", "size": "sm",
                 "color": "yellow"},
                {"type": "row", "gap": 32, "children": [
                    {"type": "column", "gap": 16, "children": [
                        {"type": "TerminalText", "text": "BEFORE", "size": "sm", "color": "red"},
                        {"type": "TerminalText", "text": "N/A", "size": "md", "color": "white"},
                    ]},
                    {"type": "column", "gap": 16, "children": [
                        {"type": "TerminalText", "text": "AFTER", "size": "sm", "color": "green"},
                        {"type": "TerminalText", "text": "N/A", "size": "md", "color": "white"},
                    ]},
                ]},
            ],
        },
    },
    "timeline": {
        "animate_in": "slide_up",
        "layout": {
            "type": "column", "gap": 32, "padding": 50,
            "children": [
                {"type": "TerminalText", "text": "Timeline", "size": "md", "color": "yellow"},
                {"type": "LabelValueCard", "label": "N/A", "value": "Event",
                 "border_color": "yellow", "delay": 8},
                {"type": "LabelValueCard", "label": "N/A", "value": "Event",
                 "border_color": "yellow", "delay": 16},
            ],
        },
    },
    "takeaway": {
        "animate_in": "typewriter",
        "layout": {
            "type": "column", "gap": 0, "padding": 50,
            "children": [
                {"type": "TerminalPrompt", "text": "user@adamax:~$"},
                {"type": "Spacer", "size": 700},
                {"type": "TerminalText", "text": "Run your own experiments.",
                 "size": "lg", "color": "white", "typewriter": True, "cursor": True, "delay": 0},
            ],
        },
    },
}


# ── Prompt ────────────────────────────────────────────────────────────────────

# Template hints tell the LLM what kind of visual story each beat should tell.
_TEMPLATE_HINTS = {
    "hook":       "Hero stat + short punchy phrase. Use StatBox for the number, TerminalText for the hook phrase.",
    "stats_grid": "Show 2–4 key metrics. Use a grid of LabelValueCard nodes. Short labels (≤5 chars), numeric values (≤8 chars).",
    "pipeline":   "Show a process as 3–5 sequential steps. Use LabelValueCard nodes stacked vertically.",
    "comparison": "Side-by-side before/after. Use a row container with two column children, each with a label and metric.",
    "timeline":   "Chronological events. Use staggered LabelValueCard nodes, label=year/version, value=event name.",
    "takeaway":   "Closing statement. Full-width TerminalText with typewriter effect. Bold, memorable, ≤12 words.",
}

_SCHEMA_REFERENCE = """\
NODE TYPES (all available):
  Containers (must have children):
    column  — vertical flex    props: gap, justify, align, padding, children
    row     — horizontal flex  props: gap, justify, align, children
    grid    — CSS grid         props: columns (2 or 3), gap, children

  Primitives (no children):
    TerminalPrompt  — "user@adamax:~$" style header  props: text
    TerminalText    — main text, optional typewriter  props: text, size, color, typewriter, cursor, delay
    StatBox         — hero metric (huge number)        props: value, label, color, animate, delay
    LabelValueCard  — bordered card                    props: label, value, border_color, color, glow, delay
    CodeBlock       — monospace block                  props: lines[], highlight_line
    Chip            — small inline badge               props: text, color
    Divider         — horizontal rule                  props: color, opacity
    Spacer          — whitespace                       props: size (px, integer)

ALLOWED VALUES:
  color / border_color: "green" | "cyan" | "yellow" | "red" | "white"
  size (TerminalText): "xs" | "sm" | "md" | "lg" | "xl"
  animate_in: "spring_in" | "spring_scale" | "typewriter" | "fade" | "slide_up" | "none"
  delay: integer ≥ 0 (frame offset for stagger — 30 frames = 1 second)

RULES:
  - Containers must have children. Primitives must NOT have children.
  - grid.columns must be 2 or 3.
  - text fields: ≤ 120 chars total, but keep SHORT — renders large on phone screen.
  - StatBox.value: ≤ 8 chars (e.g. "40%", "3B", "32GB").
  - LabelValueCard.label: ≤ 6 chars. LabelValueCard.value: ≤ 8 chars.
  - Use delay stagger (8, 16, 24 …) for cards that appear sequentially.
  - Every beat MUST start with a top-level "column" container."""


def build_prompt(topic: dict, script: dict, scene_plan: dict) -> str:
    hook     = script.get("hook", "")
    bullets  = script.get("concept_bullets", [])
    takeaway = script.get("takeaway", "")
    beats    = scene_plan.get("beats", [])

    # Map beats to their narration content
    middle_beats = [b for b in beats if b["template"] not in ("hook", "takeaway")]
    beat_content_lines = []
    for beat in beats:
        num      = beat["beat"]
        template = beat["template"]
        hint     = _TEMPLATE_HINTS.get(template, "")
        if template == "hook":
            narration = hook
        elif template == "takeaway":
            narration = takeaway
        else:
            mi = next((i for i, b in enumerate(middle_beats) if b["beat"] == num), None)
            narration = bullets[mi] if mi is not None and mi < len(bullets) else ""
        beat_content_lines.append(
            f"BEAT {num} (template hint: {template})\n"
            f"  Narration: {narration}\n"
            f"  Visual goal: {hint}"
        )

    beat_content = "\n\n".join(beat_content_lines)

    # Expected JSON shape
    json_parts = []
    for beat in beats:
        json_parts.append(
            f'  "beat_{beat["beat"]}": {{"animate_in": "...", "layout": {{"type": "column", "children": [...]}}}}'
        )
    json_shape = "{\n" + ",\n".join(json_parts) + "\n}"

    return f"""\
You are generating LayoutNode trees for a short AI explainer video.
Each beat gets a BeatLayout: {{ "animate_in": "...", "layout": <LayoutNode tree> }}

TOPIC: {topic.get('title', '')}
SUMMARY: {topic.get('summary', '')}

SCRIPT:
  hook:     {hook}
  takeaway: {takeaway}

PER-BEAT CONTENT:
{beat_content}

{_SCHEMA_REFERENCE}

DESIGN RULES:
- Terminal/hacker aesthetic: dark background (#0B0E14), monospace font.
- Start beats with TerminalPrompt for hook/takeaway beats.
- Use Spacer (size 600–800) to push content to vertical center on hook/takeaway beats.
- Colors: green = positive/metric, cyan = neutral info, yellow = label/header, red = negative.
- Keep text SHORT — it renders at 60–90px on a phone screen.
- Use stagger delays on LabelValueCard grids (delay: 8, 16, 24 …).

OUTPUT (exact JSON shape, no markdown fences, no extra fields):
{json_shape}

Return ONLY valid JSON. No explanation. No markdown.
"""


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    raw = re.sub(r",\s*([\]}])", r"\1", raw)
    return json.loads(raw)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with open(SCRIPT_PATH) as f:
        script = json.load(f)
    with open(TOPIC_PATH) as f:
        topic = json.load(f)
    with open(SCENE_PLAN_PATH) as f:
        scene_plan = json.load(f)

    beats    = scene_plan.get("beats", [])
    prompt   = build_prompt(topic, script, scene_plan)
    last_err = None
    params: dict = {}

    for attempt in range(1, 4):
        try:
            raw  = claude_client.call(prompt, stage="param_extractor", json_mode=True)
            data = _extract_json(raw)

            # Validate each beat; collect errors
            all_errors: list[str] = []
            for beat in beats:
                key = f"beat_{beat['beat']}"
                if key not in data:
                    all_errors.append(f"Missing {key}")
                else:
                    errs = _validate_beat_layout(data[key])
                    all_errors += [f"{key}: {e}" for e in errs]

            if all_errors:
                raise ValueError(f"Validation errors: {all_errors}")

            params   = data
            last_err = None
            break

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_err = e
            print(f"[param_extractor] attempt {attempt}/3 failed: {e} — retrying...")

    # Option A fallback: use static trees for any beat that failed
    if last_err:
        print(f"[param_extractor] All 3 attempts failed. Applying static fallback trees.")
        params = {}

    for beat in beats:
        key      = f"beat_{beat['beat']}"
        template = beat.get("template", "hook")
        if key not in params:
            print(f"  ⚠ {key}: using static fallback for template '{template}'")
            params[key] = STATIC_FALLBACK_TREES.get(
                template,
                STATIC_FALLBACK_TREES["hook"],
            )

    with open(OUTPUT_PATH, "w") as f:
        json.dump(params, f, indent=2)

    print(f"✓ Params saved → {OUTPUT_PATH}")
    for beat in beats:
        key = f"beat_{beat['beat']}"
        bl  = params.get(key, {})
        print(f"  {key}: animate_in={bl.get('animate_in')!r}  "
              f"root={bl.get('layout', {}).get('type')!r}  "
              f"children={len(bl.get('layout', {}).get('children', []))}")

    return params


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
