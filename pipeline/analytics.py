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

ANALYTICS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "output", "analytics.json"
)
TOPIC_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
PARAMS_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "params.json")

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
    wt = entry.get("watch_time_pct", 0) or 0
    saves = entry.get("saves", 0) or 0
    likes = entry.get("likes", 0) or 0
    shares = entry.get("shares", 0) or 0
    v48 = entry.get("views_48h", 0) or 0
    return round(
        (wt * 1.5) + (saves * 2.0) + (likes * 0.5) + (shares * 1.0) + (v48 / 20),
        2,
    )


# ── Skeleton creation (called at end of pipeline run) ────────────────────────

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")


def create_skeleton():
    """
    Write a skeleton analytics entry at the end of every pipeline run.
    Pre-fills: id, topic, layout, hook, generated_at.
    KPI fields (views, saves, shares, etc.) left as null — filled via --log-stats.

    Backward compatible: existing entries with the same id are not overwritten.
    Entries without hook/generated_at fields are simply missing those keys — no breakage.
    """
    topic_title = None
    beat2_layout = "unknown"
    hook = None

    if os.path.exists(TOPIC_PATH):
        with open(TOPIC_PATH) as f:
            topic_title = json.load(f).get("title", "")

    if os.path.exists(PARAMS_PATH):
        with open(PARAMS_PATH) as f:
            params = json.load(f)
        beat2_layout = params.get("beat_2", {}).get("data", {}).get("layout", "unknown")

    if os.path.exists(SCRIPT_PATH):
        with open(SCRIPT_PATH) as f:
            hook = json.load(f).get("hook")

    if not topic_title:
        return

    today = date.today().isoformat()
    # Use today as a temporary posted_at — user can correct via --log-stats
    entry_id = _slug(topic_title, today)

    entries = _load()
    # Never overwrite an existing entry (backward compatible)
    if any(e["id"] == entry_id for e in entries):
        return

    skeleton = {
        "id": entry_id,
        "topic": topic_title,
        "layout": beat2_layout,
        "hook": hook,
        "generated_at": today,
        "posted_at": None,
        "views_24h": None,
        "views_48h": None,
        "views_72h": None,
        "watch_time_pct": None,
        "likes": None,
        "saves": None,
        "shares": None,
        "score": None,
    }
    entries.append(skeleton)
    _save(entries)
    print(f"  Analytics skeleton created → {topic_title[:60]}")


# ── Read last unlogged video from output files ────────────────────────────────


