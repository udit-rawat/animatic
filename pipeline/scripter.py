import json
import os

from pipeline import claude_client

INPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")


def build_prompt(topic: dict) -> str:
    return f"""\
You are a short-form video scriptwriter for AI engineers on Instagram and X (Twitter).
You write 60-second Manim explainer scripts. Every word must earn its place.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}
SOURCE: {topic['url']}

SCRIPT REQUIREMENTS:
- Hook must create genuine curiosity or surprise in the first 5 seconds
- Concept bullets must be visual — each one describes something you can SHOW, not just say
- Takeaway must be a single insight an engineer can carry into their next project
- Language: direct, technical, zero fluff — write for people who read papers

Write the script using EXACTLY this structure, then immediately output the JSON:

HOOK (0-5s): <one punchy sentence — lead with the surprising result or counterintuitive claim>

CONCEPT (5-45s):
- <bullet 1: describe the first visual to show>
- <bullet 2: describe the second visual to show>
- <bullet 3: describe the third visual to show>
- <bullet 4: optional fourth visual if needed>

TAKEAWAY (45-55s): <one clear, memorable, actionable insight>

CTA (55-60s): "Follow for daily AI breakdowns"

CAPTION: <2-3 sentences for Instagram/X — open with the hook, end with a question or provocation that drives saves/shares>

HASHTAGS: <exactly 5 hashtags for AI engineers, mix of broad and niche>

Then respond with ONLY valid JSON — no text before or after:
{{
  "hook": "...",
  "concept_bullets": ["...", "...", "...", "..."],
  "takeaway": "...",
  "cta": "Follow for daily AI breakdowns",
  "caption": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
}}
"""


def extract_json(raw: str) -> dict:
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                return json.loads(part)
    # Find first { ... } block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(raw[start:end])
    return json.loads(raw.strip())


def main():
    with open(INPUT_PATH) as f:
        topic = json.load(f)

    prompt = build_prompt(topic)
    raw = claude_client.call(prompt, stage="scripter")
    script = extract_json(raw)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(script, f, indent=2)

    print(f"Script saved → {OUTPUT_PATH}")
    print(f"Hook: {script['hook']}")
    return script


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
