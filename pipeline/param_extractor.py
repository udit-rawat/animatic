"""
param_extractor.py — extracts per-beat visual params based on the scene plan.

Reads:
  output/script.json    — narration script
  output/topic.json     — topic metadata
  output/scene_plan.json — which template each beat uses (from scene_planner)

Output: output/params.json

Format:
  {
    "beat_1": {"template": "hook",       "hook_stat": "...", "hook_text": "..."},
    "beat_2": {"template": "stats_grid", "concept_text": "...", "grid_items": [...]},
    "beat_3": {"template": "comparison", "concept_text": "...", "before_label": "...", ...},
    "beat_4": {"template": "takeaway",   "takeaway_text": "..."}
  }

The LLM's ONLY job is to fill concrete data — it does NOT write any rendering code.
"""
import json
import os
import re

from pipeline import claude_client

SCRIPT_PATH    = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TOPIC_PATH     = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
SCENE_PLAN_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "scene_plan.json")
OUTPUT_PATH    = os.path.join(os.path.dirname(__file__), "..", "output", "params.json")


# ── Per-template field specs ──────────────────────────────────────────────────

TEMPLATE_SPECS = {
    "hook": """\
  hook_stat : ≤8 chars — pure number/unit. "40%", "3×", "32GB", "1080p". No sentences.
  hook_text : ≤8 words — sharpest phrase that makes someone stop scrolling.""",

    "stats_grid": """\
  concept_text : ≤7 words — what these stats describe. Punchy. NOT a full sentence.
  grid_items   : list of 2–6 objects. Each: {"label": "≤5 chars", "value": "≤8 chars"}
    GOOD labels: "VRAM", "BW", "TDP", "Price", "FLOPS", "Batch"
    GOOD values: "32GB", "608 GB/s", "290W", "$949", "2× faster", "100B"
    BAD:  {"label": "memory bandwidth", "value": "608 gigabytes per second"}""",

    "pipeline": """\
  concept_text   : ≤7 words — name the process. "Tiling fuses compute and memory".
  pipeline_steps : 3–5 items, each ≤6 chars. Acronyms preferred.
    GOOD: ["RAW", "ISP", "HEVC", "GPU"]   BAD: ["raw sensor data", "image signal processing"]""",

    "comparison": """\
  concept_text  : ≤7 words — the contrast in one phrase. "Before: 120ms. After: 72ms."
  before_label  : ≤6 chars — topic-specific name. NEVER "old"/"before". e.g. "FA2", "LSTM"
  after_label   : ≤6 chars — topic-specific name. NEVER "new"/"after". e.g. "FA3", "Mamba"
  before_detail : ≤5 words — one sharp metric fact. "120ms prefill"
  after_detail  : ≤5 words — one sharp metric fact. "72ms, 40% faster" """,

    "timeline": """\
  concept_text    : ≤7 words — what this timeline shows.
  timeline_events : 3–6 objects. Each: {"year": "≤6 chars", "label": "≤5 words"}
    GOOD years: "2017", "v2.0", "GPT-2", "2024Q1"
    GOOD labels: "Transformer paper", "First 1T model", "Open source era" """,

    "takeaway": """\
  takeaway_text : ≤12 words — closing statement. Big, bold, impactful.""",
}


TEMPLATE_JSON_SHAPES = {
    "hook":       '{"template": "hook", "hook_stat": "...", "hook_text": "..."}',
    "stats_grid": '{"template": "stats_grid", "concept_text": "...", "grid_items": [{"label": "...", "value": "..."}, ...]}',
    "pipeline":   '{"template": "pipeline", "concept_text": "...", "pipeline_steps": ["...", "...", "..."]}',
    "comparison": '{"template": "comparison", "concept_text": "...", "before_label": "...", "after_label": "...", "before_detail": "...", "after_detail": "..."}',
    "timeline":   '{"template": "timeline", "concept_text": "...", "timeline_events": [{"year": "...", "label": "..."}, ...]}',
    "takeaway":   '{"template": "takeaway", "takeaway_text": "..."}',
}


