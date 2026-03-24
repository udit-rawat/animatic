import json
import os

from pipeline import claude_client

INPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")


def build_prompt(topic: dict) -> str:
    return f"""\
You are a short-form video scriptwriter for AI engineers on Instagram and X (Twitter).
You write 60-second dopamine-loop Manim explainer scripts. Every word must earn its place.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}
SOURCE: {topic['url']}

FORMAT: 60 seconds total, structured as 4 beats:
  Beat 1 — The Anomaly     (0s-10s):  1-2 sentences that break expectation
  Beat 2 — The Collapse    (10s-25s): 2-3 sentences showing the mechanism
  Beat 3 — The Contrast    (25s-45s): 2-3 sentences — early vs deep, simple vs complex
  Beat 4 — The Hook Loop   (45s-60s): 1-2 provocative sentences that force a rewatch

SCRIPT REQUIREMENTS:
- Every beat maps to a distinct visual moment — write what you SEE, not what you say
- Language: system-terminal register — cold, precise, no warmth, no filler
- End Beat 4 with the exact text: "Follow for daily AI breakdowns."

CAPTION: 2-3 sentences for Instagram/X — open with the anomaly, close with a question that drives saves

HASHTAGS: exactly 5, mix of broad and niche AI engineering tags

Respond with ONLY valid JSON:
{{
  "hook": "<Beat 1 — The Anomaly>",
  "concept_bullets": [
    "<Beat 2 — The Collapse visual>",
    "<Beat 3 — The Contrast visual>"
  ],
  "takeaway": "<Beat 4 — The Hook Loop>",
  "cta": "Follow for daily AI breakdowns.",
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
    raw = claude_client.call(prompt, stage="scripter", json_mode=True)
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
