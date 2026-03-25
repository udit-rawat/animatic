import json
import os

from pipeline import claude_client

INPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")


def build_prompt(topic: dict) -> str:
    return f"""\
You are writing on-screen text for a short Manim animation targeting AI engineers on TikTok/Shorts.
These strings render as LARGE TEXT on a dark screen — they must be immediately readable and
create curiosity, not describe what's happening.
NOT stage directions. NOT narration. NOT descriptions of visuals. Just the words on screen.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}

OUTPUT RULES:

hook (≤12 words):
  The curiosity gap opener. State the unexpected fact or contradiction that makes someone stop scrolling.
  Short words. High contrast. Should create a "wait, how?" reaction.
  GOOD: "52GB RSS. VRAM untouched. Server OOM-killed itself."
  GOOD: "Two env vars. No code changes. 40% less memory."
  BAD:  "Today we explore memory allocation issues in PyTorch."

concept_bullets[0] (≤18 words total):
  The mechanism — how it works. Dense facts. Must name 3-5 concrete stages or components.
  GOOD: "MALLOC_ARENA_MAX=2. Caps glibc arenas. RSS drops immediately."
  BAD:  "Setting this variable controls how memory is allocated by the system."

concept_bullets[1] (≤18 words total):
  The proof — the before/after contrast with real numbers. Name both states specifically.
  GOOD: "Before: RSS climbs 3GB/hour. After: flat. Same model, same load."
  BAD:  "The results show significant improvement in memory usage patterns."

takeaway (≤15 words):
  The aha-moment + an open question that lingers. Punchy. Slightly uncomfortable.
  GOOD: "The allocator was the leak. What else are you not measuring?"
  BAD:  "This shows the importance of monitoring all system resources carefully."

NEVER write "VISUAL:", "Scene:", "Animation:", "Show", "Display", or any production note.
Language: direct, factual, punchy — like a tweet from an engineer who just shipped a fix.

CAPTION: 2-3 sentences for Instagram/X. Lead with the hook, close with the question.
HASHTAGS: exactly 5, mix of broad (#MachineLearning) and specific (#PyTorchTips, #MLOps) AI tags.

Respond with ONLY valid JSON:
{{
  "hook": "<curiosity gap — ≤12 words>",
  "concept_bullets": [
    "<mechanism — ≤18 words with concrete component names>",
    "<before/after proof — ≤18 words with real numbers>"
  ],
  "takeaway": "<aha-moment + open question — ≤15 words>",
  "cta": "",
  "caption": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
}}
"""


def extract_json(raw: str) -> dict:
    import re
    # Strip markdown fences
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    # Find first { ... } block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        candidate = raw[start:end]
    else:
        candidate = raw.strip()
    # Repair: remove trailing commas before ] or }
    candidate = re.sub(r',\s*([\]}])', r'\1', candidate)
    return json.loads(candidate)


def main():
    with open(INPUT_PATH) as f:
        topic = json.load(f)

    prompt = build_prompt(topic)
    last_err = None
    for attempt in range(1, 4):
        try:
            raw = claude_client.call(prompt, stage="scripter", json_mode=True)
            script = extract_json(raw)
            break
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_err = e
            print(f"[scripter] JSON parse failed (attempt {attempt}/3): {e} — retrying...")
    else:
        raise RuntimeError(f"Scripter failed to produce valid JSON after 3 attempts. Last error: {last_err}")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(script, f, indent=2)

    print(f"Script saved → {OUTPUT_PATH}")
    print(f"Hook: {script['hook']}")
    return script


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