def build_prompt(topic: dict, script: dict, scene_plan: dict) -> str:
    hook     = script.get("hook", "")
    bullets  = script.get("concept_bullets", [])
    takeaway = script.get("takeaway", "")
    beats    = scene_plan.get("beats", [])

    # Build per-beat extraction spec
    beat_specs_lines = []
    for beat in beats:
        beat_num = beat["beat"]
        template = beat["template"]
        spec = TEMPLATE_SPECS.get(template, "")
        beat_specs_lines.append(f"BEAT {beat_num} (template: {template}):\n{spec}")

    beat_specs = "\n\n".join(beat_specs_lines)

    # Build expected JSON shape
    json_parts = []
    for beat in beats:
        beat_num = beat["beat"]
        template = beat["template"]
        shape = TEMPLATE_JSON_SHAPES.get(template, "{}")
        json_parts.append(f'  "beat_{beat_num}": {shape}')

    json_shape = "{\n" + ",\n".join(json_parts) + "\n}"

    # Map concept bullets to middle beats for context
    middle_beats = [b for b in beats if b["template"] not in ("hook", "takeaway")]
    bullet_context = ""
    for i, b in enumerate(middle_beats):
        bullet = bullets[i] if i < len(bullets) else ""
        bullet_context += f"  beat_{b['beat']} draws from concept_bullet_{i+1}: {bullet}\n"

    return f"""\
You are extracting structured visual parameters from a short video script.
Parameters slot into fixed Manim templates — you are NOT writing code.

TOPIC: {topic.get('title', '')}
TOPIC SUMMARY: {topic.get('summary', '')}

SCRIPT:
  hook:     {hook}
{bullet_context}  takeaway: {takeaway}

CRITICAL — all text renders LARGE on a phone screen. Keep everything SHORT.
Word/char limits are HARD. Count before outputting. Rewrite to fit.

PER-BEAT EXTRACTION SPEC:
{beat_specs}

GENERAL RULES:
- pipeline_steps / grid_items: use topic-specific terms, never generic placeholders
- before_label / after_label: never "old"/"new", never "before"/"after"
- concept_text: a punchy phrase, NOT a full sentence, NOT a question
- grid_items values: prefer numbers with units ("32GB", "290W") over prose
- If a stat has no clear "before" state, it's stats_grid, not comparison
- timeline_events: real chronological dates/versions, not narrative phases

OUTPUT JSON (exact shape, no extra fields):
{json_shape}

Return ONLY valid JSON. No markdown fences, no explanation.
"""


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


def _validate(params: dict, scene_plan: dict):
    beats = scene_plan.get("beats", [])
    for beat in beats:
        beat_num = beat["beat"]
        template = beat["template"]
        key = f"beat_{beat_num}"
        assert key in params, f"Missing {key} in params"
        b = params[key]
        if template == "hook":
            assert "hook_stat" in b and "hook_text" in b
        elif template == "stats_grid":
            assert "concept_text" in b
            assert "grid_items" in b and len(b["grid_items"]) >= 2
        elif template == "pipeline":
            assert "concept_text" in b
            assert "pipeline_steps" in b and len(b["pipeline_steps"]) >= 3
        elif template == "comparison":
            assert "concept_text" in b
            assert "before_label" in b and "after_label" in b
        elif template == "timeline":
            assert "concept_text" in b
            assert "timeline_events" in b and len(b["timeline_events"]) >= 2
        elif template == "takeaway":
            assert "takeaway_text" in b


def main():
    with open(SCRIPT_PATH) as f:
        script = json.load(f)
    with open(TOPIC_PATH) as f:
        topic = json.load(f)
    with open(SCENE_PLAN_PATH) as f:
        scene_plan = json.load(f)

    prompt   = build_prompt(topic, script, scene_plan)
    last_err = None

    for attempt in range(1, 4):
        try:
            raw    = claude_client.call(prompt, stage="param_extractor", json_mode=True)
            params = _extract_json(raw)
            _validate(params, scene_plan)
            last_err = None
            break
        except (json.JSONDecodeError, KeyError, AssertionError, ValueError) as e:
            last_err = e
            print(f"[param_extractor] attempt {attempt}/3 failed: {e} — retrying...")

    if last_err:
        raise RuntimeError(f"Param extractor failed after 3 attempts. Last error: {last_err}")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(params, f, indent=2)

    print(f"✓ Params saved → {OUTPUT_PATH}")
    for beat in scene_plan.get("beats", []):
        key = f"beat_{beat['beat']}"
        b = params.get(key, {})
        tpl = beat["template"]
        if tpl == "hook":
            print(f"  {key}: stat={b.get('hook_stat')!r}  text={b.get('hook_text')!r}")
        elif tpl == "stats_grid":
            labels = [i.get("label") for i in b.get("grid_items", [])]
            print(f"  {key}: grid={labels}")
        elif tpl == "pipeline":
            print(f"  {key}: steps={b.get('pipeline_steps')}")
        elif tpl == "comparison":
            print(f"  {key}: {b.get('before_label')} → {b.get('after_label')}")
        elif tpl == "timeline":
            years = [e.get("year") for e in b.get("timeline_events", [])]
            print(f"  {key}: events={years}")
        elif tpl == "takeaway":
            print(f"  {key}: {b.get('takeaway_text')!r}")

    return params


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