def _last_video_info() -> Optional[dict]:
    """Return topic + layout for the last pipeline run, if files exist."""
    topic_title = None
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

    Prefers pending skeletons (posted_at=null) over manual entry.
    Backward compatible: works even if no skeleton exists.
    """
    print("\n" + "═" * 56)
    print("  VIDEO PERFORMANCE LOG")
    print("═" * 56)

    entries = _load()
    pending = [e for e in entries if e.get("posted_at") is None]

    if pending:
        print(f"\n  {len(pending)} pending video(s) awaiting KPIs:\n")
        for i, e in enumerate(pending, 1):
            hook_preview = f"  hook: {e['hook'][:60]}" if e.get("hook") else ""
            print(f"  {i}. {e['topic'][:55]}")
            print(f"     layout: {e['layout']}  generated: {e.get('generated_at','-')}")
            if hook_preview:
                print(f"     {hook_preview}")
        print()
        choice = input(
            f"  Select video to log [1-{len(pending)}, or 0 for manual entry] → "
        ).strip()
        if choice.isdigit() and 1 <= int(choice) <= len(pending):
            skeleton = pending[int(choice) - 1]
            topic = skeleton["topic"]
            layout = skeleton["layout"]
        else:
            topic = input("  Topic title: ").strip()
            layout = (
                input("  Beat-2 layout (e.g. BarComparison): ").strip() or "unknown"
            )
    else:
        info = _last_video_info()
        if info:
            print(f"\n  Last pipeline output:")
            print(f"    Topic  : {info['topic']}")
            print(f"    Layout : {info['layout']}")
            use_last = input("\n  Log stats for this video? [y/n] → ").strip().lower()
            if use_last == "y":
                topic = info["topic"]
                layout = info["layout"]
            else:
                topic = input("  Topic title: ").strip()
                layout = (
                    input("  Beat-2 layout (e.g. BarComparison): ").strip() or "unknown"
                )
        else:
            topic = input("  Topic title: ").strip()
            layout = (
                input("  Beat-2 layout (e.g. BarComparison): ").strip() or "unknown"
            )

    # Post date
    today = date.today().isoformat()
    pd_raw = input(f"  Posted date [YYYY-MM-DD, default={today}]: ").strip()
    posted_at = pd_raw if pd_raw else today

    # Check for collision only on manually-entered entries (skeletons use generated id)
    new_id = _slug(topic, posted_at)
    existing = next((e for e in entries if e["id"] == new_id), None)
    if existing and existing.get("posted_at") is not None:
        print(f"\n  [WARN] Entry for this topic+date already has KPIs.")
        overwrite = input("  Overwrite? [y/n] → ").strip().lower()
        if overwrite != "y":
            print("  Skipped.\n")
            return

    print("\n  Enter metrics (press Enter to skip any):\n")
    views_24h = _prompt_int("Views at 24h")
    views_48h = _prompt_int("Views at 48h")
    views_72h = _prompt_int("Views at 72h")
    watch_time_pct = _prompt_float("Watch time %", 0, 100)
    likes = _prompt_int("Likes")
    saves = _prompt_int("Saves")
    shares = _prompt_int("Shares")

    # Preserve hook + generated_at from skeleton if it exists
    skeleton_id = _slug(topic, date.today().isoformat())
    old_skeleton = next(
        (e for e in entries if e["id"] == skeleton_id and e.get("posted_at") is None),
        None,
    )

    entry = {
        "id": _slug(topic, posted_at),
        "topic": topic,
        "layout": layout,
        "hook": old_skeleton.get("hook") if old_skeleton else None,
        "generated_at": old_skeleton.get("generated_at") if old_skeleton else None,
        "posted_at": posted_at,
        "views_24h": views_24h,
        "views_48h": views_48h,
        "views_72h": views_72h,
        "watch_time_pct": watch_time_pct,
        "likes": likes,
        "saves": saves,
        "shares": shares,
    }
    entry["score"] = _compute_score(entry)

    # Remove skeleton (generated_at id) and any existing KPI entry for same final id
    entries = [e for e in entries if e["id"] not in (skeleton_id, entry["id"])]
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
        score = e.get("score")
        if layout and score is not None:
            bucket[layout].append(score)

    return {
        layout: round(sum(scores) / len(scores), 2)
        for layout, scores in bucket.items()
        if len(scores) >= 2  # need at least 2 data points per layout
    }


_STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "in",
    "on",
    "at",
    "to",
    "for",
    "with",
    "how",
    "why",
    "what",
    "this",
    "that",
    "from",
    "via",
    "vs",
    "using",
    "new",
    "ai",
    "ml",
    "llm",
    "gpu",
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
    scored = [e for e in entries if e.get("score") is not None]
    scored.sort(key=lambda e: e["score"], reverse=True)
    top = scored[: max(1, len(scored) // 2)]

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

    posted = [e for e in entries if e.get("posted_at") is not None]
    pending = [e for e in entries if e.get("posted_at") is None]

    posted_sorted = sorted(posted, key=lambda e: e.get("posted_at", ""), reverse=True)

    cols = (
        "Date",
        "Layout",
        "V-24h",
        "V-48h",
        "WT%",
        "Saves",
        "Score",
        "Hook",
        "Topic",
    )
    widths = [len(c) for c in cols]

    rows = []
    for e in posted_sorted:
        hook_text = (e.get("hook") or "-")[:35]
        row = (
            e.get("posted_at", "?"),
            (e.get("layout") or "?")[:16],
            str(e.get("views_24h") or "-"),
            str(e.get("views_48h") or "-"),
            str(e.get("watch_time_pct") or "-"),
            str(e.get("saves") or "-"),
            str(e.get("score", "-")),
            hook_text,
            (e.get("topic") or "?")[:35],
        )
        rows.append(row)
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row):
        return (
            "║ "
            + " ║ ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
            + " ║"
        )

    sep_top = "╔═" + "═╦═".join("═" * w for w in widths) + "═╗"
    sep_mid = "╠═" + "═╬═".join("═" * w for w in widths) + "═╣"
    sep_bot = "╚═" + "═╩═".join("═" * w for w in widths) + "═╝"
    title = "║" + " ANALYTICS ".center(len(sep_top) - 2) + "║"

    print()
    print(sep_top)
    print(title)
    print(sep_mid)
    print(fmt(cols))
    print(sep_mid)
    for row in rows:
        print(fmt(row))
    print(sep_bot)

    # Pending skeletons
    if pending:
        print(f"\n  ⏳ {len(pending)} pending (generated, not yet posted/logged):")
        for e in pending:
            hook_preview = f"  \"{e['hook'][:55]}\"" if e.get("hook") else ""
            print(f"    • {e['topic'][:55]}  [{e['layout']}]{hook_preview}")

    # Layout signal
    layout_scores = get_layout_scores()
    if layout_scores:
        print("\n  Layout avg scores:")
        for layout, avg in sorted(
            layout_scores.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"    {layout:<20} {avg}")

    print()


def main():
    print_summary()


if __name__ == "__main__":
    main()
