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
    # Tier 2 — devtool design system (preferred)
    "MetricCard", "GPUNode", "NumberCounter", "SectionLabel",
    # Legacy — kept for fallback compatibility
    "TerminalPrompt", "TerminalText",
    "StatBox", "LabelValueCard",
    "CodeBlock", "Chip",
    "Divider", "Spacer",
}
_ALLOWED_GPU_STATES = {"idle", "active", "bottleneck"}
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

    if node_type == "GPUNode":
        state = node.get("state")
        if state and state not in _ALLOWED_GPU_STATES:
            errors.append(f"GPUNode.state must be idle|active|bottleneck, got {state!r}")

    delay = node.get("delay")
    if delay is not None and (not isinstance(delay, (int, float)) or delay < 0):
        errors.append(f"delay must be non-negative number, got {delay!r}")

    cue = node.get("cue")
    if cue is not None and not isinstance(cue, str):
        errors.append(f"cue must be a string label, got {type(cue).__name__}")

    text = node.get("text", "")
    if text and len(text) > 120:
        errors.append(f"text too long ({len(text)} chars) in node '{node_type}'")

    for child in children:
        if not isinstance(child, dict):
            errors.append(f"Child of '{node_type}' must be an object, got {type(child).__name__}")
            continue
        errors += _validate_layout_node(child, depth + 1)

    return errors


def _validate_beat_layout(beat_layout: dict, template: str = "") -> list[str]:
    """Validate a BeatLayout dict: { animate_in, layout }."""
    errors: list[str] = []
    animate_in = beat_layout.get("animate_in")
    if animate_in not in _ALLOWED_ANIMATE_IN:
        errors.append(f"Invalid animate_in {animate_in!r}")
    if "layout" not in beat_layout:
        errors.append("Missing 'layout' field")
        return errors
    layout = beat_layout["layout"]

    # Enforce root column padding ≥ 40
    if layout.get("type") == "column":
        padding = layout.get("padding", 0)
        if not isinstance(padding, (int, float)) or padding < 40:
            errors.append(f"Root column padding must be ≥ 40, got {padding!r}")

    # Enforce SectionLabel (or legacy TerminalPrompt) as first child on hook/takeaway beats
    if template in ("hook", "takeaway"):
        children = layout.get("children", [])
        first_type = children[0].get("type") if children else None
        if first_type not in ("SectionLabel", "TerminalPrompt"):
            errors.append(
                f"Beat '{template}' must start with SectionLabel as first child, got {first_type!r}"
            )

    errors += _validate_layout_node(layout)
    return errors


# ── Static fallback trees (Option A — always renders) ─────────────────────────

