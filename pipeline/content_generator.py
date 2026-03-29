"""
content_generator.py — Single-shot structured content generation.

Replaces four pipeline stages in ONE validated LLM call:
    scripter  →  scene_planner  →  param_extractor  →  narrator (LLM rewrite step)

Outputs four files that the rest of the pipeline consumes unchanged:
    output/script.json            ← scripter-compatible (for narrator TTS skip)
    output/spoken_narration.json  ← keys: hook, concept_1…N, takeaway_cta
    output/params.json            ← ScenePayload format for Remotion
    output/scene_plan.json        ← beat list for animator
    cue_definitions.json          ← animation trigger map

Usage:
    python -m pipeline.content_generator          # uses FORCE_PROVIDER env var
    python -m pipeline.content_generator --topic "KV Cache Dequantization"

Install deps (not in requirements.txt yet):
    pip install instructor anthropic pydantic>=2.0
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Paths ──────────────────────────────────────────────────────────────────────

_ROOT       = os.path.join(os.path.dirname(__file__), "..")
TOPIC_PATH  = os.path.join(_ROOT, "output", "topic.json")
SCRIPT_OUT  = os.path.join(_ROOT, "output", "script.json")
SPOKEN_OUT  = os.path.join(_ROOT, "output", "spoken_narration.json")
PARAMS_OUT  = os.path.join(_ROOT, "output", "params.json")
PLAN_OUT    = os.path.join(_ROOT, "output", "scene_plan.json")
CUES_OUT    = os.path.join(_ROOT, "cue_definitions.json")

# ══════════════════════════════════════════════════════════════════════════════
# § 1  PYDANTIC SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class LayoutMode(str, Enum):
    METRIC     = "metric"
    COMPARISON = "comparison"
    PIPELINE   = "pipeline"


# ── Shared sub-objects ────────────────────────────────────────────────────────

class MetricItem(BaseModel):
    """One data point on a card (≤ 8 chars each for mobile legibility)."""
    label: str = Field(max_length=10, description="Short axis label, e.g. 'dequant %'")
    value: str = Field(max_length=10, description="Formatted value, e.g. '40 %'")
    color: Literal["green", "cyan", "yellow", "red", "white"] = "white"
    glow: bool = False


class PipelineStep(BaseModel):
    label:    str = Field(max_length=14, description="Node name shown on screen")
    sublabel: str | None = Field(default=None, max_length=10, description="e.g. '12 ms'")
    state:    Literal["idle", "active", "bottleneck"] = "idle"


class ComparisonPanel(BaseModel):
    heading: str = Field(max_length=16)
    color:   Literal["green", "cyan", "yellow", "red", "white"]
    metrics: list[MetricItem] = Field(min_length=1, max_length=4)


# ── Per-layout UIContent types ────────────────────────────────────────────────
# Discriminated union on the `layout` literal field.
# Each type maps 1-to-1 to a Remotion layout component.

class MetricUIContent(BaseModel):
    """Hero metric card — single big number + supporting context."""
    layout:        Literal["MetricFocus"]
    section_label: str = Field(max_length=24, description="UPPERCASE micro-label, e.g. 'THE BOTTLENECK'")
    hero:          MetricItem = Field(description="The ONE number that lands the point")
    context:       str  = Field(
        max_length=140,
        description=(
            "1-2 declarative sentences. No markdown. "
            "Separate sentences with a single space — React renders this verbatim."
        ),
    )
    chips: list[str] = Field(
        min_length=2, max_length=3,
        description="2-3 short tags ≤ 16 chars each, e.g. ['llama.cpp', 'M5 Max', '32K ctx']",
    )

    @field_validator("chips")
    @classmethod
    def chips_length(cls, v: list[str]) -> list[str]:
        for chip in v:
            if len(chip) > 16:
                raise ValueError(f"Chip '{chip}' exceeds 16 chars — shorten it.")
        return v


class ComparisonUIContent(BaseModel):
    """Side-by-side A vs B panel."""
    layout:         Literal["ComparisonSplit"]
    section_label:  str = Field(max_length=24)
    left:           ComparisonPanel
    right:          ComparisonPanel
    divider_label:  str = Field(default="vs", max_length=5)


class PipelineUIContent(BaseModel):
    """Step-by-step process flow with bottleneck annotation."""
    layout:             Literal["PipelineFlow"]
    section_label:      str = Field(max_length=24)
    steps:              list[PipelineStep] = Field(min_length=3, max_length=5)
    flow_direction:     Literal["horizontal", "vertical"] = "horizontal"
    bottleneck_label:   str | None = Field(
        default=None, max_length=30,
        description="Short annotation below the bottleneck step, e.g. '40 % of decode time'",
    )


# Discriminated union — Pydantic narrows automatically on `layout` field
UIContent = Annotated[
    Union[MetricUIContent, ComparisonUIContent, PipelineUIContent],
    Field(discriminator="layout"),
]


# ── Narration schema ──────────────────────────────────────────────────────────

class NarrationScript(BaseModel):
    """
    Four spoken blocks — total MUST land between 130 and 145 words.

    Timing targets (Senior ML Engineer at ~135 WPM):
        hook     →  8-12 s  ≈  18-27 words
        context  → 12-15 s  ≈  27-34 words
        insight  → 15-20 s  ≈  34-45 words
        takeaway → 10-14 s  ≈  22-32 words
    """
    hook: str = Field(
        description=(
            "State the broken assumption or surprising metric. ONE concrete number. "
            "Use 'you' / 'your'. End with the implicit question, not the answer. "
            "≤ 28 words."
        ),
    )
    context: str = Field(
        description=(
            "Name the exact mechanism — the variable, layer, or operation causing it. "
            "No analogies. No 'basically'. ≤ 36 words."
        ),
    )
    insight: str = Field(
        description=(
            "The non-obvious implication. What this changes about how engineers should "
            "build or measure. Mix short punchy sentences with one medium sentence. ≤ 45 words."
        ),
    )
    takeaway: str = Field(
        description=(
            "One sharp sentence restating what they now know. "
            "End with a provocation that makes them think beyond this topic. ≤ 28 words."
        ),
    )

    @model_validator(mode="after")
    def enforce_word_budget(self) -> "NarrationScript":
        full = f"{self.hook} {self.context} {self.insight} {self.takeaway}"
        total = len(full.split())
        if not (130 <= total <= 145):
            raise ValueError(
                f"Total narration is {total} words — must be 130-145. "
                f"Adjust sections: hook={len(self.hook.split())}, "
                f"context={len(self.context.split())}, "
                f"insight={len(self.insight.split())}, "
                f"takeaway={len(self.takeaway.split())}."
            )
        return self


# ── Cue definitions ───────────────────────────────────────────────────────────

class CueDefinition(BaseModel):
    """
    Intent-based animation trigger aligned to a word in the narration.

    Convention for `label` — use verb_noun:
        metric_reveal, split_enter, bottleneck_show, insight_drop, takeaway_flash
    """
    label:         str = Field(
        pattern=r"^[a-z][a-z0-9_]{2,29}$",
        description="Snake-case intent label, e.g. 'metric_reveal'",
    )
    trigger_word:  str = Field(
        min_length=3,
        description="Exact word in the narration that fires this cue",
    )
    occurrence:    int = Field(
        default=0,
        ge=-1,
        description="0 = first match, 1 = second, -1 = last match in narration",
    )
    offset_frames: int = Field(
        default=0,
        ge=-30, le=30,
        description="Frame offset from trigger word onset. Negative = anticipate.",
    )


# ── Root payload ──────────────────────────────────────────────────────────────

class VideoPayload(BaseModel):
    """
    Complete structured payload for one short-form AI explainer video.

    layout_mode selects the Remotion layout component for concept beats.
    ui_content is auto-narrowed by Pydantic to the matching sub-type.
    """
    layout_mode:     LayoutMode
    ui_content:      UIContent
    narration:       NarrationScript
    cue_definitions: list[CueDefinition] = Field(
        min_length=2, max_length=5,
        description="2-5 cues aligned to meaningful moments in the narration",
    )

    @model_validator(mode="after")
    def layout_content_agreement(self) -> "VideoPayload":
        """layout_mode and ui_content.layout must refer to the same template."""
        mapping = {
            LayoutMode.METRIC:     "MetricFocus",
            LayoutMode.COMPARISON: "ComparisonSplit",
            LayoutMode.PIPELINE:   "PipelineFlow",
        }
        expected = mapping[self.layout_mode]
        actual   = self.ui_content.layout
        if actual != expected:
            raise ValueError(
                f"layout_mode='{self.layout_mode}' expects ui_content.layout='{expected}' "
                f"but got '{actual}'."
            )
        return self


# ══════════════════════════════════════════════════════════════════════════════
# § 2  SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = textwrap.dedent("""
    You are writing a 60-second AI explainer for Instagram Reels / YouTube Shorts.
    Your audience: anyone technically curious — from a Python developer who has never touched ML
    to a seasoned data scientist who wants a sharp refresher. Write so both can follow.
    The non-expert must understand the WHAT. The expert must feel the WHY is worth their time.

    ═══════════════════════════════════════════════════════
     VOICE  —  TL;DR to a smart colleague, not a lecture
    ═══════════════════════════════════════════════════════
    • Speak like you're at a whiteboard after a postmortem, not presenting at a conference.
    • Staccato, declarative sentences. Short. Punchy. One idea per sentence.
    • You may use one medium-length sentence per block for rhythm — not more.
    • Contractions only: "it's", "that's", "you're", "doesn't". No formal conjugations.

    ═══════════════════════════════════════════════════════
     WORD BUDGET  —  HARD LIMIT, NO EXCEPTIONS
    ═══════════════════════════════════════════════════════
    Total narration (hook + context + insight + takeaway): 130-145 words.
    • hook:     ≤ 28 words
    • context:  ≤ 36 words
    • insight:  ≤ 45 words
    • takeaway: ≤ 28 words

    Count every word. If you are over, cut adverbs first, then adjectives, then clauses.
    Never pad to hit a minimum — dead words are worse than being 2 words short.

    ═══════════════════════════════════════════════════════
     THE 10-SECOND RULE  —  EVERY BLOCK MUST ADVANCE
    ═══════════════════════════════════════════════════════
    Hook     → surface the broken assumption or surprising metric (the "wait, what?")
    Context  → name the exact mechanism — the variable, layer, operation, or line of code
    Insight  → state the non-obvious implication — what changes for how engineers build
    Takeaway → one sharp reframe + a provocation that leaves them thinking

    If a block does NOT advance the concept, DELETE it. There is no "warm up" section.
    The viewer's attention is a debt that must be repaid every 10 seconds.

    ═══════════════════════════════════════════════════════
     BANNED PHRASES  —  INSTANT REJECT IF ANY APPEAR
    ═══════════════════════════════════════════════════════
    "Imagine"                   "What if I told you"
    "Have you ever"             "Let's dive in"
    "In this video"             "Today we're going to"
    "At its core"               "Essentially"
    "Basically"                 "Kind of"
    "In a nutshell"             "The bottom line is"
    "In conclusion"             "As we can see"
    "It's worth noting"         "Interestingly"
    "Needless to say"           "Simply put"

    ═══════════════════════════════════════════════════════
     ON-SCREEN TEXT RULES  (ui_content field)
    ═══════════════════════════════════════════════════════
    • section_label: ALL CAPS, ≤ 24 chars, describes the visual frame not the topic.
      GOOD: "THE BOTTLENECK" / "BEFORE vs AFTER" / "THE FIX"
      BAD:  "TurboQuant Algorithm" / "Memory Optimization"

    • MetricFocus context: TWO short sentences separated by ONE space. No line breaks.
      React renders this verbatim — spaces matter.

    • MetricFocus chips: 2-3 tags ≤ 16 chars. These are environment or context tags,
      not summaries: ["M5 Max", "llama.cpp", "32K ctx"] not ["Faster", "Better", "Cheaper"].

    • ComparisonSplit metrics: 2-4 items per panel. label ≤ 8 chars, value ≤ 8 chars.
      Use real numbers from the topic summary. Never invent benchmarks.

    • PipelineFlow steps: 3-5 nodes. Exactly ONE step should have state="bottleneck".
      bottleneck_label annotates it with the cost, e.g. "40 % decode time".

    ═══════════════════════════════════════════════════════
     CUE DEFINITIONS  (animation sync)
    ═══════════════════════════════════════════════════════
    Provide 2-5 cues. Each cue fires an animation when a specific word is spoken.
    • label: snake_case intent verb, e.g. "metric_reveal", "bottleneck_show", "split_enter"
    • trigger_word: a content word (noun/verb) from the NARRATION, not a function word
    • occurrence: 0=first match, -1=last match in narration audio
    • offset_frames: use negative to anticipate (-8 to -12 typical), 0 for simultaneous

    The cue for the main visual reveal should use offset_frames: -12 to lead by ~0.4s.
