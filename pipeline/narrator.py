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
You are writing a segmented 60-second voiceover for an AI engineering explainer video.
The narration is split into sections that will be time-synced to animation segments.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}

VIDEO SCRIPT:
  hook: {script['hook']}
  concept bullets:
{bullets}
  takeaway: {script['takeaway']}
  cta: {script['cta']}

Return a JSON object with EXACTLY these keys:
  "hook"          — 1-2 sentences for the opening hook (~5 seconds spoken)
  {concept_keys}  — one narration section per concept bullet (~8-12 seconds each)
  "takeaway_cta"  — closing takeaway + call to action, ending with "Follow for daily AI breakdowns." (~10 seconds)

Rules for every section:
- Explains the ACTUAL CONCEPT to the listener — what it is, why it matters, how it works
- Sounds like a knowledgeable engineer speaking directly
- NEVER mentions "video", "animation", "visual", "screen", "scene", "show", or "transition"
- Direct technical language — no filler, no hype
- Flows naturally when read aloud in isolation

Return ONLY valid JSON. No markdown fences, no extra text.
"""


def generate_segmented_script(topic: dict, script: dict) -> dict:
    prompt = build_narration_prompt(topic, script)
    raw = claude_client.call(prompt, stage="narrator").strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


# ── Step 2: Gemini TTS ────────────────────────────────────────────────────────

def call_tts(text: str, api_key: str) -> bytes:
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

    for attempt, wait in enumerate([30, 60, 120, None], start=1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and wait is not None:
                print(f"  ⏳ TTS rate limited — waiting {wait}s (attempt {attempt})...")
                time.sleep(wait)
            else:
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

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set — narrator requires Gemini TTS.")

    with open(SCRIPT_PATH) as f:
        script = json.load(f)
    with open(TOPIC_PATH) as f:
        topic = json.load(f)

    # Step 1 — generate segmented narration via LLM
    print("Generating segmented narration script...")
    segments = generate_segmented_script(topic, script)

    n_bullets = len(script["concept_bullets"])
    segment_keys = ["hook"] + [f"concept_{i+1}" for i in range(n_bullets)] + ["takeaway_cta"]

    # Step 2 — TTS each segment, measure duration, stitch PCM
    print(f"Calling Gemini TTS  model={TTS_MODEL}  voice={VOICE_NAME}...")
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
        pcm = call_tts(text, api_key)
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
