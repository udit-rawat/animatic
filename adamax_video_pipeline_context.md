# AdaMax Content Engine — Full Pipeline Context

> All API keys, tokens, and secrets have been redacted and replaced with `<REDACTED>`.

---

## Pipeline Overview

```
scraper → ranker → scripter → scene_planner → narrator → param_extractor → animator → mixer → notifier
```

Each stage reads from and writes to `output/`. The pipeline runs fully automated once triggered.

---

## 1. THE ORCHESTRATOR

### `run.py`

```python
import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

STAGES = ["scraper", "ranker", "scripter", "scene_planner", "narrator", "param_extractor", "animator", "mixer", "notifier"]


def apply_provider(provider: str, model: str | None):
    if provider == "claude":
        os.environ["FORCE_PROVIDER"] = "claude"
    elif provider == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("[ERROR] --provider openrouter requires OPENROUTER_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "openrouter"
    elif provider == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            print("[ERROR] --provider gemini requires GEMINI_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "gemini"
    elif provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("[ERROR] --provider anthropic requires ANTHROPIC_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "anthropic"
    elif provider == "handoff":
        os.environ["FORCE_PROVIDER"] = "handoff"

    if model:
        os.environ["OPENROUTER_MODEL"] = model


def _is_gemini_active() -> bool:
    force = os.environ.get("FORCE_PROVIDER")
    if force:
        return force == "gemini"
    return bool(os.environ.get("GEMINI_API_KEY"))


def run_stage(name: str):
    from pipeline.logger import get as get_log
    get_log().info(f"Stage START: {name}")
    print(f"\n--- Running: {name} ---")
    if name == "scraper":
        from pipeline.scraper import main
    elif name == "ranker":
        from pipeline.ranker import main
    elif name == "scripter":
        from pipeline.scripter import main
    elif name == "scene_planner":
        from pipeline.scene_planner import main
    elif name == "animator":
        from pipeline.animator import main
    elif name == "param_extractor":
        from pipeline.param_extractor import main
    elif name == "narrator":
        from pipeline.narrator import main
    elif name == "mixer":
        from pipeline.mixer import main
    elif name == "notifier":
        from pipeline.notifier import main
    else:
        raise ValueError(f"Unknown stage: {name}")
    main()


def main():
    parser = argparse.ArgumentParser(description="adamax-content-engine pipeline")
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--provider", choices=["claude", "openrouter", "anthropic", "gemini", "handoff"])
    parser.add_argument("--model")
    parser.add_argument("--gemini", action="store_true")
    args = parser.parse_args()

    if args.gemini:
        os.environ["FORCE_PROVIDER"] = "gemini"
        os.environ.setdefault("GEMINI_MODEL_RANKER",          "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_SCRIPTER",        "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_SCENE_PLANNER",   "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_NARRATOR",        "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_PARAM_EXTRACTOR", "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_ANIMATOR",        "gemini-2.5-flash-lite")

    if args.provider:
        apply_provider(args.provider, args.model)

    stages_to_run = [args.stage] if args.stage else STAGES
    for stage in stages_to_run:
        run_stage(stage)

    print("\n✅ Pipeline complete.")


if __name__ == "__main__":
    main()
```

---

## 2. THE RESEARCHERS

### `pipeline/scraper.py`

