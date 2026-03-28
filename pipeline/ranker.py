import json
import os
import re

from pipeline import claude_client

INPUT_PATH   = os.path.join(os.path.dirname(__file__), "..", "output", "candidates.json")
OUTPUT_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "picked_history.json")
MAX_HISTORY  = 30   # titles to remember

# Short words that shouldn't trigger topic overlap detection
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
    "with", "how", "why", "what", "this", "that", "from", "via", "vs",
    "using", "new", "ai", "ml", "llm", "gpu",
}


PROMPT_TEMPLATE = """\
You are a content strategist for an AI engineering audience on Instagram and X (Twitter).
Your job: pick ONE topic from the candidates below that will make the best short Manim animation explainer.

SCORING CRITERIA — rate each candidate 1–10 on four dimensions:

1. VISUAL RICHNESS — Does this topic have concrete visual elements to show?
   High: named pipeline stages, before/after metrics with real numbers, a process with distinct steps,
         a measurable comparison (speed, memory, accuracy), a mechanism with named components
   Low: abstract concepts with no tangible shape, opinion/policy topics, pure math derivations,
        topics where the "visual" would just be text on screen

2. ENGINEER VALUE — Will a working ML/AI engineer learn something immediately actionable or surprising?
   High: a technique they can test today, a benchmark that changes best practices, a paper with a concrete trick
   Low: general hype, things every engineer already knows, marketing posts

3. FRESHNESS — Is this genuinely new or newly relevant?
   High: paper from the last 72 hours, a newly released model/tool, a result that overturns prior assumptions
   Low: rehashed fundamentals, evergreen content dressed up as news

4. FOCUS — Can the core idea be shown with 3–5 named steps + a clear before/after contrast?
   High: one concrete mechanism or benchmark result with identifiable stages and measurable delta
   Low: broad surveys, multi-paper comparisons, "state of X" overviews, topics needing >5 steps

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


def _keywords(title: str) -> set[str]:
    """Extract significant lowercase words (≥5 chars, not stop words) from a title."""
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    return {w for w in words if len(w) >= 5 and w not in _STOP_WORDS}


def filter_candidates(candidates: list[dict], history: list[str]) -> list[dict]:
    """
    Remove candidates that share ≥2 significant keywords with any single history
    title. Per-title matching (not aggregate) prevents generic ML words pooled
    across 30 history titles from causing false positives.

    ≥2 threshold catches:
      - exact/near-exact duplicates (many shared words)
      - thematic siblings ('Google TurboQuant running Qwen' shares 'turboquant'
        + 'google' with 'Google TurboQuant: 6x Memory Reduction')
    Single-word overlap (e.g. 'speed', 'memory') is not enough to filter.
    """
    if not history:
        return candidates

    history_kw_sets = [_keywords(t) for t in history]

    kept = []
    for c in candidates:
        candidate_kw = _keywords(c["title"])
        blocked_by = None
        for hist_title, hist_kw in zip(history, history_kw_sets):
            overlap = candidate_kw & hist_kw
            if len(overlap) >= 2:
                blocked_by = (hist_title, overlap)
                break
        if blocked_by:
            print(f"  [ranker] filtered (overlap={blocked_by[1]} with '{blocked_by[0][:60]}'): {c['title']}")
        else:
            kept.append(c)
    return kept


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
    # Find first { ... } block
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(raw[start:end])
    return json.loads(raw.strip())


def main():
    with open(INPUT_PATH) as f:
        candidates = json.load(f)

    history = load_history()
    if history:
        print(f"History contains {len(history)} covered topics — filtering candidates...")

    # Pre-filter before Claude even sees the list: removes thematic duplicates
    # (e.g. all TurboQuant variants) that share keywords with history titles.
    filtered = filter_candidates(candidates, history)
    if len(filtered) < len(candidates):
        print(f"  {len(candidates) - len(filtered)} candidate(s) removed by keyword filter, {len(filtered)} remain.")
    if not filtered:
        print("[ranker] All candidates filtered — falling back to full list.")
        filtered = candidates

    prompt = build_prompt(filtered, history)
    last_err = None
    for attempt in range(1, 4):
        try:
            raw   = claude_client.call(prompt, stage="ranker", json_mode=True)
            topic = extract_json(raw)
            break
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_err = e
            print(f"[ranker] JSON parse failed (attempt {attempt}/3): {e} — retrying...")
    else:
        raise RuntimeError(f"Ranker failed to produce valid JSON after 3 attempts. Last error: {last_err}")

    # Save to history immediately so repeated pipeline runs (e.g. during dev / test
    # without Telegram delivery) don't re-pick the same topic. Notifier also calls
    # save_history() after delivery — that's a no-op since the title is already there.
    save_history(history, topic["title"])
    print(f"Topic committed to history: {topic['title']}")

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
