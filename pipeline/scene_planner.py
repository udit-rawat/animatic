"""
scene_planner.py — classifies which visual template each script beat should use.

Runs AFTER scripter, BEFORE narrator and param_extractor.
Output: output/scene_plan.json

Beat 1 (hook) and last beat (takeaway) are always fixed.
Middle beats are classified by the LLM based on content type.

Available middle templates:
  pipeline    — step-by-step process flow (A→B→C→D)
  comparison  — side-by-side before/after or A vs B
  stats_grid  — grid of labeled stat cards (specs, benchmarks)
  timeline    — vertical sequence of dated/ordered events
"""
import json
import os
import re

from pipeline import claude_client

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TOPIC_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "scene_plan.json")

MIDDLE_TEMPLATES = {
    "pipeline":   "A step-by-step process flow (A→B→C→D). Best for: algorithms, training loops, data pipelines, build processes — anything with 3-5 named sequential stages.",
    "comparison": "Side-by-side before/after or A vs B. Best for: two competing approaches with a clear winner, old vs new architecture — requires a concrete measurable difference.",
    "stats_grid": "Grid of 2-6 labeled stat cards (label + value). Best for: hardware specs, benchmark numbers, multi-metric callouts, feature scorecards. Use whenever there are 2+ named statistics.",
    "timeline":   "Vertical sequence of dated or ordered events. Best for: history of a technology, version release milestones, research evolution — requires chronological structure.",
}


def build_prompt(topic: dict, script: dict) -> str:
    bullets = script.get("concept_bullets", [])
    b1 = bullets[0] if bullets else ""
    b2 = bullets[1] if len(bullets) > 1 else ""
    b3 = bullets[2] if len(bullets) > 2 else ""

    tpl_desc = "\n".join(f'  "{k}": {v}' for k, v in MIDDLE_TEMPLATES.items())

    return f"""\
You are a visual template classifier for short-form tech explainer videos.

TOPIC: {topic.get('title', '')}
SUMMARY: {topic.get('summary', '')}

SCRIPT CONCEPT BULLETS:
  concept_1: {b1}
  concept_2: {b2}
  concept_3: {b3}

AVAILABLE MIDDLE BEAT TEMPLATES:
{tpl_desc}

TASK: Assign one template to each concept bullet that has real content.
- Beat 1 = hook (always fixed)
- Beat N = takeaway (always fixed, renumber to last)
- Middle beats = 1–3 beats depending on how many concept_bullets have real content

CLASSIFICATION RULES (strict priority order):
1. If a concept bullet contains named specs, benchmarks, or 2+ statistics → "stats_grid"
2. If a concept bullet describes named sequential stages → "pipeline"
3. If a concept bullet contrasts two named things with measurable difference → "comparison"
4. If a concept bullet lists events with dates/versions → "timeline"
5. Never use "pipeline" for a list of specs — specs are "stats_grid"
6. Skip concept bullets that are empty or duplicate the hook

OUTPUT JSON:
{{
  "beats": [
    {{"beat": 1, "template": "hook"}},
    {{"beat": 2, "template": "<one of the 4 templates>"}},
    {{"beat": 3, "template": "<one of the 4 templates or omit if no content>"}},
    {{"beat": 4, "template": "takeaway"}}
  ]
}}

Rules:
- Always include beat 1 (hook) and the last beat (takeaway)
- Only include middle beats for concept bullets with real, distinct content
- Renumber beats sequentially starting from 1
- Return ONLY valid JSON. No markdown, no explanation.
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


def _renumber(plan: dict) -> dict:
    """Ensure beat numbers are sequential 1…N regardless of what LLM output."""
    beats = plan.get("beats", [])
    for i, b in enumerate(beats):
        b["beat"] = i + 1
    return plan


def main():
    with open(SCRIPT_PATH) as f:
        script = json.load(f)
    with open(TOPIC_PATH) as f:
        topic = json.load(f)

    prompt   = build_prompt(topic, script)
    last_err = None

    for attempt in range(1, 4):
        try:
            raw  = claude_client.call(prompt, stage="scene_planner", json_mode=True)
            plan = _extract_json(raw)
            plan = _renumber(plan)
            beats = plan.get("beats", [])
            assert len(beats) >= 3, "Need at least 3 beats (hook + 1 middle + takeaway)"
            assert beats[0]["template"] == "hook", "Beat 1 must be hook"
            assert beats[-1]["template"] == "takeaway", "Last beat must be takeaway"
            for b in beats[1:-1]:
                assert b["template"] in MIDDLE_TEMPLATES, f"Unknown template: {b['template']}"
            last_err = None
            break
        except (json.JSONDecodeError, KeyError, AssertionError, ValueError) as e:
            last_err = e
            print(f"[scene_planner] attempt {attempt}/3 failed: {e} — retrying...")

    if last_err:
        print(f"[scene_planner] all attempts failed, using default plan")
        plan = {
            "beats": [
                {"beat": 1, "template": "hook"},
                {"beat": 2, "template": "stats_grid"},
                {"beat": 3, "template": "comparison"},
                {"beat": 4, "template": "takeaway"},
            ]
        }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(plan, f, indent=2)

    templates = [b["template"] for b in plan["beats"]]
    print(f"✓ Scene plan → {OUTPUT_PATH}")
    print(f"  Flow: {' → '.join(templates)}")
    return plan


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
