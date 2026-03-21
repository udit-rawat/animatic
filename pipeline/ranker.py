import json
import os

from pipeline import claude_client

INPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "candidates.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")

# ── Discovery prompt ────────────────────────────────────────────────────────
# Optimised for: AI engineering audience, 60-second Manim explainer,
# Instagram/X short-form. Prioritises visual potential + engineer value.
PROMPT_TEMPLATE = """\
You are a content strategist for an AI engineering audience on Instagram and X (Twitter).
Your job: pick ONE topic from the candidates below that will make the best 60-second Manim animation.

SCORING CRITERIA — rate each candidate 1–10 on four dimensions:

1. VISUAL POTENTIAL — Can this be shown as clean, self-evident animations?
   High: step-by-step algorithms, architecture diagrams, before/after comparisons, quantitative charts
   Low: opinion pieces, vague industry trends, text-heavy arguments

2. ENGINEER VALUE — Will a working ML/AI engineer learn something immediately actionable or surprising?
   High: a technique they can test today, a benchmark that changes best practices, a paper with a concrete trick
   Low: general hype, things every engineer already knows, marketing posts

3. FRESHNESS — Is this genuinely new or newly relevant?
   High: paper from the last 72 hours, a newly released model/tool, a result that overturns prior assumptions
   Low: rehashed fundamentals, evergreen content dressed up as news

4. FOCUS — Can the core idea be fully explained in 60 seconds with 3–4 visual steps?
   High: one concrete mechanism or benchmark result
   Low: broad surveys, multi-paper comparisons, "state of X" overviews

IDEAL TOPIC EXAMPLES (use as a calibration bar):
- "Flash Attention 3 cuts prefill latency 40%% — here's the tiling trick behind it"
- "Why LoRA rank matters: a visual guide to rank-1 vs rank-64 weight updates"
- "Speculative decoding: how a small draft model makes large models 3× faster"
- "Grouped-query attention: the small change that halved KV-cache memory in Llama 3"

STRICTLY AVOID:
- "AI is changing everything"-style posts
- Topics requiring more than 4 visual steps to explain clearly
- Papers with no public abstract or open access
- Topics that are purely mathematical with no intuitive visual hook

CANDIDATES:
{candidates}

Select the single best candidate. Respond with ONLY valid JSON — no explanation outside the JSON:
{{
  "title": "...",
  "summary": "...",
  "url": "...",
  "source": "...",
  "why_picked": "one sentence: what makes it visually teachable in 60 seconds"
}}
"""


def build_prompt(candidates: list[dict]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. [{c['source']}] {c['title']}")
        lines.append(f"   Summary: {c['summary']}")
        lines.append(f"   URL: {c['url']}")
        lines.append("")
    return PROMPT_TEMPLATE.format(candidates="\n".join(lines))


def extract_json(raw: str) -> dict:
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                return json.loads(part)
    return json.loads(raw.strip())


def main():
    with open(INPUT_PATH) as f:
        candidates = json.load(f)

    prompt = build_prompt(candidates)
    raw = claude_client.call(prompt, stage="ranker")
    topic = extract_json(raw)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(topic, f, indent=2)

    print(f"Selected: {topic['title']}")
    print(f"Why: {topic['why_picked']}")
    print(f"Saved → {OUTPUT_PATH}")
    return topic


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