```python
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
USER_AGENT = "adamax-content-engine/1.0 (daily AI video pipeline)"


def get_subreddits() -> list[str]:
    raw = os.environ.get(
        "SUBREDDITS",
        "r/MachineLearning,r/LocalLLaMA,r/deeplearning,r/mlops,r/StableDiffusion,r/Transformers,r/computervision"
    )
    return [s.strip() for s in raw.split(",") if s.strip()]


def fetch_reddit_posts(subreddit: str, limit: int = 5) -> list[dict]:
    url = f"https://www.reddit.com/{subreddit}/top.json?t=day&limit={limit * 2}"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()
    data = response.json()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    results = []
    for post in data["data"]["children"]:
        p = post["data"]
        created = datetime.fromtimestamp(p["created_utc"], tz=timezone.utc)
        if created < cutoff:
            continue
        results.append({
            "source": subreddit,
            "title": p["title"],
            "summary": (p.get("selftext") or "")[:300] or p.get("url", ""),
            "url": f"https://reddit.com{p['permalink']}",
        })
        if len(results) == limit:
            break
    return results


def fetch_arxiv_papers(query: str, max_results: int = 3) -> list[dict]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": 10,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = requests.get(
        "https://export.arxiv.org/api/query", params=params, timeout=15
    )
    response.raise_for_status()

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(response.text)
    results = []
    for entry in root.findall("atom:entry", ns)[:max_results]:
        title   = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:300]
        link    = entry.find("atom:id", ns).text.strip()
        results.append({"source": "arxiv", "title": title, "summary": summary, "url": link})
    return results


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    candidates = []

    for sub in get_subreddits():
        candidates += fetch_reddit_posts(sub, limit=3)

    candidates += fetch_arxiv_papers(
        "large language model OR diffusion model OR reinforcement learning",
        max_results=3,
    )

    output_path = os.path.join(OUTPUT_DIR, "candidates.json")
    with open(output_path, "w") as f:
        json.dump(candidates, f, indent=2)

    print(f"Saved {len(candidates)} candidates → {output_path}")
    return candidates
```

### `pipeline/ranker.py` — LLM Prompt (Topic Selection)

```python
PROMPT_TEMPLATE = """\
You are a content strategist for an AI engineering audience on Instagram and X (Twitter).
Your job: pick ONE topic from the candidates below that will make the best short Manim animation explainer.

SCORING CRITERIA — rate each candidate 1–10 on four dimensions:

1. VISUAL RICHNESS — Does this topic have concrete visual elements to show?
   High: named pipeline stages, before/after metrics with real numbers, a process with distinct steps,
         a measurable comparison (speed, memory, accuracy), a mechanism with named components
   Low: abstract concepts with no tangible shape, opinion/policy topics, pure math derivations

2. ENGINEER VALUE — Will a working ML/AI engineer learn something immediately actionable or surprising?
   High: a technique they can test today, a benchmark that changes best practices
   Low: general hype, things every engineer already knows, marketing posts

3. FRESHNESS — Is this genuinely new or newly relevant?
   High: paper from the last 72 hours, a newly released model/tool
   Low: rehashed fundamentals, evergreen content dressed up as news

4. FOCUS — Can the core idea be shown with 3–5 named steps + a clear before/after contrast?
   High: one concrete mechanism or benchmark result with identifiable stages and measurable delta
   Low: broad surveys, multi-paper comparisons, "state of X" overviews

IDEAL TOPIC EXAMPLES:
- "Flash Attention 3 cuts prefill latency 40% — here's the tiling trick behind it"
- "Why LoRA rank matters: a visual guide to rank-1 vs rank-64 weight updates"
- "Speculative decoding: how a small draft model makes large models 3× faster"

STRICTLY AVOID:
- "AI is changing everything"-style posts
- Topics requiring more than 4 visual steps to explain clearly
- Papers with no public abstract or open access
- Topics that are purely mathematical with no intuitive visual hook

CANDIDATES:
{candidates}

Select the single best candidate. Respond with ONLY valid JSON:
{
  "title": "...",
  "summary": "...",
  "url": "...",
  "source": "...",
  "why_picked": "one sentence: what makes it visually teachable in 60 seconds"
}
"""
```

---

## 3. THE WRITER (CRITICAL)

### `pipeline/scripter.py` — On-Screen Text Prompt

```python
SCRIPTER_PROMPT = """\
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
{
  "hook": "<curiosity gap — ≤12 words>",
  "concept_bullets": [
    "<mechanism — ≤18 words with concrete component names>",
    "<before/after proof — ≤18 words with real numbers>"
  ],
  "takeaway": "<aha-moment + open question — ≤15 words>",
  "cta": "",
  "caption": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
}
"""
```

### `pipeline/scene_planner.py` — Template Classifier Prompt

