"""
narrator.py — generates a segmented voiceover using Gemini TTS.

Three steps:
  1. LLM rewrites the visual script into spoken sections (one per script segment)
  2. Gemini TTS converts each section to audio → measures duration
  3. PCM segments stitched into output/narration.wav
     output/narration_timing.json saved with per-section timecodes
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
import wave

from pipeline import claude_client
from pipeline.video_spec import update_video_spec_timing

SCRIPT_PATH = os.path.join(os.path.dirname(
    __file__), "..", "output", "script.json")
TOPIC_PATH = os.path.join(os.path.dirname(
    __file__), "..", "output", "topic.json")
AUDIO_PATH = os.path.join(os.path.dirname(
    __file__), "..", "output", "narration.wav")
TIMING_PATH = os.path.join(os.path.dirname(
    __file__), "..", "output", "narration_timing.json")

# TTS model fallback chain — tried in order until one succeeds.
# Verified available via ListModels API (2026-04-09):
#   gemini-2.5-flash-preview-tts  — best quality, may need project allowlisting
#   gemini-2.5-pro-preview-tts    — fallback, also available
TTS_MODELS = [
    os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts"),
    "gemini-2.5-pro-preview-tts",
]
TTS_MODEL = TTS_MODELS[0]   # kept for backward-compat references
# Aoede = calm, precise female voice — best retention for tech content
VOICE_NAME = os.environ.get("TTS_VOICE", "Aoede")

# Directorial prompt prepended to every TTS segment.
# Gemini 2.5 TTS reads this and physically alters pacing/delivery.
# Change the style here to reshape the whole video's voice character.
_DEFAULT_VOICE_DIRECTIVE = (
    "You are a sharp, confident tech journalist who just found a story worth telling. "
    "You are not performing excitement — you are delivering a fact that genuinely surprised you, "
    "and your voice carries the quiet gravity of someone who knows what it means. "
    "The hook is the most important line. Say the brand name or the surprising number first, "
    "then let the implication land. Speak it like a headline being read aloud — "
    "punchy, clear, slightly faster than normal to hold attention. "
    "After the hook, shift to steady and precise: full flowing sentences, "
    "natural breath pauses after every number or named concept so it registers. "
    "Never perform enthusiasm. Never slow-drag the opening. "
    "The listener should feel like they caught something important before everyone else did. "
    "When you hit the takeaway, drop pace slightly — that is the line they will screenshot. "
    "Do not sound like a YouTuber, a news anchor, or a podcast host. "
    "Sound like someone who read the paper, ran the benchmark, and is telling you what it actually means. "
)


def _get_voice_directive() -> str:
    """Return custom tone if --tone was passed via env, otherwise the default."""
    override = os.environ.get("NARRATOR_TONE_OVERRIDE", "").strip()
    if override:
        return override + " "
    return _DEFAULT_VOICE_DIRECTIVE


VOICE_DIRECTIVE = _DEFAULT_VOICE_DIRECTIVE  # kept for backward compat imports


# ── Step 1: LLM rewrites visual script → segmented narration ─────────────────

def build_narration_prompt(topic: dict, script: dict) -> str:
    n = len(script["concept_bullets"])
    bullets = "\n".join(
        f"  bullet_{i+1}: {b}" for i, b in enumerate(script["concept_bullets"])
    )
    concept_keys = ", ".join(f'"concept_{i+1}"' for i in range(n))
    return f"""\
You are writing a segmented voiceover for a 25–35 second AI short-form reel (Instagram/TikTok/Shorts).
Target topics: GitHub repos and AI tools people can run TODAY, model releases with dramatic claims.
The goal: stop the scroll in 2 seconds, deliver the key fact, trigger a save.

TOPIC: {topic['title']}

SOURCE MATERIAL:
  hook:          {script['hook']}
  concepts:
{bullets}
  takeaway:      {script['takeaway']}

TOTAL TARGET: 25–35 seconds spoken. Every section must be tight. Cut every word that does not earn its place.

