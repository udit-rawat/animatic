# Animatic

**A spec-driven engine for AI-narrated motion-graphic reels.**
One JSON spec in → one fully animated, voice-synced 1080×1920 explainer video out.

```text
spec.json ──► Gemini TTS ──────► HyperFrames / GSAP ──► MP4
             (segment-locked      (single-file HTML       (deterministic
              narration)           composition)            render + QA)
```

## Core ideas

- **The spec is the single source of truth.** One JSON file defines the narration text, per-scene timing, voice, fps and output path — and drives TTS, composition and render from end to end.
- **Narration-locked animation.** Audio is generated per scene segment and fitted to the spec's timing (never stretched more than ~8%). Every animation beat is keyed to a segment start, so visuals hit exactly when the words land.
- **Compositions are plain HTML + GSAP.** A reel is a single inspectable file — no proprietary editor, no hidden state, no `Math.random()`. The same spec renders the same video every time.
- **QA is part of the pipeline, not an afterthought.** Lint → frame snapshots → render → ffprobe + frame extraction checks. Catching layout collisions before render keeps re-renders rare and cheap.
- **Per-segment TTS caching.** Re-timing or re-rendering a reel costs zero additional API calls; only changed narration text is re-synthesized.

## Core outcomes

- 30–45 second technical explainer reels with restrained, keynote-style motion design — produced start-to-finish in a single sitting
- Instagram-safe layouts by construction (content kept inside the 72–850 × 220–1500 safe box at 1080×1920)
- Three commands from idea to deliverable: scaffold → voice → render

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env                # add your GEMINI_API_KEY(S)

python scripts/new_reel.py --title "My Reel"                            # scaffold spec + composition
python scripts/generate_tts.py --spec reels/current/spec.json          # segment-locked narration
python scripts/render_hyperframes.py --spec reels/current/spec.json    # final MP4
```

| Path | What it is |
| --- | --- |
| `reels/current/` | The active reel: `spec.json` + `index.html` composition |
| `scripts/` | Spec scaffolding, TTS generation, render entry points |
| `pipeline/` | Topic ranking, scripting, narration and delivery stages |
| `renderers/hyperframes/` | HyperFrames render bridge and helpers |
| `remotion/` | Earlier Remotion-based rendering engine (still functional) |
| `specs/` | The reel spec JSON schema |

## Project history

This repo has been through four distinct lives:

1. **Autonomous daily pipeline.** A fully hands-off loop: scrape sources → rank topics with an LLM → write a structured script → fact-check → plan scenes → render with Remotion → deliver to Telegram. Ran once a day, end to end.
2. **Generative motion engine.** Fixed video templates were replaced by a recursive `LayoutNode` JSON renderer, a virtual-canvas camera with spring physics, audio-reactive styling and CRT post-processing.
3. **Gemini-native rebuild.** Multi-key rotation, TTS voice work and quota-aware clients moved the whole stack onto free-tier Gemini.
4. **Spec-driven reels (today).** Automation kept where it pays — narration, timing, rendering, QA — and human craft kept where it matters: the story and the motion design. Less pipeline, better reels.

## See it running in the wild

Every reel this engine produces is published here:

**📹 Instagram → [instagram.com/ada.max24](https://www.instagram.com/ada.max24)**