```python
# Available templates for middle beats
MIDDLE_TEMPLATES = {
    "pipeline":   "A step-by-step process flow (A→B→C→D). Best for: algorithms, training loops, data pipelines.",
    "comparison": "Side-by-side before/after or A vs B. Requires a concrete measurable difference.",
    "stats_grid": "Grid of 2-6 labeled stat cards (label + value). Best for: hardware specs, benchmarks.",
    "timeline":   "Vertical sequence of dated/ordered events. Best for: history, version milestones.",
}

SCENE_PLANNER_PROMPT = """\
You are a visual template classifier for short-form tech explainer videos.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}

SCRIPT CONCEPT BULLETS:
  concept_1: {bullets[0]}
  concept_2: {bullets[1]}
  concept_3: {bullets[2]}

AVAILABLE MIDDLE BEAT TEMPLATES:
  "pipeline":   A step-by-step process flow (A→B→C→D). Best for: algorithms, training loops.
  "comparison": Side-by-side before/after or A vs B. Requires a concrete measurable difference.
  "stats_grid": Grid of 2-6 labeled stat cards. Best for: hardware specs, benchmarks.
  "timeline":   Vertical sequence of dated/ordered events. Best for: history, milestones.

CLASSIFICATION RULES (strict priority):
1. Named specs, benchmarks, or 2+ statistics → "stats_grid"
2. Named sequential stages → "pipeline"
3. Two named things with measurable difference → "comparison"
4. Events with dates/versions → "timeline"
5. Never use "pipeline" for a list of specs

OUTPUT JSON:
{
  "beats": [
    {"beat": 1, "template": "hook"},
    {"beat": 2, "template": "<template>"},
    {"beat": 3, "template": "<template or omit>"},
    {"beat": 4, "template": "takeaway"}
  ]
}
"""
```

### `pipeline/param_extractor.py` — Per-Template Data Extraction Prompt

```python
# Template field specs
TEMPLATE_SPECS = {
    "hook": """\
  hook_stat : ≤8 chars — pure number/unit. "40%", "3×", "32GB". No sentences.
  hook_text : ≤8 words — sharpest phrase that makes someone stop scrolling.""",

    "stats_grid": """\
  concept_text : ≤7 words — what these stats describe.
  grid_items   : list of 2–6 objects. Each: {"label": "≤5 chars", "value": "≤8 chars"}
    GOOD: {"label": "VRAM", "value": "32GB"}
    BAD:  {"label": "memory bandwidth", "value": "608 gigabytes per second"}""",

    "pipeline": """\
  concept_text   : ≤7 words — name the process.
  pipeline_steps : 3–5 items, each ≤6 chars. Acronyms preferred.
    GOOD: ["RAW", "ISP", "HEVC", "GPU"]""",

    "comparison": """\
  concept_text  : ≤7 words — the contrast in one phrase.
  before_label  : ≤6 chars — topic-specific name. NEVER "old"/"before".
  after_label   : ≤6 chars — topic-specific name. NEVER "new"/"after".
  before_detail : ≤5 words — one sharp metric fact.
  after_detail  : ≤5 words — one sharp metric fact.""",

    "timeline": """\
  concept_text    : ≤7 words — what this timeline shows.
  timeline_events : 3–6 objects. Each: {"year": "≤6 chars", "label": "≤5 words"}""",

    "takeaway": """\
  takeaway_text : ≤12 words — closing statement. Big, bold, impactful.""",
}

PARAM_EXTRACTOR_PROMPT = """\
You are extracting structured visual parameters from a short video script.
Parameters slot into fixed Manim templates — you are NOT writing code.

TOPIC: {topic['title']}
TOPIC SUMMARY: {topic['summary']}

SCRIPT:
  hook:     {hook}
  {bullet_context}
  takeaway: {takeaway}

CRITICAL — all text renders LARGE on a phone screen. Keep everything SHORT.
Word/char limits are HARD. Count before outputting. Rewrite to fit.

PER-BEAT EXTRACTION SPEC:
{beat_specs}

GENERAL RULES:
- grid_items values: prefer numbers with units ("32GB", "290W") over prose
- before_label / after_label: never "old"/"new", never "before"/"after"
- concept_text: a punchy phrase, NOT a full sentence
- If a stat has no clear "before" state, it's stats_grid, not comparison

OUTPUT JSON:
{json_shape}

Return ONLY valid JSON. No markdown fences, no explanation.
"""
```

### `pipeline/narrator.py` — Narration Rewrite Prompt

