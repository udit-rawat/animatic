import json
import os

from pipeline import claude_client

INPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")


def build_prompt(topic: dict, correction: str | None = None) -> str:
    correction_block = ""
    if correction:
        correction_block = f"""
CORRECTION DIRECTIVE — a previous draft was rejected by the fact-checker.
You MUST fix the following before writing the new script:
{correction}
Do NOT repeat any of the hallucinated or contradicted claims above.

"""
    return f"""\
You are writing on-screen text for a short Manim animation targeting AI engineers on TikTok/Shorts.
These strings render as LARGE TEXT on a dark screen — they must be immediately readable and
create curiosity, not describe what's happening.
NOT stage directions. NOT narration. NOT descriptions of visuals. Just the words on screen.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}
{correction_block}OUTPUT RULES:

hook (≤12 words):
  Open with FRICTION. State the unexpected pain point, contradiction, or broken assumption.
  DO NOT state what the tool or solution is yet. Just the problem or metric.
  GOOD: "52GB RSS. VRAM untouched. Server OOM-killed itself."
  GOOD: "Your GPU is idle, but your latency is 400ms. Why?"

concept_bullets[0] (≤18 words total):
  The mechanism. Drop the corporate tone. Sound like a hacker explaining it in a Slack channel.
  Name the exact variable, architecture block, or technique. No vague descriptions.

concept_bullets[1] (≤18 words total):
  The hard proof. State the benchmark delta explicitly: Before X → After Y.
  Real numbers only. No hedging. No "up to" or "approximately".

takeaway (≤15 words):
  End with a statement that proves their intuition might be wrong, directly challenging the reader.
  GOOD: "The allocator was the leak. Could you have spotted this?"
  GOOD: "Two vars fixed it. What else in your stack are you not measuring?"

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


def generate_script(topic: dict, correction: str | None = None) -> dict:
    """Generate script JSON. Pass correction= to inject fact-checker feedback."""
    prompt   = build_prompt(topic, correction=correction)
    last_err = None
    for attempt in range(1, 4):
        try:
            raw    = claude_client.call(prompt, stage="scripter", json_mode=True)
            script = extract_json(raw)
            return script
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_err = e
            print(f"[scripter] JSON parse failed (attempt {attempt}/3): {e} — retrying...")
    raise RuntimeError(f"Scripter failed after 3 attempts. Last error: {last_err}")


def main():
    with open(INPUT_PATH) as f:
        topic = json.load(f)

    script = generate_script(topic)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(script, f, indent=2)

    print(f"Script saved → {OUTPUT_PATH}")
    print(f"Hook: {script['hook']}")
    return script


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
