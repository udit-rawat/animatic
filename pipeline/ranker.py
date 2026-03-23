import json
import os

from pipeline import claude_client

INPUT_PATH   = os.path.join(os.path.dirname(__file__), "..", "output", "candidates.json")
OUTPUT_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "picked_history.json")
MAX_HISTORY  = 30   # titles to remember


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
{already_covered}
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


def load_history() -> list[str]:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH) as f:
        return json.load(f)


def save_history(history: list[str], new_title: str):
    history = [new_title] + [t for t in history if t != new_title]
    history = history[:MAX_HISTORY]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def build_prompt(candidates: list[dict], history: list[str]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. [{c['source']}] {c['title']}")
        lines.append(f"   Summary: {c['summary']}")
        lines.append(f"   URL: {c['url']}")
        lines.append("")

    if history:
        already = "\n".join(f"- {t}" for t in history)
        already_covered = (
            f"\nALREADY COVERED — do NOT pick these topics again, pick something fresh:\n"
            f"{already}\n"
        )
    else:
        already_covered = ""

    return PROMPT_TEMPLATE.format(
        candidates="\n".join(lines),
        already_covered=already_covered,
    )


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

    history = load_history()
    if history:
        print(f"Excluding {len(history)} previously covered topics...")

    prompt = build_prompt(candidates, history)
    raw    = claude_client.call(prompt, stage="ranker")
    topic  = extract_json(raw)

    # History is saved by the notifier after successful video delivery,
    # not here — so failed pipeline runs don't consume a history slot.

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