```python
NARRATION_PROMPT = """\
You are writing a segmented voiceover for a short-form AI explainer (TikTok/Shorts style).
The goal is curiosity — make the viewer lean in, not tune out.

TOPIC: {topic['title']}

SOURCE MATERIAL:
  hook:          {script['hook']}
  concepts:
    bullet_1: {bullets[0]}
    bullet_2: {bullets[1]}
  takeaway:      {script['takeaway']}

Write spoken narration in this structure:

  "hook" (8-12 seconds):
    Open with the unexpected fact or contradiction — something that creates a "wait, what?" moment.
    Pose the question implicitly before you answer it. Use "you" to make it personal.
    GOOD: "Your GPU had plenty of memory. Your RAM had plenty of memory. So why did the process die?"
    BAD:  "Today we examine memory allocation patterns in PyTorch training pipelines."

  "concept_1", "concept_2" (12-18 seconds each):
    Start mid-thought — no "so", no "now", no preamble.
    Name the mechanism directly, then give the concrete number or fact.
    Mix short punchy sentences (4-6 words) with one medium sentence for rhythm.
    End with the implication — "which means", "so now", "and that changes everything."
    GOOD: "Two environment variables. That's it. MALLOC_ARENA_MAX caps how many memory arenas
           glibc spins up. Set it to 2, and your RSS drops — without touching a single line of model code."
    BAD:  "The mechanism involves setting environment variables that control memory allocation."

  "takeaway_cta" (10-16 seconds):
    Deliver the aha-moment — reframe what they just learned in one sharp sentence.
    End on a provocation or open question that makes them think beyond this topic.
    GOOD: "The allocator was eating your memory the whole time. The question isn't how to fix it —
           it's what else you're not measuring."
    BAD:  "In conclusion, these optimizations can significantly improve your training pipeline."

RULES:
- Write for speaking, not reading. Natural rhythm and breath pauses.
- No hedging: "basically", "kind of", "essentially" — cut them all.
- NEVER say "video", "animation", "screen", "visual", "watch", "subscribe", "follow".
- No news-anchor phrasing: "Today we look at...", "In this segment...", "As we can see..."
- Use contractions naturally: "it's", "that's", "you're", "doesn't"
- Each section must stand alone — it will be spliced independently

Return ONLY valid JSON with keys: "hook", "concept_1", "concept_2", "takeaway_cta"
"""
```

---

## 4. THE RENDERER (CRITICAL)

### Color Palette & Font Size Constants

```python
# ── Palette ───────────────────────────────────────────────────────────────────
C_WHITE  = "#FDFDFD"
C_GREEN  = "#00FF41"   # matrix green — stats, arrows, positive indicators
C_CYAN   = "#00E5FF"   # electric cyan — boxes, borders, labels
C_YELLOW = "#FFD600"   # warm yellow — concept headers
C_RED    = "#FF4444"   # alert red — "before" / negative state

# ── Font sizes (portrait frame: 1080×1920, 25.3 Manim units tall) ─────────────
# 1 Manim unit ≈ 76px. Sizes tuned for 8-20% screen height per element.
FS_STAT     = 300   # hook key number — hero element, dominates screen
FS_HOOK     = 120   # hook phrase (5-8 words)
FS_CONCEPT  = 100   # concept header (5-7 words)
FS_LABEL    = 80    # panel/card section titles
FS_DETAIL   = 68    # panel content / detail text
FS_TAKEAWAY = 160   # closing takeaway — big, bold, impactful

# ── Zone layout (portrait frame: 14.2w × 25.3h) ──────────────────────────────
# TEXT ZONE  : y ≥ 6    (top ~35% — concept headers only)
# BUFFER     : y = 2–6  (breathing room — nothing lives here)
# ANIM ZONE  : y ≤ 2    (bottom ~60% — all animated elements)
```

### `pipeline/animator.py` — Scene Assembly

