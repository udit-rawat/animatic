# adamax-content-engine

Automated daily pipeline that wakes up, finds the best ML engineering topic posted in the last 24 hours, writes a punchy 60-second explainer script, generates a narrated React/Remotion video with audio-synced animations, and delivers it to Telegram — zero manual steps.

---

## What it is

One `python run.py --gemini` call drives the entire loop:

1. **Scrape** — hits 7 ML subreddits + arXiv, collects ~21 fresh candidates
2. **Rank** — LLM scores on visual richness, engineer value, freshness, focus; picks one winner; keyword-deduplicates against 30-post history so the same story never repeats
3. **Script** — writes on-screen text: hook / 3 concept bullets / takeaway
4. **Verify** — NLI entailment pass checks every hard claim against the source summary; CONTRADICTED claims trigger a scripter rewrite (max 2 retries)
5. **Plan** — classifies each concept bullet into a layout template (pipeline / comparison / stats_grid)
6. **Extract** — LLM generates a typed `ScenePayload` JSON per beat for the Remotion renderer
7. **Narrate** — LLM rewrites visual copy into spoken segments; Gemini TTS renders each segment separately; PCM chunks are stitched into a single WAV with per-segment timecodes
8. **Align** — optional Whisper word-alignment produces frame-accurate cue triggers
9. **Render** — Remotion reads the props JSON and renders a 1080×1920 MP4; animations spring-in synced to audio cues
10. **Deliver** — Telegram receives the video + caption + token audit; topic committed to history only on confirmed delivery

**Alternatively**, `--single-shot` collapses steps 3–6 into a single Pydantic-validated LLM call via `content_generator.py`.

---

## How it works

### Pipeline modes

```
Standard (default):
  scraper → ranker → scripter → verifier → scene_planner → param_extractor
          → narrator → word_aligner → animator → notifier

Single-shot (--single-shot):
  scraper → ranker → content_generator
          → narrator → word_aligner → animator → notifier
```

`content_generator` is a single Pydantic-validated call that outputs all four files the downstream stages need (`script.json`, `spoken_narration.json`, `params.json`, `scene_plan.json`) in one shot. When `spoken_narration.json` is present, `narrator.py` skips its own LLM rewrite step and goes straight to TTS.

### Visual layer (Remotion)

The render engine lives in `remotion/src/`. Every beat maps to one of six layout components dispatched by `SceneRouter`:

| Layout | Used for |
|---|---|
| `MetricFocus` | Hero metric + supporting context + chips |
| `ComparisonSplit` | Side-by-side A vs B panels |
| `PipelineFlow` | Step-by-step process with bottleneck annotation |
| `DataGrid` | 2–4 metric cards in a CSS grid |
| `TakeawayScene` | Outro — word-reveal headline + progress border + CTA chip |
| `KineticBridge` | Gap beats — pulses 2–5 keywords sequentially, never a black screen |

The camera is an infinite canvas: all beats are stacked vertically at `y = index × 1920px`. A spring-damped camera pans between them on narration segment boundaries. Beat-local animations start from `frame 0` relative to when the camera arrives.

### Anti-dead-air

- **Sequence persistence** — if a beat has no content, `ghostContent()` walks backward and renders the nearest valid beat at `opacity: 0.22 + blur(3px)` instead of showing black
- **KineticBridge** — explicit bridge beats get pulsing keyword animation
- **Beat/timing guard** — `animator.py` warns loudly if `beats.length ≠ timing segments`, which causes the camera pan schedule to misfire

### LLM layer

All calls route through `pipeline/claude_client.py`. Provider is set by `FORCE_PROVIDER` env var or CLI flag.

| Provider | Set via | Notes |
|---|---|---|
| Gemini | `GEMINI_API_KEYS` | Up to 4 keys rotate on 429/500; daily quota tracked in `gemini_quota.json` |
| Anthropic SDK | `ANTHROPIC_API_KEY` | Good for CI/CD |
| Claude CLI | *(default)* | Runs inside a Claude Code session — no key needed |
| OpenRouter | `OPENROUTER_API_KEY` | Per-stage model routing via `OPENROUTER_MODEL_RANKER` etc. |
| Handoff | `--hop` flag | Pauses at animator, writes prompt to file, waits for manual paste |

