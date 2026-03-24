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
VOICE_NAME = "Kore"   # firm, clear — good for technical explainers


# ── Step 1: LLM rewrites visual script → segmented narration ─────────────────

def build_narration_prompt(topic: dict, script: dict) -> str:
    n = len(script["concept_bullets"])
    bullets = "\n".join(
        f"  bullet_{i+1}: {b}" for i, b in enumerate(script["concept_bullets"])
    )
    concept_keys = ", ".join(f'"concept_{i+1}"' for i in range(n))
    return f"""\
You are writing a segmented 60-second voiceover for an AI engineering dopamine-loop video.
Cold, precise, system-terminal register. No warmth. No filler. Every word is load-bearing.

TOPIC: {topic['title']}

VIDEO BEATS:
  hook (Beat 1 — The Anomaly):    {script['hook']}
  concept bullets:
{bullets}
  takeaway (Beat 4 — Hook Loop):  {script['takeaway']}
  cta:                            {script.get('cta', 'Follow for daily AI breakdowns.')}

Return a JSON object with EXACTLY these keys:
  "hook"          — 2-3 sentences, ~10 seconds spoken. Break expectation. Cold open.
  {concept_keys}  — 2-3 sentences each, ~15 seconds spoken. Mechanism or contrast. Dense with facts.
  "takeaway_cta"  — 2-3 sentences, ~15 seconds. End on an unanswered question or a sharp provocation. No CTAs, no "follow" lines.

Rules:
- Each section must stand alone — it will be spliced independently
- NEVER mention "video", "animation", "visual", "screen", "scene", "show", "transition"
- No hedging ("kind of", "basically", "essentially") — state facts
- Write as if narrating a system log, not a YouTube explainer

Return ONLY valid JSON. No markdown, no extra text.
"""


def generate_segmented_script(topic: dict, script: dict) -> dict:
    prompt = build_narration_prompt(topic, script)
    raw = claude_client.call(prompt, stage="narrator", json_mode=True).strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


# ── Step 2: Gemini TTS ────────────────────────────────────────────────────────

class _TTSRateLimited(Exception):
    pass


def call_tts(text: str, api_key: str) -> bytes:
    """Single TTS call — raises _TTSRateLimited on 429 so caller can rotate keys."""
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
        f"{TTS_MODEL}:generateContent?key={api_key}"
    )
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise _TTSRateLimited() from e
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini TTS HTTP {e.code}: {body[:400]}") from e

    audio_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
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
    """Rotate through all keys on 429 — no waiting until all keys exhausted."""
    for i, key in enumerate(keys):
        try:
            return call_tts(text, key)
        except _TTSRateLimited:
            if i < len(keys) - 1:
                print(f" [key {i+1} RPM limit → key {i+2}]", end="", flush=True)
                continue
            # All keys exhausted — wait and retry from first key
            print(f" [all {len(keys)} keys RPM-limited — waiting 30s]", flush=True)
            time.sleep(30)
            return call_tts_with_rotation(text, keys)


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
