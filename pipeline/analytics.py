"""
Video performance analytics — manual input loop (Option A).

Storage: output/analytics.json
Each entry is keyed by a slug derived from the topic title + post date.

Schema per entry:
  {
    "id":             "flash-attention-2-2026-03-31",
    "topic":          "Flash Attention 2 vs Standard Attention",
    "layout":         "BarComparison",          # beat_2 layout
    "posted_at":      "2026-03-31",
    "views_24h":      420,
    "views_48h":      810,
    "views_72h":      950,
    "watch_time_pct": 48,                       # % of video watched (Instagram insight)
    "likes":          32,
    "saves":          18,                       # saves > likes for tech content
    "shares":         5,
    "score":          72.4                      # derived — do not set manually
  }

Score formula (tuned for tech Reels):
  score = (watch_time_pct * 1.5) + (saves * 2.0) + (likes * 0.5) + (shares * 1.0)
         + (views_48h / 20)

Higher saves and watch_time_pct are weighted most — they signal genuine interest
from the technical audience over passive scrollers.

Ranker integration:
  get_layout_scores()  → dict[layout_name, avg_score]  used by ranker as soft prior
  get_topic_signals()  → list of (keyword, avg_score)  used to boost similar topics
"""
import json
import os
import re
from datetime import date
from typing import Optional

ANALYTICS_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "analytics.json")
TOPIC_PATH     = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
PARAMS_PATH    = os.path.join(os.path.dirname(__file__), "..", "output", "params.json")

# Minimum entries before scores are used as a signal
MIN_ENTRIES_FOR_SIGNAL = 5


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if not os.path.exists(ANALYTICS_PATH):
        return []
    with open(ANALYTICS_PATH) as f:
        return json.load(f)


