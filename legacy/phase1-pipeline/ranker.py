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
You are a content strategist for an AI-curious audience on Instagram Reels.
Your job: pick ONE topic that will perform best as a 60-second short-form video.

STEP 1 — SEARCH THE WEB FIRST (do this before reading the candidates list):
Use Google Search to find what is happening in AI RIGHT NOW today:

  Search 1: "github trending AI today" OR "site:github.com AI repo trending"
    → Find new AI/ML repos that went viral on GitHub in the last 24 hours.
    → Look for repos built on top of famous models (Llama, GPT-4, Claude, Gemini).
    → Note the repo name, what it does, star count if visible, and GitHub URL.

  Search 2: "new AI model release today" OR "AI breakthrough today site:x.com OR site:twitter.com"
    → Find what AI labs (OpenAI, Google, Meta, Anthropic, Mistral) released or announced today.
    → Note any dramatic claims: speed records broken, models beating others, tools going free.

  Search 3: "AI tool open source today github"
    → Find tools people can actually run locally — no API key, no subscription.
    → These are high-save content: viewers bookmark "run this today" content.

Add any strong finds from your web search to your consideration pool alongside the scraped
candidates below. A fresh repo or announcement found via search beats a 2-day-old Reddit post.

STEP 2 — EVALUATE ALL CANDIDATES (scraped + web search finds):

Instagram Reels is distributed by SHARES and SAVES — not just likes.
People share content that surprised them or challenged an assumption they held.
People save content that they want to act on later.
Write for those two behaviors.

SCORING CRITERIA — rate each candidate 1–10 on five dimensions:

1. BRAND GRAVITY — Is a well-known name central to this topic?
   High: OpenAI, Google/DeepMind, Meta, Anthropic, NVIDIA, Mistral, DeepSeek, Apple, Microsoft
         — the audience already has feelings about these names; they stop scrolling when they appear
   Low: obscure tools, academic labs, papers with no brand attachment
   Note: a niche tool CAN score high if the hook can credibly reference a famous brand by comparison
         (e.g. "beats GPT-4o" or "OpenAI just got outpaced by a 3B model")

2. DRAMATIC HOOK POTENTIAL — Does the topic have a natural dramatic reversal, death, or surprising contrast?
   High: "X just died", "Y broke a 56-year record", "the model that replaced 3 others", "free vs $20/month"
         — anything with a before/after, a fall from grace, or a specific number that defies expectation
   Low: incremental improvements, feature additions, topics that are "interesting" but not surprising

3. VISUAL RICHNESS — Does this topic have concrete elements to show as animated data?
   High: named pipeline stages, before/after metrics with real numbers, benchmark bars, a measurable comparison
   Low: pure math derivations, abstract policy topics, topics where the only visual is text on screen

4. FRESHNESS — Is this genuinely new or newly relevant?
   High: released/published in the last 72 hours, a result that overturns prior assumptions
   Low: rehashed fundamentals, evergreen content dressed up as news

5. FOCUS — Can the core idea be expressed in one surprising sentence + 3 supporting facts?
   High: one concrete mechanism or benchmark result with a clear before/after delta
   Low: broad surveys, multi-paper comparisons, "state of X" overviews

IDEAL TOPIC EXAMPLES (calibration bar — these would score 8+ on all five dimensions):
- "OpenAI's Sora lasted 6 months. Here's the unit economics that killed it."
- "Google's AlphaEvolve just broke a 56-year-old math record by rewriting its own algorithms."
- "Meta's Llama 4 Maverick beats GPT-4o — and you can run it on your own hardware."
- "Mistral Small 4: 119B parameters, only 6B fire per token. One model that replaced three."
- "DeepSeek gives 5 million tokens free. You've been paying for API calls you didn't need to."

CONTENT TYPE PRIORITY — in order of preference:

1. NEW AI TOOL / REPO (source: github_trending or hackernews)
   These score highest because they are ACTIONABLE — the viewer can pull and run the repo today.
   "How to use X" content gets SAVED. Saves are the top Instagram distribution signal.
   The hook writes itself: "Someone just built X using [Famous Model]. Here's how it works."
   Prefer repos that: (a) are built on a famous model (Llama, GPT-4, Claude, Gemini),
   (b) solve a problem anyone can relate to (run locally, no API key, replaces paid tool),
   (c) have a clear 3-step usage story visible from the repo description.

2. MODEL RELEASE / BREAKTHROUGH (source: reddit, hackernews)
   A new model from a famous lab (OpenAI, Google, Meta, Mistral, Anthropic) with a specific
   surprising capability or benchmark result. Only pick if the claim is dramatic and verifiable.

3. RESEARCH PAPER (source: arxiv)
   Only if the paper has a concrete trick with a visual mechanism AND a measurable result.
   Avoid pure math, surveys, or papers with no public demo/code.

STRONGLY PREFER topics where:
- The viewer can DO something after watching (run a repo, change a workflow, try a tool)
- A famous brand name appears naturally in the hook
- The core claim fits in ≤12 words as a dramatic reversal or surprising contrast
- The topic broke in the last 48 hours

STRICTLY AVOID:
- Pure benchmark comparisons with no actionable takeaway ("model X scores Y on benchmark Z")
- Niche tools with no famous brand reference AND no clear "you can run this today" angle
- "AI is changing everything"-style posts
- Topics requiring more than 4 visual steps to explain clearly
- Papers with no public abstract, open access, or code
{already_covered}{analytics_hint}CANDIDATES:
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


def _analytics_hint() -> str:
    """
    Return a soft hint for the ranker based on past video performance.
    Only active once MIN_ENTRIES_FOR_SIGNAL entries exist in analytics.
    Returns empty string when there is not enough data yet.
    """
    try:
        from pipeline.analytics import get_layout_scores, get_topic_signals
        layout_scores = get_layout_scores()
        topic_signals = get_topic_signals()
    except Exception:
        return ""

    if not layout_scores and not topic_signals:
        return ""

    lines = ["\nPERFORMANCE SIGNAL — from past videos on this account:"]

    if layout_scores:
        best_layout = max(layout_scores, key=layout_scores.get)
        lines.append(
            f"  Best-performing visual layout so far: {best_layout} "
            f"(avg score {layout_scores[best_layout]}). "
            f"Prefer topics that fit this layout when quality is equal."
        )

    if topic_signals:
        top_kws = ", ".join(kw for kw, _ in topic_signals[:6])
        lines.append(
            f"  Keywords from top-performing past topics: {top_kws}. "
            f"Topics related to these themes have historically performed well — "
            f"give a slight preference when two candidates are otherwise equal."
        )

    lines.append("")
    return "\n".join(lines)


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

    analytics_hint = _analytics_hint()

    return PROMPT_TEMPLATE.format(
        candidates="\n".join(lines),
        already_covered=already_covered,
        analytics_hint=analytics_hint,
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
            # json_mode=False — grounding (Google Search) is incompatible with
            # responseMimeType. The ranker prompt instructs JSON output; extract_json()
            # parses it from the plain text response.
            raw   = claude_client.call(prompt, stage="ranker", json_mode=False)
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
