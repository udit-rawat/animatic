# adamax-content-engine

Short-form technical reel production workspace for `@ada.max24`.

The project is transitioning away from the old end-to-end automated pipeline and toward a lean HyperFrames-first reel system:

```text
reel spec -> Gemini TTS -> HyperFrames composition -> final MP4
```

The old pipeline still exists in this branch for reference, but it is no longer the direction of the project.

## Current Direction

The active production style is hand-authored HyperFrames:

- one reel concept
- one source spec
- one reusable TTS runner
- one reusable render command
- final MP4 output
- generated narration and render artifacts kept out of git

Recent finished reels live under `output/hyperframes_custom/` and serve as visual references:

- `2026-04-24_memory-wall-hf`
- `2026-04-25_spotify-blend-hf`
- `2026-04-25_iphone-portrait-hf`

The next refactor should collapse the current reel-specific scripts into one generic spec-driven workflow.

## Active Spec-Driven Workflow

The new workflow is intentionally small:

```text
reels/current/
  spec.json
  index.html

scripts/
  generate_tts.py
  render_hyperframes.py
  new_reel.py

cache/
  tts/
  renders/
  old_specs/

output/final/
  <slug>.mp4
```

The source of truth is `reels/current/spec.json`. It defines the slug, title, duration, FPS, voice, narration segments, composition directory, and output path.

Example shape:

```json
{
  "slug": "iphone-portrait",
  "title": "iPhone Portrait Mode",
  "duration": 25.2,
  "fps": 60,
  "voice": "Aoede",
  "tts_provider": "gemini",
  "composition_dir": "reels/current",
  "output_file": "output/final/iphone_portrait.mp4",
  "segments": [
    {
      "id": "hook",
      "start": 0.35,
      "duration": 3.2,
      "text": "This is why iPhone portrait mode beats Android."
    }
  ]
}
```

### Commands

Create or replace the current reel spec:

```bash
python scripts/new_reel.py --title "iPhone Portrait Mode" --slug iphone-portrait --force
```

Generate Gemini TTS from the spec:

```bash
python scripts/generate_tts.py --spec reels/current/spec.json
```

Render the current HyperFrames composition:

```bash
python scripts/render_hyperframes.py --spec reels/current/spec.json
```

Validate without external calls:

```bash
python scripts/generate_tts.py --spec reels/current/spec.json --validate-only
python scripts/render_hyperframes.py --spec reels/current/spec.json --dry-run
```

Generated audio is written next to the composition for HyperFrames to consume, but stays ignored by git. Raw TTS chunks and render workspaces go under `cache/`.

## Architecture

The active system is deliberately file-driven. The spec owns timing and outputs; the HTML owns visuals; the scripts only translate the spec into generated assets.

```text
                 tracked source
┌────────────────────────────────────────────┐
│ reels/current/spec.json                    │
│ - slug, title, duration, fps               │
│ - voice + TTS provider                     │
│ - narration segment timing                 │
│ - composition dir + final output path      │
└─────────────────────┬──────────────────────┘
                      │
                      ├── scripts/generate_tts.py
                      │   ├── reads spec.segments
                      │   ├── calls Gemini TTS
                      │   ├── writes reels/current/narration.wav
                      │   └── writes reels/current/narration_timing.json
                      │
                      └── scripts/render_hyperframes.py
                          ├── copies composition to cache/render_work/<slug>
                          ├── injects spec.duration into HyperFrames HTML
                          ├── runs HyperFrames CLI
                          └── writes output/final/<slug>.mp4
```

Responsibility boundaries:

- `spec.json` controls narration timing, render settings, and output paths.
- `index.html` controls the animation, layout, styling, and visual timeline.
- `generate_tts.py` must not know about individual reels.
- `render_hyperframes.py` must not know about individual reels.
- `cache/` is disposable and can be regenerated.
- `output/final/` contains deliverables, not source of truth.

This prevents the old failure mode where each reel created a new bespoke TTS script, a new render command, and a new output convention.

## Current Temporary State

Until the refactor lands, the repo still contains reel-specific helper scripts:

- `scripts/generate_memory_wall_hyperframes_gemini_tts.py`
- `scripts/generate_spotify_blend_hyperframes_gemini_tts.py`
- `scripts/generate_iphone_portrait_hyperframes_gemini_tts.py`

These should be treated as migration scaffolding, not the final architecture.

Use the generic scripts for all new reels. Only use the reel-specific scripts to reproduce an old reel exactly.

The minimal active shared code for TTS is:

- `pipeline/narrator.py`
- `pipeline/claude_client.py`
- `pipeline/quota.py`
- `pipeline/logger.py`
- `pipeline/video_spec.py`

## Visual System

Use `ANIMATION_PLAYBOOK.md` as the style memory for future reels.

Current high-performing direction:

- premium product-demo clarity
- object-based explanation
- strong safe-area alignment
- restrained motion
- no neon/cyberpunk defaults
- no flashy transitions
- no text-first infographic slabs unless the concept demands it

The old README image/diagram has been intentionally removed. A new architecture diagram should be added after the spec-driven workflow is implemented.

## Legacy Pipeline

The previous pipeline path was:

```text
custom topic -> content_generator -> narrator -> word_aligner
            -> brief_generator -> compositor pause -> animator -> notifier
```

That path produced many intermediate files in `output/` and depended heavily on Remotion or compositor-generated `CustomVideo.tsx` files.

It is still present for now, but should be archived after the new HyperFrames workflow is stable.

Legacy areas:

- `remotion/`
- `renderers/`
- most of `pipeline/`
- `legacy/phase1-pipeline/`
- generated files under `output/`

## Environment

See `.env.example`.

Minimum active setup:

```text
GEMINI_API_KEY or GEMINI_API_KEYS
```

Optional legacy setup:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
OPENROUTER_API_KEY
ANTHROPIC_API_KEY
```

Python dependencies:

```bash
pip install -r requirements.txt
```

HyperFrames rendering currently uses the local HyperFrames CLI.

## Git Hygiene

Generated artifacts should stay out of source control:

- TTS chunks
- rendered MP4/MOV files
- temporary narration WAV files
- cache directories
- old output JSON from previous runs

Tracked files should represent source of truth: specs, composition HTML, reusable scripts, and documentation.