```python
def assemble_scene(params: dict, timing: dict, scene_plan: dict) -> str:
    from pipeline.templates import (
        beat1_hook, beat2_pipeline, beat3_before_after, beat4_takeaway,
        beat_stats_grid, beat_timeline,
    )

    TEMPLATE_MAP = {
        "hook":       beat1_hook,
        "pipeline":   beat2_pipeline,
        "comparison": beat3_before_after,
        "stats_grid": beat_stats_grid,
        "timeline":   beat_timeline,
        "takeaway":   beat4_takeaway,
    }

    beats = scene_plan.get("beats", [])
    total = len(beats)

    def beat_duration(beat_num: int) -> float:
        if beat_num == 1:
            key = "hook"
        elif beat_num == total:
            key = "takeaway_cta"
        else:
            middle_idx = beat_num - 2
            key = f"concept_{middle_idx + 1}"
        return timing.get(key, {}).get("duration", 12.0)

    beat_blocks = []
    for beat in beats:
        beat_num    = beat["beat"]
        template    = beat["template"]
        module      = TEMPLATE_MAP[template]
        beat_params = params.get(f"beat_{beat_num}", params)
        duration    = beat_duration(beat_num)
        beat_blocks.append(module.generate(beat_params, duration))

    return (
        MANIM_HEADER
        + "class ContentScene(Scene):\n"
        + "    def construct(self):\n"
        + "\n".join(beat_blocks) + "\n"
    )
```

### `pipeline/templates/beat1_hook.py`

```python
"""
Beat 1 — Hook
Layout:
  y = 6.0  — stat (FS_STAT=300, GrowFromCenter animation)
  y =-1.0  — hook phrase (FS_HOOK=120, width=10.0)
"""

def generate(params: dict, duration: float) -> str:
    stat = params.get("hook_stat", "").replace("\\", "\\\\").replace('"', '\\"')
    text = params.get("hook_text", "").replace("\\", "\\\\").replace('"', '\\"')

    anim_stat = 1.0
    anim_hook = 0.8
    anim_out  = 0.5
    wait_time = max(round(duration - anim_stat - anim_hook - anim_out, 2), 0.1)

    return (
        "        # ── BEAT 1: HOOK\n"
        f'        _b1_stat = Text("{stat}", font_size=FS_STAT, color=C_GREEN, font="Monospace")\n'
        "        _b1_stat.move_to(np.array([0.0, 6.0, 0.0]))\n"
        f'        _b1_hook = Text("{text}", font_size=FS_HOOK, color=C_WHITE, font="Monospace", width=10.0)\n'
        "        _b1_hook.move_to(np.array([0.0, -1.0, 0.0]))\n"
        f"        self.play(GrowFromCenter(_b1_stat), run_time={anim_stat})\n"
        f"        self.play(FadeIn(_b1_hook), run_time={anim_hook})\n"
        f"        self.wait({wait_time})\n"
        f"        self.play(FadeOut(_b1_stat), FadeOut(_b1_hook), run_time={anim_out})\n"
    )
```

### `pipeline/templates/beat_stats_grid.py`

```python
"""
Beat — Stats Grid
Grid of 2-6 labeled stat cards. Concept header in TEXT ZONE, cards in ANIM ZONE.
Each card: label (top, C_CYAN, FS_DETAIL) + value (center, C_WHITE, FS_LABEL).

Grid layouts:
  2 items → 2 tall side-by-side panels
  3 items → single column
  4 items → 2×2 grid
  5 items → 2+3 rows
  6 items → 2×3 grid
"""

def _layout(n: int):
    if n == 2:
        return [(-3.5, -4.0), (3.5, -4.0)], (5.5, 8.5)
    elif n == 3:
        return [(0.0, 0.0), (0.0, -5.0), (0.0, -10.0)], (8.5, 3.8)
    elif n == 4:
        return [(-3.5, -0.5), (3.5, -0.5), (-3.5, -7.5), (3.5, -7.5)], (5.5, 5.5)
    elif n == 5:
        return [(-3.5, 0.5), (3.5, 0.5), (-5.0, -6.5), (0.0, -6.5), (5.0, -6.5)], (5.5, 5.0)
    else:
        return [(-5.0, 0.5), (0.0, 0.5), (5.0, 0.5),
                (-5.0, -6.5), (0.0, -6.5), (5.0, -6.5)], (4.2, 5.0)

def generate(params: dict, duration: float) -> str:
    concept = params.get("concept_text", "")
    items   = params.get("grid_items", [])[:6]
    n       = len(items)
    positions, (card_w, card_h) = _layout(n)
    val_max_w = round(card_w - 0.8, 1)

    # For each card:
    #   Rectangle border (C_CYAN, fill_opacity=0.05)
    #   Label at card_top - 0.9  (FS_DETAIL, C_CYAN)
    #   Value at card center - 0.2  (FS_LABEL, C_WHITE)
    #   scale_to_fit_width applied conditionally to prevent overflow
    ...
```