---

## Features

- **Keyword-based topic dedup** — history matching uses per-title keyword overlap (≥2 significant words), not exact title comparison. Four TurboQuant variants in candidates → all filtered if TurboQuant is in history. Topic committed to history immediately on pick, not only after delivery.
- **NLI fact-checker** — `verifier.py` extracts 3–5 hard claims, classifies each as SUPPORTED / CONTRADICTED / UNVERIFIABLE against the source summary. CONTRADICTED injects a correction directive back into the scripter.
- **Pydantic-validated single-shot generation** — `content_generator.py` enforces 130–145 word hard budget, 18 banned phrases, 10-second rule, and layout/content agreement in one call. Anti-bloat by schema, not by instructions alone.
- **Audio-reactive animation cues** — `word_aligner.py` (Whisper) produces word-level timestamps; `animator.py` builds a `{label: frame}` cue map; Remotion components use `useCue("label")` to fire animations precisely when the word is spoken.
- **Beat/timing alignment guard** — `scene_planner.py` enforces that beat count equals concept bullet count + 2 (hook + takeaway). Prevents the camera pan schedule from misfiring and showing a dead screen before the TakeawayScene animates.
- **Dynamic video duration** — Remotion's `calculateMetadata` reads the actual audio file duration at render time. No hardcoded frame counts.
- **Gemini quota RCA** — `python run.py --rca` prints a day-level run table with per-stage call breakdown, failed-run waste, and animator retry cost.
- **Token audit** — every run outputs `output/audit.json` and prints a cost table at the end.

---

## Terminal examples

### Full pipeline runs

```bash
# Recommended daily driver — Gemini for all LLM stages + TTS
python run.py --gemini

# Single-shot mode — anti-bloat Pydantic schema replaces 4 stages
python run.py --gemini --single-shot

# Claude CLI (no keys needed — must be inside an active Claude Code session)
python run.py

# Anthropic SDK
ANTHROPIC_API_KEY=sk-... python run.py --provider anthropic

# OpenRouter with a specific model for all stages
python run.py --provider openrouter --model deepseek/deepseek-r1:free
```

### Run a single stage

```bash
# Re-scrape candidates
python run.py --stage scraper

# Re-rank from existing candidates (useful after editing picked_history.json)
python run.py --stage ranker

# Rewrite script from existing topic.json
python run.py --gemini --stage scripter

# Re-run NLI fact-checker on current script.json
python run.py --gemini --stage verifier

# Re-run single-shot generator (replaces scripter+verifier+scene_planner+param_extractor)
python run.py --gemini --stage content_generator

# Regenerate scene plan from existing script
python run.py --gemini --stage scene_planner

# Regenerate ScenePayload JSON from existing script + scene plan
python run.py --gemini --stage param_extractor

# Re-run TTS only (reads script.json → narration.wav + narration_timing.json)
python run.py --stage narrator

# Re-run Whisper word alignment (requires: pip install openai-whisper)
python run.py --stage word_aligner

# Re-render video from existing params + audio (no LLM call)
python run.py --stage animator

# Re-deliver existing video.mp4 to Telegram
python run.py --stage notifier
```

### Remotion render directly

```bash
cd remotion

# Full video using current remotion_props.json
npx remotion render src/index.ts VideoComposition ../output/video.mp4 \
  --props=../output/remotion_props.json --concurrency=4

# Gate test composition (no props file needed — uses defaultProps)
npx remotion render src/index.ts Phase2Test /tmp/gate_test.mp4 --concurrency=2

# Live preview in browser
npx remotion studio
```

### Quota and diagnostics

```bash
# Check today's Gemini quota before running
python run.py --check-quota

# Full day-level RCA — per-stage cost, failed runs, animator retry cost
python run.py --rca

# Check beat/timing alignment for current run
python -c "
import json
beats  = json.load(open('output/scene_plan.json'))['beats']
timing = json.load(open('output/narration_timing.json'))
print(f'beats: {len(beats)}  timing: {len(timing)}  match: {len(beats)==len(timing)}')
print('templates:', [b[\"template\"] for b in beats])
print('segments: ', list(timing.keys()))
"

# Print last 5 picked topics
python -c "
import json
[print(t) for t in json.load(open('output/picked_history.json'))[:5]]
"
```

