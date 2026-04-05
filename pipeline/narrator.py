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

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TOPIC_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
AUDIO_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "narration.wav")
TIMING_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "narration_timing.json")

TTS_MODEL  = "gemini-2.5-flash-preview-tts"
VOICE_NAME = os.environ.get("TTS_VOICE", "Aoede")  # Aoede = calm, precise female voice — best retention for tech content

# Directorial prompt prepended to every TTS segment.
# Gemini 2.5 TTS reads this and physically alters pacing/delivery.
# Change the style here to reshape the whole video's voice character.
_DEFAULT_VOICE_DIRECTIVE = (
    "You are a senior ML engineer explaining something important to a colleague over coffee. "
    "You already know this is significant — you do not need to perform excitement. "
    "Speak with calm confidence. Let the facts carry the weight, not your tone. "
    "Speak in full, flowing sentences — never staccato fragments. "
    "Pause briefly after every number or technical term so it registers. "
    "When you hit the takeaway, slow down slightly — that is the line they will remember. "
    "Do not sound like a YouTuber, a news anchor, or a podcast host. "
    "Sound like the smartest person in the room who does not need to prove it. "
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
You are writing a segmented voiceover for a short-form AI explainer (TikTok/Shorts style).
The goal is curiosity — make the viewer lean in, not tune out.

TOPIC: {topic['title']}

SOURCE MATERIAL:
  hook:          {script['hook']}
  concepts:
{bullets}
  takeaway:      {script['takeaway']}

Write spoken narration in this structure:

  "hook" (8-12 seconds):
    Open with the unexpected fact or contradiction — something that creates a "wait, what?" moment.
    Pose the question implicitly before you answer it. Use "you" to make it personal.
    GOOD: "Your GPU had plenty of memory. Your RAM had plenty of memory. So why did the process die?"
    BAD:  "Today we examine memory allocation patterns in PyTorch training pipelines."

  {concept_keys} (12-18 seconds each):
    Start mid-thought — no "so", no "now", no preamble.
    Name the mechanism directly, then give the concrete number or fact.
    Mix short punchy sentences (4-6 words) with one medium sentence for rhythm.
    End with the implication — "which means", "so now", "and that changes everything."
    GOOD: "Two environment variables. That's it. MALLOC_ARENA_MAX caps how many memory arenas glibc spins up. Set it to 2, and your RSS drops — without touching a single line of model code."
    BAD:  "The mechanism involves setting environment variables that control memory allocation behavior."

  "takeaway_cta" (10-16 seconds):
    First sentence: the save-trigger — a specific rule, flag, number, or decision the
    engineer can act on or reference next week. Make it cheat-sheet quality.
    Second sentence (optional): a provocation that extends the thought.
    The actionable line ALWAYS comes first. Never end on a question alone.
    GOOD: "Set MALLOC_ARENA_MAX=2 before any PyTorch job. One env var, forty percent RSS drop. The question is what else your allocator is hiding."
    GOOD: "Use evolutionary search when your objective is exact and cheap to evaluate. Matrix ops, compilers, schedulers — all qualify."
    BAD:  "In conclusion, these optimizations can significantly improve your training pipeline performance."
    BAD:  "What else are you not measuring?" (question alone — no actionable anchor)

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
- Hook: stop-scroll in 3 seconds. No explanation, no setup. Two patterns:
  Mechanism topics → broken assumption first: "Every 1-bit LLM kept embeddings at 16-bit. Bonsai closes it. 1.15 GB."
  Capability topics → desire + proof number: "Private ChatGPT. Your iPhone. No internet. 1.15 GB. 44 tokens per second."
  BAD: "Run your own ChatGPT on your iPhone." (command/feature pitch — no number, no surprise)
  BAD: "Today we look at Bonsai 8B..." (news-anchor opener)

Return ONLY valid JSON with EXACTLY these keys:
  "hook", {concept_keys}, "takeaway_cta"
No markdown, no extra text.
"""


def generate_segmented_script(topic: dict, script: dict) -> dict:
    # content_generator.py writes spoken_narration.json with the exact segment
    # keys narrator needs for TTS. Only use it if the key set matches what the
    # current script requires — stale files from a different pipeline mode or a
    # different bullet count would cause a beat/timing mismatch downstream.
    _spoken_path = os.path.join(os.path.dirname(__file__), "..", "output", "spoken_narration.json")
    if os.path.exists(_spoken_path):
        with open(_spoken_path) as _f:
            _spoken = json.load(_f)
        n_bullets = len(script.get("concept_bullets", []))
        _expected_keys = set(
            ["hook"] + [f"concept_{i+1}" for i in range(n_bullets)] + ["takeaway_cta"]
        )
        if set(_spoken.keys()) == _expected_keys:
            print("[narrator] spoken_narration.json matches script — skipping LLM rewrite step.")
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
            raw = claude_client.call(prompt, stage="narrator", json_mode=True).strip()
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
            print(f"[narrator] JSON parse failed (attempt {attempt}/3): {e} — retrying...")
    raise RuntimeError(f"Narrator failed to produce valid JSON after 3 attempts. Last error: {last_err}")


# ── Step 2: Gemini TTS ────────────────────────────────────────────────────────

class _TTSRateLimited(Exception):
    pass


def call_tts(text: str, api_key: str) -> bytes:
    """Single TTS call — raises _TTSRateLimited on 429 so caller can rotate keys."""
    # Prepend directorial cue so the model shapes delivery, not just reads words.
    directed_text = _get_voice_directive() + text
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

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{TTS_MODEL}:generateContent?key={api_key}"
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
        if e.code in (429, 500, 503):
            # 429 = rate limit, 500/503 = transient server error — rotate to next key
            raise _TTSRateLimited() from e
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini TTS HTTP {e.code}: {body[:400]}") from e
    except (TimeoutError, OSError) as e:
        raise _TTSRateLimited() from e   # treat timeout as RPM — rotate to next key

    candidate = data.get("candidates", [{}])[0]
    if "content" not in candidate:
        finish_reason = candidate.get("finishReason", "UNKNOWN")
        # RECITATION / transient server hiccup → rotate key and retry
        # SAFETY → also rotate (different key may succeed; TTS safety is rare for factual text)
        print(f" [no content: finishReason={finish_reason}]", end="", flush=True)
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
    """Rotate through all keys on 429/500/503/timeout. Wait 60s only after all keys fail a full cycle."""
    max_full_cycles = 5
    cycle_wait = 60
    for cycle in range(max_full_cycles):
        for i, key in enumerate(keys):
            try:
                return call_tts(text, key)
            except _TTSRateLimited:
                if i < len(keys) - 1:
                    print(f" [key {i+1} → key {i+2}]", end="", flush=True)
                # last key handled by outer cycle wait below
        print(f" [all {len(keys)} keys failed — waiting {cycle_wait}s (cycle {cycle+1}/{max_full_cycles})]", flush=True)
        time.sleep(cycle_wait)
    raise RuntimeError(f"TTS failed after {max_full_cycles} full key rotation cycles.")


def main():
    keys = _get_tts_keys()
    if not keys:
        raise RuntimeError("GEMINI_API_KEY or GEMINI_API_KEYS not set — narrator requires Gemini TTS.")

    with open(SCRIPT_PATH) as f:
        script = json.load(f)
    with open(TOPIC_PATH) as f:
        topic = json.load(f)

    # Step 1 — generate segmented narration via LLM
    print("Generating segmented narration script...")
    segments = generate_segmented_script(topic, script)

    n_bullets = len(script["concept_bullets"])
    segment_keys = ["hook"] + [f"concept_{i+1}" for i in range(n_bullets)] + ["takeaway_cta"]

    # Step 2 — TTS each segment with key rotation, measure duration, stitch PCM
    print(f"Calling Gemini TTS  model={TTS_MODEL}  voice={VOICE_NAME}  keys={len(keys)}...")
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

    total = cursor
    print(f"✓ Narration saved → {AUDIO_PATH}  ({total:.1f}s total)")
    print(f"✓ Timing saved   → {TIMING_PATH}")
    return AUDIO_PATH


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