### `pipeline/templates/beat2_pipeline.py`

```python
"""
Beat 2 — Pipeline (VERTICAL layout)
Concept text at y=8.5. Steps stack vertically from y=2.0 down.
Arrows connect boxes on the same x=0 axis.
Box width=5.0 to prevent label overflow.
Labels use conditional scale_to_fit_width to ensure uniform size.
"""

def generate(params: dict, duration: float) -> str:
    concept = params.get("concept_text", "")
    steps   = params.get("pipeline_steps", [])[:5]
    n       = len(steps)

    v_span  = 10.5   # ANIM ZONE height
    spacing = round(v_span / n, 3)
    box_h   = round(min(2.4, spacing - 0.8), 2)
    box_w   = 5.0
    y_first = 2.0
    centers = [round(y_first - i * spacing, 3) for i in range(n)]

    # Concept text at y=8.5 with width=10.0
    # Boxes: Rectangle(width=5.0, height=box_h, color=C_CYAN)
    # Labels: Text at box center, NO width= param (prevents scaling short labels up)
    #         if label.width > 4.6: label.scale_to_fit_width(4.6)
    # Arrows: vertical Arrow from box_bottom to next_box_top, color=C_GREEN
    ...
```

### `pipeline/templates/beat3_before_after.py`

```python
"""
Beat 3 — Before / After (two-panel comparison, NO bars)
Layout:
  Concept text at y=8.5 (width=10.0)
  Left panel  (C_RED border,   fill_opacity=0.05) — BEFORE state
  Right panel (C_GREEN border, fill_opacity=0.05) — AFTER state

Panel geometry:
  xL=-3.0, xR=3.0, pw=5.0, ph=11.0, pcy=-3.0
  y_title  = pcy + ph/2 - 1.5 = 2.0   (section label near top)
  y_detail = pcy - 0.5        = -3.5   (metric fact mid-lower)

Inside each panel:
  Section label (FS_LABEL=80)  — e.g. "FA2" / "FA3"
  Detail line   (FS_DETAIL=68) — e.g. "120ms prefill" / "72ms, 40% faster"
"""

def generate(params: dict, duration: float) -> str:
    concept      = params.get("concept_text", "")
    before_label = params.get("before_label", "BEFORE")
    after_label  = params.get("after_label",  "AFTER")
    before_det   = params.get("before_detail", "")
    after_det    = params.get("after_detail",  "")
    ...
```

### `pipeline/templates/beat_timeline.py`

```python
"""
Beat — Timeline (vertical spine)
Layout:
  Concept text at y=8.5 (TEXT ZONE)
  Vertical spine at x=-1.0 (C_CYAN line)
  Per event:
    Dot on spine       (C_GREEN, radius=0.18)
    Year label x=-4.5  (FS_DETAIL, C_GREEN)
    Event label x=2.5  (FS_DETAIL, C_WHITE, width=6.5)

Spacing: max 4.5 units between events (y_top=1.5, y_bot dynamic)
"""
```

### `pipeline/templates/beat4_takeaway.py`

```python
"""
Beat 4 — Takeaway
Single large text centered at y=0.0
FS_TAKEAWAY=160, width=10.0 (keeps ≤12 words on 1-2 lines)
Animation: Write → wait → FadeOut
"""

def generate(params: dict, duration: float) -> str:
    text = params.get("takeaway_text", "")

    anim_in   = 1.5
    anim_out  = 0.5
    wait_time = max(round(duration - anim_in - anim_out, 2), 0.1)

    # Text("{text}", font_size=FS_TAKEAWAY, color=C_WHITE, font="Monospace", width=10.0)
    # move_to(np.array([0.0, 0.0, 0.0]))
    ...
```

---

## 5. THE AUDIO

### `pipeline/narrator.py` — TTS Configuration