STATIC_FALLBACK_TREES: dict[str, dict] = {
    "hook": {
        "animate_in": "spring_scale",
        "layout": {
            "type": "column", "gap": 32, "padding": 60,
            "children": [
                {"type": "SectionLabel", "text": "adamax.ai", "color": "cyan"},
                {"type": "Spacer", "size": 650},
                {"type": "NumberCounter", "value": "N/A", "label": "metric",
                 "color": "cyan", "delay": 0},
                {"type": "Spacer", "size": 32},
                {"type": "TerminalText", "text": "Data unavailable.", "size": "lg",
                 "color": "white", "typewriter": True, "cursor": True, "delay": 20},
            ],
        },
    },
    "stats_grid": {
        "animate_in": "spring_in",
        "layout": {
            "type": "column", "gap": 32, "padding": 60,
            "children": [
                {"type": "SectionLabel", "text": "Key Stats", "color": "yellow"},
                {"type": "Divider", "color": "cyan", "opacity": 0.15},
                {"type": "grid", "columns": 2, "gap": 20, "children": [
                    {"type": "MetricCard", "label": "N/A", "value": "N/A",
                     "color": "cyan", "delay": 0},
                    {"type": "MetricCard", "label": "N/A", "value": "N/A",
                     "color": "cyan", "delay": 8},
                ]},
            ],
        },
    },
    "pipeline": {
        "animate_in": "slide_up",
        "layout": {
            "type": "column", "gap": 32, "padding": 60,
            "children": [
                {"type": "SectionLabel", "text": "How It Works", "color": "yellow"},
                {"type": "Divider", "color": "cyan", "opacity": 0.15},
                {"type": "MetricCard", "label": "Step 1", "value": "N/A",
                 "color": "cyan", "delay": 0},
                {"type": "MetricCard", "label": "Step 2", "value": "N/A",
                 "color": "cyan", "delay": 8},
                {"type": "MetricCard", "label": "Step 3", "value": "N/A",
                 "color": "green", "delay": 16},
            ],
        },
    },
    "comparison": {
        "animate_in": "fade",
        "layout": {
            "type": "column", "gap": 32, "padding": 60,
            "children": [
                {"type": "SectionLabel", "text": "Before vs After", "color": "yellow"},
                {"type": "Divider", "color": "cyan", "opacity": 0.15},
                {"type": "row", "gap": 24, "children": [
                    {"type": "column", "gap": 16, "children": [
                        {"type": "SectionLabel", "text": "Before", "color": "red"},
                        {"type": "MetricCard", "label": "N/A", "value": "N/A",
                         "color": "red", "delay": 0},
                    ]},
                    {"type": "column", "gap": 16, "children": [
                        {"type": "SectionLabel", "text": "After", "color": "cyan"},
                        {"type": "MetricCard", "label": "N/A", "value": "N/A",
                         "color": "cyan", "glow": True, "delay": 8},
                    ]},
                ]},
            ],
        },
    },
    "timeline": {
        "animate_in": "slide_up",
        "layout": {
            "type": "column", "gap": 32, "padding": 60,
            "children": [
                {"type": "SectionLabel", "text": "Timeline", "color": "yellow"},
                {"type": "Divider", "color": "yellow", "opacity": 0.15},
                {"type": "MetricCard", "label": "N/A", "value": "Event",
                 "color": "yellow", "delay": 0},
                {"type": "MetricCard", "label": "N/A", "value": "Event",
                 "color": "yellow", "delay": 8},
            ],
        },
    },
    "takeaway": {
        "animate_in": "typewriter",
        "layout": {
            "type": "column", "gap": 32, "padding": 60,
            "children": [
                {"type": "SectionLabel", "text": "adamax.ai", "color": "cyan"},
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
    "hook":       "Hero metric + punchy phrase. Use NumberCounter for the big number (delay:0), TerminalText for the hook phrase (delay:20). SectionLabel at top.",
    "stats_grid": "2–4 key metrics in a grid. Use MetricCard nodes (NOT LabelValueCard). label ≤6 chars, value ≤8 chars. Stagger delay 0,8,16,24.",
    "pipeline":   "3–5 sequential steps. Use MetricCard nodes stacked vertically, label=step name, value=output or result.",
    "comparison": "Side-by-side. Use a row of two columns: each column has SectionLabel (BEFORE/AFTER) + MetricCard.",
    "timeline":   "Chronological. Use MetricCard nodes, label=year/version, value=event keyword.",
    "takeaway":   "Closing statement. SectionLabel at top, large Spacer, then TerminalText with typewriter:true, cursor:true.",
}

_SCHEMA_REFERENCE = """\
NODE TYPES — use Tier 2 primitives by default:

  Containers (must have children):
    column  — vertical flex    props: gap, justify, align, padding, children
    row     — horizontal flex  props: gap, justify, align, children
    grid    — CSS grid         props: columns (2 or 3), gap, children

  Tier 2 primitives — PREFERRED (devtool aesthetic):
    SectionLabel   — section header with accent bar   props: text, color
    NumberCounter  — huge hero metric, scale spring   props: value, label, color, delay
    MetricCard     — glassmorphism data card          props: label, value, color, glow, delay
    GPUNode        — GPU tile for cluster visuals     props: label, value, state, delay
                     state: "idle" | "active" | "bottleneck"

  Supporting primitives:
    TerminalText   — body text, typewriter option     props: text, size, color, typewriter, cursor, delay
    Divider        — 1px separator line               props: color, opacity
    Spacer         — vertical whitespace              props: size (px integer)
    Chip           — pill badge                       props: text, color
    CodeBlock      — code block with highlight        props: lines[], highlight_line

ALLOWED VALUES:
  color: "green"(emerald) | "cyan"(indigo) | "yellow"(violet) | "red" | "white"
  state (GPUNode only): "idle" | "active" | "bottleneck"
  size (TerminalText): "xs" | "sm" | "md" | "lg" | "xl"
  animate_in: "spring_in" | "spring_scale" | "typewriter" | "fade" | "slide_up" | "none"
  delay: integer ≥ 0 (frames — 30 frames = 1 second)
  cue: string (optional) — named cue from cue_definitions.json; when set, animation starts
       when the cue fires instead of at the fixed delay. Standard labels: "metric_reveal",
       "before_after_split", "insight_drop", "key_number", "bottleneck_reveal", "takeaway_flash"

STRUCTURAL RULES (validator enforced — violations cause retry):
  - Root "column" MUST have padding ≥ 40 (use 60) and gap: 32.
  - hook beats: first child MUST be SectionLabel, then Spacer 600–750, then NumberCounter or TerminalText.
  - takeaway beats: first child MUST be SectionLabel, then Spacer 650–800, then TerminalText typewriter.
  - Middle beats: first child MUST be SectionLabel (section header), then Divider, then data nodes.
  - Containers must have children. Primitives must NOT have children.
  - grid.columns must be 2 or 3.
  - text/label/value: keep SHORT — renders at 50–200px on phone screen.
  - NumberCounter.value ≤ 8 chars. MetricCard.label ≤ 8 chars. MetricCard.value ≤ 8 chars.
  - Stagger MetricCard/GPUNode delays: 0, 8, 16, 24 …

REFERENCE TREES (copy structure exactly, replace values):

hook beat:
  {"type":"column","padding":60,"gap":32,"children":[
    {"type":"SectionLabel","text":"adamax.ai","color":"cyan"},
    {"type":"Spacer","size":650},
    {"type":"NumberCounter","value":"3.8×","label":"throughput gain","color":"cyan","delay":0},
    {"type":"Spacer","size":32},
    {"type":"TerminalText","text":"One config change. Same 96 GPUs.","size":"lg","color":"white","delay":20}
  ]}

stats_grid beat:
  {"type":"column","padding":60,"gap":32,"children":[
    {"type":"SectionLabel","text":"Benchmark","color":"yellow"},
    {"type":"Divider","color":"cyan","opacity":0.15},
    {"type":"grid","columns":2,"gap":20,"children":[
      {"type":"MetricCard","label":"TP=8","value":"290K t/s","color":"red","delay":0},
      {"type":"MetricCard","label":"DP=8","value":"1.1M t/s","color":"cyan","glow":true,"delay":8}
    ]}
  ]}

pipeline beat:
  {"type":"column","padding":60,"gap":32,"children":[
    {"type":"SectionLabel","text":"How it works","color":"yellow"},
    {"type":"Divider","color":"cyan","opacity":0.15},
    {"type":"MetricCard","label":"Step 1","value":"Tokenize","color":"cyan","delay":0},
    {"type":"MetricCard","label":"Step 2","value":"Encode","color":"cyan","delay":8},
    {"type":"MetricCard","label":"Step 3","value":"Decode","color":"green","delay":16}
  ]}

comparison beat:
  {"type":"column","padding":60,"gap":32,"children":[
    {"type":"SectionLabel","text":"Before vs After","color":"yellow"},
    {"type":"Divider","color":"cyan","opacity":0.15},
    {"type":"row","gap":24,"children":[
      {"type":"column","gap":16,"children":[
        {"type":"SectionLabel","text":"Before","color":"red"},
        {"type":"MetricCard","label":"TP=8","value":"290K t/s","color":"red","delay":0}
      ]},
      {"type":"column","gap":16,"children":[
        {"type":"SectionLabel","text":"After","color":"cyan"},
        {"type":"MetricCard","label":"DP=8","value":"1.1M t/s","color":"cyan","glow":true,"delay":8}
      ]}
    ]}
  ]}

takeaway beat:
  {"type":"column","padding":60,"gap":32,"children":[
    {"type":"SectionLabel","text":"adamax.ai","color":"cyan"},
    {"type":"Spacer","size":700},
    {"type":"TerminalText","text":"The bottleneck was coordination. Not compute.","size":"lg","color":"white","typewriter":true,"cursor":true,"delay":0}
  ]}"""


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

DESIGN RULES (non-negotiable):
- Root column MUST have padding: 60 and gap: 32. Validator rejects padding < 40.
- hook/takeaway beats: MUST have SectionLabel as FIRST child, then Spacer 650–800, then content.
- Middle beats: MUST start with SectionLabel as section header, then Divider, then data nodes.
- Use MetricCard instead of LabelValueCard. Use NumberCounter instead of StatBox. Use SectionLabel instead of TerminalPrompt.
- Colors: green(emerald)=positive, cyan(indigo)=primary/neutral, yellow(violet)=headers, red=negative.
- Keep text SHORT — renders at 50–200px on phone. MetricCard.value ≤ 8 chars.
- Stagger MetricCard/GPUNode: delay 0, 8, 16, 24 …
- Follow the REFERENCE TREES above exactly — copy structure, replace values with real content.

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
                key      = f"beat_{beat['beat']}"
                template = beat.get("template", "")
                if key not in data:
                    all_errors.append(f"Missing {key}")
                else:
                    errs = _validate_beat_layout(data[key], template=template)
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