Write spoken narration in this structure:

  "hook" (4–6 seconds — ≤20 words spoken):
    First word or two: the brand name, repo name, or surprising number.
    One punchy sentence. That is it. No preamble. No "today we look at."
    Create the "wait, what?" moment in under 3 seconds.
    GOOD: "Someone just built a local GPT-4 replacement using Llama 4. It's free."
    GOOD: "Google's AlphaEvolve just broke a 56-year-old math record — by rewriting its own code."
    GOOD: "119 billion parameters. Only 6 billion activate per token. That's Mistral Small 4."
    BAD:  "Your GPU had plenty of memory. Your RAM had plenty of memory. So why did the process die?" ← no brand, no drama
    BAD:  "Today we examine memory allocation patterns in PyTorch training pipelines." ← news anchor opener

  {concept_keys} (6–9 seconds each — ≤35 words per concept):
    Start mid-thought — no "so", no "now", no preamble.
    For REPO topics: concept_1 = what it does + model it's built on.
                     concept_2 = the install or run command read aloud naturally.
                     concept_3 = what you can build or automate with it today.
    For MODEL topics: mechanism first, then the number, then the implication.
    Mix short punchy sentences (3-5 words) with one medium sentence for rhythm.
    GOOD: "AgentKit wraps Llama 4 into a one-command local agent. pip install, point it at a folder, it starts reasoning."
    GOOD: "Two environment variables. That's it. Set MALLOC_ARENA_MAX to 2 — RSS drops without touching model code."
    BAD:  "The mechanism involves setting environment variables that control memory allocation behavior."

  "takeaway_cta" (5–8 seconds — ≤25 words spoken):
    For REPO topics: repo name + "Pull it. Run it." + one-line what changes for the viewer.
    For MODEL topics: the specific rule or number the viewer will act on or save.
    Actionable line first. Save-trigger quality. No questions alone.
    GOOD: "It's on GitHub — search AgentKit. Pull it. Run it. No API key, no subscription, just your machine."
    GOOD: "Set MALLOC_ARENA_MAX=2 before any PyTorch job. One env var. Forty percent RSS drop."
    BAD:  "In conclusion, these optimizations can significantly improve your training pipeline."
    BAD:  "What else are you not measuring?" (question alone — no anchor)

RULES — non-negotiable:
- Write for speaking, not reading. Use natural rhythm and breath pauses.
- No hedging: "basically", "kind of", "essentially", "in a sense" — cut them all.
- NEVER say "video", "animation", "screen", "visual", "watch", "see", "subscribe", "follow".
- No news-anchor phrasing: "Today we look at...", "In this segment...", "As we can see..."
- Use contractions naturally: "it's", "that's", "you're", "doesn't"
- Each section must stand alone — it will be spliced independently
- BANNED adjectives — use the actual number instead: "incredibly", "massive", "huge",
  "enormous", "groundbreaking", "revolutionary", "mind-blowing", "next level", "powerful"
- BANNED phrases: "This changes everything", "game changer", "at its core", "simply put"
- Hook: stop-scroll in 3 seconds. Lead with the famous brand OR the surprising number OR the dramatic event.
  Three patterns — use the one that fits the topic:
  Famous brand + reversal:  "OpenAI's Sora lasted six months. The unit economics killed it."
  Surprising number first:  "119 billion parameters. Only 6 billion activate per token. That's Mistral Small 4."
  Dramatic event + context: "Google's AlphaEvolve just broke a 56-year-old math record — by rewriting its own code."
  BAD: "Every 1-bit LLM kept embeddings at 16-bit." ← no brand, too niche, no drama
  BAD: "Run your own ChatGPT on your iPhone." ← command/feature pitch, no surprise
  BAD: "Today we look at Bonsai 8B..." ← news-anchor opener

Return ONLY valid JSON with EXACTLY these keys:
  "hook", {concept_keys}, "takeaway_cta"