```python
TTS_MODEL  = "gemini-2.5-flash-preview-tts"
VOICE_NAME = os.environ.get("TTS_VOICE", "Puck")  # Puck = fast-paced, Shorts-native
# Other options:
#   Charon / Kore    — authoritative, news/finance
#   Fenrir / Aoede   — warm, long-form explainers
#   Zephyr           — high energy female, Shorts

# Directorial cue prepended to every TTS segment.
# Gemini 2.5 TTS reads this and alters pacing/delivery physically.
VOICE_DIRECTIVE = (
    "Say this in a fast-paced, curious tech explainer style — "
    "punchy and energetic, like you're revealing something most people don't know. "
    "Build tension in the hook, deliver facts with conviction, "
    "use natural breath pauses for emphasis, and land the ending with a sharp edge: "
)
```

### TTS API Call

```python
def call_tts(text: str, api_key: str) -> bytes:
    directed_text = VOICE_DIRECTIVE + text  # directorial cue shapes delivery
    payload = json.dumps({
        "contents": [{"parts": [{"text": directed_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": VOICE_NAME}
                }
            },
        },
    }).encode()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent?key=<REDACTED>"
    # Returns raw PCM audio (16-bit, 24000 Hz, mono)
    # Duration measured as: len(pcm_bytes) / (24000 * 2)
```

### Timing Output (`output/narration_timing.json`)

```json
{
  "hook": {
    "start": 0.0,
    "duration": 9.2,
    "end": 9.2,
    "text": "Your GPU had plenty of memory..."
  },
  "concept_1": {
    "start": 9.2,
    "duration": 14.5,
    "end": 23.7,
    "text": "Two environment variables..."
  },
  "concept_2": {
    "start": 23.7,
    "duration": 13.8,
    "end": 37.5,
    "text": "Before: RSS climbs 3GB/hour..."
  },
  "takeaway_cta": {
    "start": 37.5,
    "duration": 11.3,
    "end": 48.8,
    "text": "The allocator was eating your memory..."
  }
}
```

### `pipeline/mixer.py` — FFmpeg A/V Merge

```python
"""
Merges output/video.mp4 + output/narration.wav → output/video_final.mp4
Stretches/compresses video PTS to match exact audio duration.
"""

# Video filter: scale video time to match audio duration
pts_scale = v_dur / a_dur   # <1 speeds up, >1 slows down
vf = f"setpts={pts_scale:.6f}*PTS"

# Optional audio post-processing (env vars)
# AUDIO_TEMPO=1.1  → atempo filter (speeds up speech)
# AUDIO_LOWPASS=8000 → lowpass filter (warms up TTS voice)

subprocess.run([
    "ffmpeg", "-y",
    "-i", "output/video.mp4",
    "-i", "output/narration.wav",
    "-vf", vf,
    "-af", af,          # "anull" if no post-processing
    "-c:v", "libx264",
    "-crf", "18",
    "-preset", "fast",
    "-c:a", "aac",
    "-b:a", "192k",
    "output/video_final.mp4",
])
```

---

## Key Output Files

| File | Stage | Contents |
|---|---|---|
| `output/candidates.json` | scraper | Raw Reddit + arXiv posts |
| `output/topic.json` | ranker | Single selected topic with why_picked |
| `output/script.json` | scripter | hook, concept_bullets, takeaway (on-screen text) |
| `output/scene_plan.json` | scene_planner | `[{beat, template}]` ordered list |
| `output/params.json` | param_extractor | Per-beat structured data for each template |
| `output/narration.wav` | narrator | Stitched PCM audio (24kHz mono) |
| `output/narration_timing.json` | narrator | Per-segment start/duration/end/text |
| `output/video.mp4` | animator | Silent Manim render (1080×1920) |
| `output/video_final.mp4` | mixer | Final video with synced audio |

---

## Environment Variables (secrets redacted)

```env
TELEGRAM_BOT_TOKEN=<REDACTED>
TELEGRAM_CHAT_ID=<REDACTED>
GEMINI_API_KEY=<REDACTED>
GEMINI_API_KEYS=<REDACTED>,<REDACTED>   # optional multi-key rotation
TTS_VOICE=Puck                           # voice name (default: Puck)
AUDIO_TEMPO=1.0                          # 1.0 = no change, 1.1 = 10% faster
AUDIO_LOWPASS=0                          # Hz cutoff, 0 = disabled
SUBREDDITS=r/MachineLearning,r/LocalLLaMA,r/deeplearning
```
