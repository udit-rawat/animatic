import json
import os

from pipeline import claude_client

INPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")


def build_prompt(topic: dict) -> str:
    return f"""\
You are writing on-screen text for a 60-second Manim animation for AI engineers.
These strings will be rendered directly as large text on a black screen — they are
NOT stage directions, NOT narration, NOT descriptions of visuals.
Every string must work as a standalone statement a viewer reads on screen.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}

OUTPUT RULES — critical:
- hook: 1 punchy sentence (≤12 words). The anomaly. Cold open. No "VISUAL:", no descriptions.
  GOOD: "52GB RSS. VRAM untouched. The server OOM-killed itself."
  BAD:  "VISUAL: Server rack showing memory usage climbing..."
- concept_bullets[0]: 1-2 short sentences (≤18 words total). The mechanism. Dense facts.
  GOOD: "MALLOC_ARENA_MAX=2 PYTORCH_NO_CUDA_MEMORY_CACHING=1. Two vars. Zero code changes."
  BAD:  "VISUAL: Graph showing RSS memory steadily climbing while VRAM stays flat..."
- concept_bullets[1]: 1-2 short sentences (≤18 words total). The contrast or proof.
  GOOD: "Before: RSS climbs 3GB/hour. After: flat line. Same model, same load."
  BAD:  "VISUAL: Split screen showing before/after terminal output..."
- takeaway: 1 sharp sentence ending in an unanswered question (≤15 words).
  GOOD: "The allocator was the leak. What else are you not watching?"
  BAD:  "VISUAL: Clean terminal showing free -h output..."

Language: system-terminal register — cold, precise, no warmth, no filler words.
NEVER write "VISUAL:", "Scene:", "Animation:", "Show", "Display" or any production note.

CAPTION: 2-3 sentences for Instagram/X. Open with the anomaly, close with a question.
HASHTAGS: exactly 5, mix of broad (#MachineLearning) and niche (#PyTorchTips) AI tags.

Respond with ONLY valid JSON:
{{
  "hook": "<1 punchy on-screen sentence>",
  "concept_bullets": [
    "<mechanism — short on-screen statement>",
    "<contrast/proof — short on-screen statement>"
  ],
  "takeaway": "<sharp closing question>",
  "cta": "",
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