---

## Setup

```bash
# 1. Clone and install Python deps
pip install -r requirements.txt

# 2. Install Remotion deps
cd remotion && npm install && cd ..

# 3. Configure env
cp .env.example .env
# Required: GEMINI_API_KEYS (or GEMINI_API_KEY), TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# Optional: OPENROUTER_API_KEY, ANTHROPIC_API_KEY, SUBREDDITS

# 4. Run
python run.py --gemini
```

For `content_generator` (single-shot mode), also install:
```bash
pip install instructor
pip install google-generativeai   # if using --gemini
pip install anthropic             # if using --provider anthropic
```

---

## Output files

```
output/
├── candidates.json         scraped topic pool (~21 candidates)
├── topic.json              selected topic + why_picked reasoning
├── script.json             hook, concept_bullets, takeaway, caption, hashtags
├── spoken_narration.json   spoken audio text per segment (written by content_generator)
├── verify_report.json      NLI fact-check audit: claims, verdicts, retry count
├── scene_plan.json         beat list with template hint per beat
├── params.json             ScenePayload JSON per beat (input to Remotion)
├── narration_timing.json   per-segment timecodes {start, end, duration, text}
├── narration.wav           stitched TTS audio (24 kHz 16-bit mono PCM)
├── word_timings.json       Whisper word-level timestamps (optional, for cues)
├── remotion_props.json     merged props passed to Remotion --props
├── video.mp4               final rendered video
├── picked_history.json     last 30 delivered topics (keyword dedup guard)
├── audit.json              token usage and cost per stage
├── gemini_quota.json       daily Gemini quota state + run-level audit log
├── animator_retries.json   animator attempt count (surfaced in Telegram message)
└── pipeline.log            full debug log
```

---

## Project structure

```
adamax-content-engine/
├── run.py                        pipeline runner + CLI entry point
├── cue_definitions.json          animation trigger map (segment + word cues)
├── pipeline/
│   ├── claude_client.py          unified LLM call layer (all providers)
│   ├── scraper.py                Reddit + arXiv fetcher
│   ├── ranker.py                 LLM topic selector + keyword dedup
│   ├── scripter.py               on-screen text writer (visual script)
│   ├── verifier.py               NLI entailment fact-checker
│   ├── scene_planner.py          beat layout classifier
│   ├── param_extractor.py        ScenePayload JSON generator per beat
│   ├── content_generator.py      single-shot replacement for the above 4 stages
│   ├── narrator.py               segmented narration rewriter + Gemini TTS stitcher
│   ├── word_aligner.py           Whisper word-level timestamp extractor
│   ├── animator.py               Remotion props assembler + render runner
│   ├── notifier.py               Telegram delivery + history commit
│   ├── auditor.py                token usage tracker
│   ├── quota.py                  Gemini daily quota tracker + RCA reporter
│   └── logger.py                 structured logging
└── remotion/
    ├── src/
    │   ├── Root.tsx               Remotion composition registry
    │   ├── VideoComposition.tsx   main beat loop + spring camera system
    │   ├── SceneRouter.tsx        layout dispatcher (6 layout components)
    │   ├── LayoutRenderer.tsx     legacy LayoutNode tree renderer (v2 fallback)
    │   ├── CameraViewport.tsx     infinite canvas + BeatZone + spring camera
    │   ├── layouts/
    │   │   ├── MetricFocus.tsx
    │   │   ├── ComparisonSplit.tsx
    │   │   ├── PipelineFlow.tsx
    │   │   ├── DataGrid.tsx
    │   │   ├── TakeawayScene.tsx
    │   │   ├── KineticBridge.tsx
    │   │   └── _shared.tsx        COLOR tokens, FONT, SectionLabelRow, useBreath
    │   ├── hooks/
    │   │   ├── useCameraY.ts      spring-damped infinite-canvas camera
    │   │   ├── useBeatFrame.ts    beat-local frame context
    │   │   ├── useCue.ts          word-cue animation trigger
    │   │   └── useAudioMetrics.ts FFT-based audio reactivity
    │   └── utils/
    │       └── springIn.ts        slideUp / scaleIn presets (CRISP / HERO)
    └── public/
        └── narration.wav          copied here by animator.py before render
```
