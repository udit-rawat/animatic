# Animatic

**A spec-driven engine for AI-narrated motion-graphic reels, authored with Claude Code.**
One JSON spec in, one voice-locked 1080×1920, 60 fps explainer reel out.

```text
spec.json ──► Gemini TTS ──► word timings ──► HTML + GSAP ──► gates + QA ──► MP4
              (one read)     (transcribe)     (hand-built)    (mechanical)   (seek-rendered)
```

## Core ideas

- **The spec is the single source of truth.** One JSON file holds the narration, duration, voice, TTS model, safe area, output path and a `gate` block that states the reel's mechanism, ending and motion vocabulary.
- **One narration read, never stretched.** The whole script goes to Gemini TTS as a single call so prosody stays continuous. If the read runs long, the script or the reel changes; the voice is never time-compressed.
- **Animation is locked to words.** `hyperframes transcribe` gives word-level timings, and every beat in the composition is keyed to the word it lands on.
- **Compositions are plain HTML + GSAP.** Each reel is one inspectable file rendered by seeking a paused timeline frame by frame, so the same spec renders the same video every time. No `Math.random()`, no wall-clock time.
- **Gates, not taste.** Mechanical checks run before a topic is pitched, before a final render, and on the draft MP4's first three seconds. A Claude Code hook refuses the final render until the motion gate passes.

## Built with Claude Code

Reels are written in Claude Code sessions. The repo ships what those sessions need:

- `.claude/settings.json` registers a PreToolUse hook (`scripts/hooks/pre_render_gate.py`) that blocks final renders on a failing motion gate.
- `scripts/reel_gate.py` holds the gates: `topic` rejects topics, lanes and openings the channel just used; `motion` rejects stock motion (scale-from-zero pops, bounce, count-ups, banned fonts) and any motion family from the last three reels; `hook` measures the first 3 s of a draft (frame-0 content, an early visual event, first-word and claim-word timing).
- Skills for HyperFrames, GSAP, motion direction and short-form hooks are installed per machine. See [docs/claude-code.md](docs/claude-code.md) for sources and the session loop.

## Quickstart

Requires Python 3.10+, Node 18+, ffmpeg and a Gemini API key.

```bash
pip install -r requirements.txt
cp .env.example .env                                            # GEMINI_API_KEYS=...

python3 scripts/new_reel.py --title "My Reel"                   # spec + blank composition
python3 scripts/reel_gate.py topic  --spec reels/current/spec_my-reel_v1.json
python3 scripts/generate_tts.py     --spec reels/current/spec_my-reel_v1.json
(cd output/hyperframes_custom/<date>_my-reel && npx hyperframes transcribe narration.wav)
# author index.html against the word timings, then:
(cd output/hyperframes_custom/<date>_my-reel && npx hyperframes lint .)
python3 scripts/render_hyperframes.py --spec reels/current/spec_my-reel_v1.json
python3 scripts/check_safe_area.py --spec reels/current/spec_my-reel_v1.json --video output/final/my-reel.mp4
```

## Layout

| Path | What it is |
| --- | --- |
| `scripts/` | Live workflow: scaffold, TTS, render, gates, safe-area check, Gemini quota check |
| `scripts/hooks/` | Claude Code hooks |
| `assets/fonts/` | Schibsted Grotesk and Martian Mono (SIL OFL), copied into each new composition |
| `docs/` | Claude Code workflow notes |
| `pipeline/` | Gemini TTS client (`narrator.py`, live) and the earlier automated pipeline stages (legacy) |
| `renderers/`, `specs/` | Template-based HyperFrames renderer and its spec schema (legacy) |
| `remotion/` | Earlier Remotion rendering engine (legacy, still functional) |
| `run.py` | Entry point of the legacy daily pipeline |

## Project history

This repo has been through five lives:

1. **Autonomous daily pipeline.** Scrape sources → rank topics with an LLM → write a script → fact-check → plan scenes → render with Remotion → deliver to Telegram, once a day, hands-off.
2. **Generative motion engine.** Fixed templates gave way to a recursive `LayoutNode` JSON renderer, a virtual camera with spring physics, audio-reactive styling and CRT post-processing.
3. **Gemini-native rebuild.** Multi-key rotation, voice work and quota-aware clients moved the stack onto free-tier Gemini.
4. **Spec-driven reels.** Automation kept where it pays (narration, timing, rendering, QA) and craft kept where it matters: the story and the motion.
5. **Gated, agent-authored reels (today).** Claude Code writes each composition from a blank file, and mechanical gates stop the channel repeating its own topics, openings and motion.

## See it running

Every reel from this engine is published at **[instagram.com/ada.max24](https://www.instagram.com/ada.max24)**.
