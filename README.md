# adamax-content-engine

AdaMax video pipeline for short technical AI reels.

Current live path:

```text
custom topic -> content_generator -> narrator -> word_aligner
            -> brief_generator -> compositor pause -> animator -> notifier
```

The repo is in transition:
- current renderer: Remotion
- next renderer target: HyperFrames
- archived legacy pipeline: scraper/ranker/multi-stage generation

## Current workflow

### 1. Custom topic run

Provide title + summary, optionally override narration + tone.

```bash
python run.py --gemini --custom \
  --title "Self-Host ChatGPT UI With Open WebUI" \
  --summary "Open WebUI runs a ChatGPT-style interface locally with Ollama..." \
  --tone "Calm and measured. Speak like a senior engineer." \
  --narration '{"hook":"ChatGPT. Self-hosted. Free.","concept_1":"...","concept_2":"...","takeaway_cta":"Save this. You will need the command later."}'
```

### 2. Compositor mode

This is the main quality path today.

```bash
python run.py --gemini --custom --compositor \
  --title "..." \
  --summary "..." \
  --tone "..." \
  --narration '{...}'
```

What happens:
1. `content_generator` writes structured content outputs into `output/`
2. `narrator` shows the final spoken narration for approval, then generates TTS
3. `word_aligner` optionally adds word timestamps
4. `brief_generator` writes animation brief files and the compositor prompt
5. pipeline pauses and prints the full compositor brief inline
6. you paste that into Claude and get a bespoke `CustomVideo.tsx`
7. drop the file at the printed path, press Enter, pipeline renders
8. `notifier` can send the result to Telegram

### 3. Resume from a stage

```bash
python run.py --gemini --custom --compositor --stage narrator --title "..."
python run.py --gemini --custom --compositor --stage brief_generator --title "..."
python run.py --gemini --custom --compositor --stage animator --title "..."
```

## Active stages

| Stage | File | What it does |
|---|---|---|
| `content_generator` | `pipeline/content_generator.py` | Single structured LLM call -> script + spoken narration + scene data + cue definitions |
| `narrator` | `pipeline/narrator.py` | Gemini TTS + timing JSON |
| `word_aligner` | `pipeline/word_aligner.py` | Optional Whisper word timestamps |
| `brief_generator` | `pipeline/brief_generator.py` | Builds animation brief + compositor prompt + drop path |
| `animator` | `pipeline/animator.py` | Current Remotion render bridge |
| `notifier` | `pipeline/notifier.py` | Telegram delivery + run summary |

## Output contract today

Main generated artifacts:

- `output/topic.json`
- `output/script.json`
- `output/spoken_narration.json`
- `output/params.json`
- `output/scene_plan.json`
- `output/narration.wav`
- `output/narration_timing.json`
- `output/word_timings.json`
- `output/animation_brief.json`
- `output/compositor_prompt.md`
- `output/drop_path.txt`
- `output/video.mp4`

## Current renderer state

Remotion is still the live render layer.

Two render paths still exist:
- template render via `VideoComposition`
- bespoke render via compositor-generated `CustomVideo.tsx`

The codebase is moving away from Remotion-specific authoring toward a future
renderer-neutral spec and a HyperFrames backend, but that migration is not done
yet.

## Legacy code

Archived phase-1 legacy pipeline lives under:

- `legacy/phase1-pipeline/`

That archive contains:
- `scraper.py`
- `ranker.py`
- `scripter.py`
- `verifier.py`
- `scene_planner.py`
- `param_extractor.py`

These are no longer wired into `run.py`.

## Environment

See [.env.example](/Users/uditrawat/Desktop/experiment/adamax-content-engine/.env.example:1).

Minimum active setup:
- `GEMINI_API_KEY` or `GEMINI_API_KEYS`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Renderer prerequisites for current Remotion path:

```bash
cd remotion && npm install
```

Python deps:

```bash
pip install -r requirements.txt
```

Optional:
- `openai-whisper` for word timestamps
- OpenRouter / Anthropic keys for fallback provider modes

## Repo notes

- `BRIEF_PROMPT_V4.md` is the active prompt file
- older prompt versions were moved to `legacy/prompts/`
- docs still tied to Remotion should be treated as current-state, not future-state