No markdown, no extra text.
"""


def generate_segmented_script(topic: dict, script: dict) -> dict:
    # content_generator.py writes spoken_narration.json with the exact segment
    # keys narrator needs for TTS. Only use it if the key set matches what the
    # current script requires — stale files from a different pipeline mode or a
    # different bullet count would cause a beat/timing mismatch downstream.
    _spoken_path = os.path.join(os.path.dirname(
        __file__), "..", "output", "spoken_narration.json")
    if os.path.exists(_spoken_path):
        with open(_spoken_path) as _f:
            _spoken = json.load(_f)
        n_bullets = len(script.get("concept_bullets", []))
        _expected_keys = set(
            ["hook"] +
            [f"concept_{i+1}" for i in range(n_bullets)] + ["takeaway_cta"]
        )
        if set(_spoken.keys()) == _expected_keys:
            print(
                "[narrator] spoken_narration.json matches script — skipping LLM rewrite step.")
            return _spoken
        else:
            print(
                f"[narrator] spoken_narration.json key mismatch "
                f"(have {sorted(_spoken.keys())}, need {sorted(_expected_keys)}) "
                f"— falling through to LLM rewrite."
            )

    import re as _re
    prompt = build_narration_prompt(topic, script)
    last_err = None
    for attempt in range(1, 4):
        try:
            raw = claude_client.call(
                prompt, stage="narrator", json_mode=True).strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            # Find first { ... } block and repair trailing commas
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                raw = raw[start:end]
            raw = _re.sub(r',\s*([\]}])', r'\1', raw)
            return json.loads(raw)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_err = e
            print(
                f"[narrator] JSON parse failed (attempt {attempt}/3): {e} — retrying...")
    raise RuntimeError(
        f"Narrator failed to produce valid JSON after 3 attempts. Last error: {last_err}")


# ── Step 2: Gemini TTS ────────────────────────────────────────────────────────

class _TTSRateLimited(Exception):
    pass


class _TTSModelDenied(Exception):
    """403 PERMISSION_DENIED — this model requires project allowlisting. Try next model."""
    pass


def call_tts(text: str, api_key: str, model: str | None = None) -> bytes:
    """Single TTS call — raises _TTSRateLimited on 429/5xx, _TTSModelDenied on 403."""
    tts_model = model or TTS_MODEL
    # TTS models do not support system_instruction (500) or prepended directives (400).
    # Voice delivery is shaped via the voiceName selection only — Aoede is calm + precise.
    payload = json.dumps({
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": VOICE_NAME}
                }
            },
        },
    }).encode()

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{tts_model}:generateContent?key={api_key}"
    )
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Project-level block — this model needs allowlisting. Try next model.
            print(f" [403 denied: {tts_model}]", end="", flush=True)
            raise _TTSModelDenied() from e
        if e.code in (429, 500, 503):
            # Rate limit or transient error — rotate to next key
            raise _TTSRateLimited() from e
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini TTS HTTP {e.code}: {body[:400]}") from e
    except (TimeoutError, OSError) as e:
        raise _TTSRateLimited() from e   # treat timeout as RPM — rotate to next key

    candidate = data.get("candidates", [{}])[0]
    if "content" not in candidate:
        finish_reason = candidate.get("finishReason", "UNKNOWN")
        print(
            f" [no content: finishReason={finish_reason}]", end="", flush=True)
        raise _TTSRateLimited()
    audio_b64 = candidate["content"]["parts"][0]["inlineData"]["data"]
    try:
        from pipeline import quota as _q
        _q.record_call("narrator")
    except Exception:
        pass
    return base64.b64decode(audio_b64)


def pcm_duration(pcm_data: bytes, sample_rate: int = 24000) -> float:
    return len(pcm_data) / (sample_rate * 2)  # 16-bit PCM = 2 bytes/sample


def save_wav(pcm_data: bytes, path: str, sample_rate: int = 24000):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


# ── Main ──────────────────────────────────────────────────────────────────────

def _get_tts_keys() -> list[str]:
    """Return all available Gemini API keys for TTS rotation."""
    multi = os.environ.get("GEMINI_API_KEYS", "")
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]
    single = os.environ.get("GEMINI_API_KEY", "")
    return [single] if single else []


def call_tts_with_rotation(text: str, keys: list[str]) -> bytes:
    """
    Rotate through keys on 429/5xx or 403.
    403 is per-key project allowlisting — try remaining keys before giving up on model.
    Only skip to next model if EVERY key returns 403 for that model.
    """
    max_full_cycles = 5
    cycle_wait = 60

    for model_idx, model in enumerate(TTS_MODELS):
        denied_keys: set[int] = set()
        for cycle in range(max_full_cycles):
            for i, key in enumerate(keys):
                try:
                    result = call_tts(text, key, model=model)
                    if model_idx > 0:
                        print(f" [using {model}]", end="", flush=True)
                    return result
                except _TTSModelDenied:
                    denied_keys.add(i)
                    # 403 is per-key — keep trying remaining keys
                    if len(denied_keys) == len(keys):
                        # Every key denied — model is fully blocked, skip it
                        if model_idx < len(TTS_MODELS) - 1:
                            print(f" [all keys denied for {model} → trying {TTS_MODELS[model_idx + 1]}]", flush=True)
                        break
                    if i < len(keys) - 1:
                        print(f" [key {i+1} 403 → key {i+2}]", end="", flush=True)
                except _TTSRateLimited:
                    if i < len(keys) - 1:
                        print(f" [key {i+1} → key {i+2}]", end="", flush=True)

            if len(denied_keys) == len(keys):
                break  # move to next model

            print(
                f" [all {len(keys)} keys failed — waiting {cycle_wait}s (cycle {cycle+1}/{max_full_cycles})]", flush=True)
            time.sleep(cycle_wait)

        if len(denied_keys) < len(keys):
            # Not all keys were denied — we exhausted rate-limit cycles
            raise RuntimeError(
                f"TTS failed after {max_full_cycles} full key rotation cycles on model {model}.")

    raise RuntimeError(
        f"TTS failed: all models in fallback chain denied or exhausted. Models tried: {TTS_MODELS}")


def main():
    keys = _get_tts_keys()
    if not keys:
        raise RuntimeError(
            "GEMINI_API_KEY or GEMINI_API_KEYS not set — narrator requires Gemini TTS.")

    with open(SCRIPT_PATH) as f:
        script = json.load(f)
    with open(TOPIC_PATH) as f:
        topic = json.load(f)

    # Step 1 — generate segmented narration via LLM
    print("Generating segmented narration script...")
    segments = generate_segmented_script(topic, script)

    n_bullets = len(script["concept_bullets"])
    segment_keys = ["hook"] + \
        [f"concept_{i+1}" for i in range(n_bullets)] + ["takeaway_cta"]

    # Step 2 — TTS each segment with key rotation, measure duration, stitch PCM
    print(
        f"Calling Gemini TTS  model={TTS_MODEL}  voice={VOICE_NAME}  keys={len(keys)}...")
    timing = {}
    all_pcm = b""
    cursor = 0.0

    for key in segment_keys:
        text = segments.get(key, "").strip()
        if not text:
            print(f"  [WARN] Missing segment '{key}' — skipping")
            continue
        word_count = len(text.split())
        print(f"  {key} ({word_count} words)...", end="", flush=True)
        pcm = call_tts_with_rotation(text, keys)
        dur = pcm_duration(pcm)
        timing[key] = {
            "start":    round(cursor, 3),
            "duration": round(dur, 3),
            "end":      round(cursor + dur, 3),
            "text":     text,
        }
        all_pcm += pcm
        cursor += dur
        print(f" {dur:.1f}s")

    # Step 3 — save stitched audio
    os.makedirs(os.path.dirname(AUDIO_PATH), exist_ok=True)
    save_wav(all_pcm, AUDIO_PATH)

    # Step 4 — save timing for animator
    with open(TIMING_PATH, "w") as f:
        json.dump(timing, f, indent=2)

    updated = update_video_spec_timing(timing, audio_src="narration.wav")
    if updated:
        print("✓ video_spec.json refreshed with exact timing")

    total = cursor
    print(f"✓ Narration saved → {AUDIO_PATH}  ({total:.1f}s total)")
    print(f"✓ Timing saved   → {TIMING_PATH}")
    return AUDIO_PATH


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