def _save(entries: list[dict]):
    os.makedirs(os.path.dirname(os.path.abspath(ANALYTICS_PATH)), exist_ok=True)
    with open(ANALYTICS_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def _slug(title: str, posted_at: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return f"{slug}-{posted_at}"


def _compute_score(entry: dict) -> float:
    wt     = entry.get("watch_time_pct", 0) or 0
    saves  = entry.get("saves", 0)          or 0
    likes  = entry.get("likes", 0)          or 0
    shares = entry.get("shares", 0)         or 0
    v48    = entry.get("views_48h", 0)      or 0
    return round(
        (wt * 1.5) + (saves * 2.0) + (likes * 0.5) + (shares * 1.0) + (v48 / 20),
        2,
    )


# ── Read last unlogged video from output files ────────────────────────────────

def _last_video_info() -> Optional[dict]:
    """Return topic + layout for the last pipeline run, if files exist."""
    topic_title  = None
    beat2_layout = None

    if os.path.exists(TOPIC_PATH):
        with open(TOPIC_PATH) as f:
            t = json.load(f)
        topic_title = t.get("title", "")

    if os.path.exists(PARAMS_PATH):
        with open(PARAMS_PATH) as f:
            params = json.load(f)
        beat2 = params.get("beat_2", {})
        beat2_layout = beat2.get("data", {}).get("layout", "unknown")

    if not topic_title:
        return None
    return {"topic": topic_title, "layout": beat2_layout or "unknown"}


def _already_logged(topic: str, posted_at: str, entries: list[dict]) -> bool:
    sid = _slug(topic, posted_at)
    return any(e["id"] == sid for e in entries)


# ── Interactive logging ───────────────────────────────────────────────────────

def _prompt_int(label: str, required: bool = False) -> Optional[int]:
    while True:
        raw = input(f"  {label}: ").strip()
        if not raw and not required:
            return None
        if raw.isdigit():
            return int(raw)
        print("    → Enter a whole number (or press Enter to skip).")


def _prompt_float(label: str, lo: float, hi: float) -> Optional[float]:
    while True:
        raw = input(f"  {label} ({lo}–{hi}): ").strip()
        if not raw:
            return None
        try:
            v = float(raw)
            if lo <= v <= hi:
                return v
            print(f"    → Must be between {lo} and {hi}.")
        except ValueError:
            print("    → Enter a number.")


def log_stats_interactive():
    """
    Interactive CLI prompt to log performance stats for the last video.
    Called via: python3 run.py --log-stats
    """
    print("\n" + "═" * 56)
    print("  VIDEO PERFORMANCE LOG")
    print("═" * 56)

    entries = _load()
    info    = _last_video_info()

    # Topic
    if info:
        print(f"\n  Last pipeline output:")
        print(f"    Topic  : {info['topic']}")
        print(f"    Layout : {info['layout']}")
        use_last = input("\n  Log stats for this video? [y/n] → ").strip().lower()
        if use_last == "y":
            topic  = info["topic"]
            layout = info["layout"]
        else:
            topic  = input("  Topic title: ").strip()
            layout = input("  Beat-2 layout (e.g. BarComparison): ").strip() or "unknown"
    else:
        topic  = input("  Topic title: ").strip()
        layout = input("  Beat-2 layout (e.g. BarComparison): ").strip() or "unknown"

    # Post date
    today = date.today().isoformat()
    pd_raw = input(f"  Posted date [YYYY-MM-DD, default={today}]: ").strip()
    posted_at = pd_raw if pd_raw else today

    if _already_logged(topic, posted_at, entries):
        print(f"\n  [WARN] Entry for this topic+date already exists.")
        overwrite = input("  Overwrite? [y/n] → ").strip().lower()
        if overwrite != "y":
            print("  Skipped.\n")
            return

    print("\n  Enter metrics (press Enter to skip any):\n")
    views_24h      = _prompt_int("Views at 24h")
    views_48h      = _prompt_int("Views at 48h")
    views_72h      = _prompt_int("Views at 72h")
    watch_time_pct = _prompt_float("Watch time %", 0, 100)
    likes          = _prompt_int("Likes")
    saves          = _prompt_int("Saves")
    shares         = _prompt_int("Shares")

    entry = {
        "id":             _slug(topic, posted_at),
        "topic":          topic,
        "layout":         layout,
        "posted_at":      posted_at,
        "views_24h":      views_24h,
        "views_48h":      views_48h,
        "views_72h":      views_72h,
        "watch_time_pct": watch_time_pct,
        "likes":          likes,
        "saves":          saves,
        "shares":         shares,
    }
    entry["score"] = _compute_score(entry)

    # Remove any existing entry for same id (overwrite case)
    entries = [e for e in entries if e["id"] != entry["id"]]
    entries.append(entry)
    _save(entries)

    print(f"\n  ✅ Logged  (score={entry['score']})")
    print(f"  Saved → {ANALYTICS_PATH}\n")
    print_summary()


# ── Signal extraction for ranker ─────────────────────────────────────────────

def get_layout_scores() -> dict[str, float]:
    """
    Returns avg performance score per beat-2 layout.
    Only populated once MIN_ENTRIES_FOR_SIGNAL entries exist.
    """
    entries = _load()
    if len(entries) < MIN_ENTRIES_FOR_SIGNAL:
        return {}

    from collections import defaultdict
    bucket: dict[str, list[float]] = defaultdict(list)
    for e in entries:
        layout = e.get("layout")
        score  = e.get("score")
        if layout and score is not None:
            bucket[layout].append(score)

    return {
        layout: round(sum(scores) / len(scores), 2)
        for layout, scores in bucket.items()
        if len(scores) >= 2  # need at least 2 data points per layout
    }


_STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
    "with", "how", "why", "what", "this", "that", "from", "via", "vs",
    "using", "new", "ai", "ml", "llm", "gpu",
}


def get_topic_signals() -> list[tuple[str, float]]:
    """
    Returns (keyword, avg_score) pairs from high-scoring past videos.
    Used by ranker to give a soft boost to similar topics.
    Only populated once MIN_ENTRIES_FOR_SIGNAL entries exist.
    """
    entries = _load()
    if len(entries) < MIN_ENTRIES_FOR_SIGNAL:
        return []

    # Take top half by score
    scored  = [e for e in entries if e.get("score") is not None]
    scored.sort(key=lambda e: e["score"], reverse=True)
    top     = scored[: max(1, len(scored) // 2)]

    from collections import defaultdict
    kw_scores: dict[str, list[float]] = defaultdict(list)
    for e in top:
        words = re.findall(r"[a-zA-Z0-9]+", e["topic"].lower())
        for w in words:
            if len(w) >= 5 and w not in _STOP_WORDS:
                kw_scores[w].append(e["score"])

    result = [
        (kw, round(sum(scores) / len(scores), 2))
        for kw, scores in kw_scores.items()
        if len(scores) >= 2
    ]
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:15]


# ── Summary table ─────────────────────────────────────────────────────────────

def print_summary():
    entries = _load()
    if not entries:
        print("  No analytics data yet. Run --log-stats after posting a video.\n")
        return

    entries_sorted = sorted(entries, key=lambda e: e.get("posted_at", ""), reverse=True)

    cols   = ("Date", "Layout", "V-24h", "V-48h", "WT%", "Saves", "Score", "Topic")
    widths = [len(c) for c in cols]

    rows = []
    for e in entries_sorted:
        row = (
            e.get("posted_at", "?"),
            (e.get("layout") or "?")[:16],
            str(e.get("views_24h") or "-"),
            str(e.get("views_48h") or "-"),
            str(e.get("watch_time_pct") or "-"),
            str(e.get("saves") or "-"),
            str(e.get("score", "-")),
            (e.get("topic") or "?")[:40],
        )
        rows.append(row)
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row):
        return "║ " + " ║ ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " ║"

    sep_top = "╔═" + "═╦═".join("═" * w for w in widths) + "═╗"
    sep_mid = "╠═" + "═╬═".join("═" * w for w in widths) + "═╣"
    sep_bot = "╚═" + "═╩═".join("═" * w for w in widths) + "═╝"
    title   = "║" + " ANALYTICS ".center(len(sep_top) - 2) + "║"

    print()
    print(sep_top)
    print(title)
    print(sep_mid)
    print(fmt(cols))
    print(sep_mid)
    for row in rows:
        print(fmt(row))
    print(sep_bot)

    # Layout signal
    layout_scores = get_layout_scores()
    if layout_scores:
        print("\n  Layout avg scores (from analytics):")
        for layout, avg in sorted(layout_scores.items(), key=lambda x: x[1], reverse=True):
            print(f"    {layout:<20} {avg}")

    print()


def main():
    print_summary()


if __name__ == "__main__":
    main()