""").strip()


# ══════════════════════════════════════════════════════════════════════════════
# § 3  ORCHESTRATION
# ══════════════════════════════════════════════════════════════════════════════

def _user_prompt(topic: dict) -> str:
    """Build the per-run user message from the scraped topic."""
    return textwrap.dedent(f"""
        TOPIC:   {topic["title"]}
        SUMMARY: {topic.get("summary", "").strip()}

        Generate a VideoPayload JSON for this topic.
        Choose the layout_mode that best fits the content:
          - "metric"     → one hero number defines the insight (e.g. "40 % dequant overhead")
          - "comparison" → clear before/after or A-vs-B with measurable delta
          - "pipeline"   → a process with 3-5 named sequential stages and one bottleneck

        Only use numbers that appear in the SUMMARY above.
        Do NOT invent benchmarks, latency figures, or accuracy numbers.
    """).strip()


def generate(topic: dict, max_retries: int = 3) -> VideoPayload:
    """
    Call the LLM and return a validated VideoPayload.

    Provider selection (mirrors run.py FORCE_PROVIDER logic):
        FORCE_PROVIDER=gemini   → instructor + Gemini 2.5 Flash
        FORCE_PROVIDER=anthropic → instructor + Anthropic SDK
        anything else            → fallback to claude_client.py + manual parse
    """
    provider = os.environ.get("FORCE_PROVIDER", "claude")

    if provider == "gemini":
        return _generate_gemini(topic, max_retries)
    elif provider == "anthropic":
        return _generate_anthropic(topic, max_retries)
    else:
        # Claude Code CLI path — no Anthropic SDK key needed
        return _generate_claude_cli(topic, max_retries)


# ── Gemini path (instructor) ───────────────────────────────────────────────────

def _generate_gemini(topic: dict, max_retries: int) -> VideoPayload:
    try:
        import instructor
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "Gemini path requires: pip install instructor google-generativeai"
        )

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEYS", "").split(",")[0]
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set.")

    genai.configure(api_key=api_key.strip())
    model_name = os.environ.get("GEMINI_MODEL_CONTENT_GENERATOR", "gemini-2.5-flash")

    client = instructor.from_gemini(
        client=genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
        ),
        mode=instructor.Mode.GEMINI_JSON,
    )

    print(f"[content_generator] Gemini  model={model_name}  max_retries={max_retries}")
    payload, _ = client.chat.completions.create_with_completion(
        messages=[{"role": "user", "content": _user_prompt(topic)}],
        response_model=VideoPayload,
        max_retries=max_retries,
    )
    return payload


# ── Anthropic path (instructor) ───────────────────────────────────────────────

def _generate_anthropic(topic: dict, max_retries: int) -> VideoPayload:
    try:
        import instructor
        from anthropic import Anthropic
    except ImportError:
        raise ImportError(
            "Anthropic path requires: pip install instructor anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")

    client = instructor.from_anthropic(Anthropic(api_key=api_key))
    model  = "claude-sonnet-4-6"

    print(f"[content_generator] Anthropic  model={model}  max_retries={max_retries}")
    payload = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(topic)}],
        response_model=VideoPayload,
        max_retries=max_retries,
    )
    return payload


# ── Claude CLI fallback (no SDK key needed) ───────────────────────────────────

def _generate_claude_cli(topic: dict, max_retries: int) -> VideoPayload:
    """
    Uses the existing claude_client.py subprocess path.
    Parses the JSON manually and validates through Pydantic.
    Works inside an active Claude Code session without any API key.
    """
    import re
    from pipeline import claude_client

    combined_prompt = f"{SYSTEM_PROMPT}\n\n{_user_prompt(topic)}\n\nReturn ONLY valid JSON matching the VideoPayload schema."

    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = claude_client.call(combined_prompt, stage="content_generator", json_mode=True)

            # Strip markdown fences if present
            if "```" in raw:
                for part in raw.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        raw = part
                        break

            start, end = raw.find("{"), raw.rfind("}") + 1
            if start != -1 and end > start:
                raw = raw[start:end]
            raw = re.sub(r",\s*([\]}])", r"\1", raw)   # repair trailing commas

            data    = json.loads(raw)
            payload = VideoPayload.model_validate(data)
            print(f"[content_generator] Claude CLI  attempt={attempt}  ✓")
            return payload

        except Exception as e:
            last_err = e
            print(f"[content_generator] attempt {attempt}/{max_retries} failed: {e}")

    raise RuntimeError(
        f"content_generator failed after {max_retries} attempts. "
        f"Last error: {last_err}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# § 4  PIPELINE OUTPUT SERIALISATION
#     Converts VideoPayload → the 4 files that downstream stages expect
# ══════════════════════════════════════════════════════════════════════════════

_LAYOUT_TO_ANIMATE_IN = {
    "MetricFocus":     "spring_scale",
    "ComparisonSplit": "spring_in",
    "PipelineFlow":    "slide_up",
}

_LAYOUT_TO_TEMPLATE = {
    "MetricFocus":     "stats_grid",   # closest scene_planner hint
    "ComparisonSplit": "comparison",
    "PipelineFlow":    "pipeline",
}


def _build_script_json(payload: VideoPayload, topic: dict) -> dict:
    """
    Produce script.json in the format scripter.py emits.
    narrator.py reads this to count bullets and for the visual hook text.
    """
    ui = payload.ui_content

    # Hook visual: pull the hero value if MetricFocus, else section_label
    if isinstance(ui, MetricUIContent):
        hook_visual = f"{ui.hero.value} {ui.hero.label}. {ui.context}"
    elif isinstance(ui, ComparisonUIContent):
        hook_visual = f"{ui.left.heading} vs {ui.right.heading}. {ui.section_label}."
    else:  # PipelineFlow
        hook_visual = f"{ui.section_label}. {ui.steps[0].label} → … → {ui.steps[-1].label}."

    # Map narration blocks → concept_bullets for narrator.py's bullet counter
    concept_bullets = [
        payload.narration.context,
        payload.narration.insight,
    ]

    return {
        "hook":            payload.narration.hook,
        "concept_bullets": concept_bullets,
        "takeaway":        payload.narration.takeaway,
        "hook_visual":     hook_visual,  # extra field — narrator.py ignores unknown keys
        "cta":             "",
        "caption": (
            f"{topic['title']}. "
            f"{payload.narration.hook} "
            f"{payload.narration.takeaway}"
        )[:280],
        "hashtags": ["#MachineLearning", "#MLEngineering", "#AI", "#LLM", "#MLOps"],
    }


def _build_spoken_narration(payload: VideoPayload) -> dict:
    """
    Produce spoken_narration.json with keys narrator.py uses for TTS.
    Bypasses narrator.py's LLM-rewrite step entirely.
    """
    return {
        "hook":         payload.narration.hook,
        "concept_1":    payload.narration.context,
        "concept_2":    payload.narration.insight,
        "takeaway_cta": payload.narration.takeaway,
    }


def _build_params_json(payload: VideoPayload) -> dict:
    """
    Produce params.json: { beat_N: ScenePayload } for Remotion's SceneRouter.

    Beat structure (always 4 beats for this 4-segment narration design):
        beat_1: MetricFocus    ← hook — hero number teaser
        beat_2: <layout_mode>  ← main concept visual
        beat_3: KineticBridge  ← insight keywords — never a duplicate of beat_2
        beat_4: TakeawayScene  ← outro
    """
    ui   = payload.ui_content
    data = ui.model_dump()
    anim = _LAYOUT_TO_ANIMATE_IN.get(ui.layout, "spring_in")

    hook_section = ui.section_label

    # beat_1: always MetricFocus — the hook number.
    # beat_2: always the LLM-chosen layout (ComparisonSplit / PipelineFlow / DataGrid).
    #         For MetricFocus topics, synthesise a DataGrid from context + chips so
    #         beat_2 is VISUALLY DIFFERENT from beat_1 — no duplicate screens.
    if isinstance(ui, MetricUIContent):
        hook_data = data.copy()
        # beat_2 for MetricFocus: DataGrid with supporting metrics derived from chips + context
        chip_metrics = [
            {"label": c[:8], "value": "—", "color": "cyan"}
            for c in (ui.chips or [])[:3]
        ]
        if not chip_metrics:
            chip_metrics = [{"label": "detail", "value": "—", "color": "cyan"}]
        beat2_data = {
            "layout":          "DataGrid",
            "section_label":   hook_section,
            "metrics":         chip_metrics,
            "highlight_index": 0,
            "caption":         ui.context[:80] if ui.context else "",
        }
    else:
        hook_data = {
            "layout":        "MetricFocus",
            "section_label": hook_section,
            "hero":          {"value": "?", "label": ui.section_label[:10], "color": "cyan"},
            "context":       payload.narration.hook,
            "chips":         [ui.section_label[:16]],
        }
        beat2_data = data

    # beat_3: KineticBridge — 3-4 meaningful keywords from the insight block.
    # Prefer longer content words; skip stop words and very short tokens.
    _stop = {"this", "that", "with", "from", "they", "their", "about", "which",
             "will", "have", "been", "into", "your", "more", "also", "when",
             "these", "than", "both", "just", "now"}
    bridge_keywords = [
        w.strip(".,;:?!\"'()") for w in payload.narration.insight.split()
        if len(w.strip(".,;:?!\"'()")) >= 5
        and w.strip(".,;:?!\"'()").lower() not in _stop
    ][:4]
    if len(bridge_keywords) < 2:
        bridge_keywords = ["key insight", "think about it"]
    bridge_keywords = [w[:20] for w in bridge_keywords]

    # TakeawayScene headline: first complete sentence, ≤ 16 words, no ellipsis.
    headline = payload.narration.takeaway
    if "." in headline:
        first_sentence = headline.split(".")[0].strip()
        if 4 <= len(first_sentence.split()) <= 18:
            headline = first_sentence
    words = headline.split()
    if len(words) > 16:
        headline = " ".join(words[:16])

    return {
        "beat_1": {
            "animate_in": "spring_scale",
            "data": hook_data,
        },
        "beat_2": {
            "animate_in": "spring_in",
            "data": beat2_data,
        },
        "beat_3": {
            "animate_in": "fade",
            "data": {
                "layout":        "KineticBridge",
                "section_label": hook_section,
                "keywords":      bridge_keywords,
                "accent_color":  "cyan",
            },
        },
        "beat_4": {
            "animate_in": "none",
            "data": {
                "layout":        "TakeawayScene",
                "section_label": "TAKEAWAY",
                "headline":      headline,
                "accent_color":  "cyan",
            },
        },
    }


def _build_scene_plan() -> dict:
    """
    Produce scene_plan.json matching the 4-beat structure above.
    animator.py reads this for beat templates and the beat list.
    """
    return {
        "beats": [
            {"beat": 1, "template": "hook"},
            {"beat": 2, "template": "stats_grid"},
            {"beat": 3, "template": "bridge"},
            {"beat": 4, "template": "takeaway"},
        ]
    }


def _build_cue_definitions(payload: VideoPayload) -> dict:
    """
    Produce cue_definitions.json from the generated cue list +
    fixed segment cues (always present).
    """
    segment_cues = [
        {"label": "hook_start",      "segment": "hook",         "offset_frames": 0},
        {"label": "concept_1_start", "segment": "concept_1",    "offset_frames": 0},
        {"label": "concept_2_start", "segment": "concept_2",    "offset_frames": 0},
        {"label": "takeaway_start",  "segment": "takeaway_cta", "offset_frames": 0},
    ]
    word_cues = [c.model_dump() for c in payload.cue_definitions]
    return {"segment_cues": segment_cues, "word_cues": word_cues}


def save_outputs(payload: VideoPayload, topic: dict) -> None:
    """Write all four pipeline files from a validated VideoPayload."""
    os.makedirs(os.path.join(_ROOT, "output"), exist_ok=True)

    script  = _build_script_json(payload, topic)
    spoken  = _build_spoken_narration(payload)
    params  = _build_params_json(payload)
    plan    = _build_scene_plan()
    cues    = _build_cue_definitions(payload)

    for path, data in [
        (SCRIPT_OUT, script),
        (SPOKEN_OUT, spoken),
        (PARAMS_OUT, params),
        (PLAN_OUT,   plan),
        (CUES_OUT,   cues),
    ]:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  ✓ {os.path.relpath(path, _ROOT)}")


# ══════════════════════════════════════════════════════════════════════════════
# § 5  NARRATOR.PY INTEGRATION PATCH
#     narrator.py checks for spoken_narration.json and skips LLM rewrite
#     when it exists. Add this block at the top of generate_segmented_script():
#
#       spoken_path = os.path.join(os.path.dirname(__file__), "..", "output", "spoken_narration.json")
#       if os.path.exists(spoken_path):
#           with open(spoken_path) as f:
#               print("[narrator] Using pre-generated spoken narration — skipping LLM rewrite.")
#               return json.load(f)
#
# ══════════════════════════════════════════════════════════════════════════════


def main():
    from dotenv import load_dotenv
    load_dotenv()

    # Accept topic on CLI or fall back to output/topic.json
    if len(sys.argv) > 2 and sys.argv[1] == "--topic":
        topic = {"title": " ".join(sys.argv[2:]), "summary": ""}
    else:
        if not os.path.exists(TOPIC_PATH):
            raise RuntimeError(f"topic.json not found at {TOPIC_PATH}. Run scraper + ranker first.")
        with open(TOPIC_PATH) as f:
            topic = json.load(f)

    print(f"\n[content_generator] Topic: {topic['title']}")
    print(f"[content_generator] Provider: {os.environ.get('FORCE_PROVIDER', 'claude')}\n")

    payload = generate(topic)

    print(f"\n  layout_mode : {payload.layout_mode}")
    print(f"  narration   : {len(payload.narration.hook.split())}w hook  "
          f"/ {len(payload.narration.context.split())}w context  "
          f"/ {len(payload.narration.insight.split())}w insight  "
          f"/ {len(payload.narration.takeaway.split())}w takeaway")
    total = sum(len(s.split()) for s in [
        payload.narration.hook, payload.narration.context,
        payload.narration.insight, payload.narration.takeaway,
    ])
    print(f"  total words : {total}  (budget: 130-145)")
    print(f"  cues        : {[c.label for c in payload.cue_definitions]}")
    print()

    save_outputs(payload, topic)
    print("\n✓ content_generator complete.")


if __name__ == "__main__":
    main()
