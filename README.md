# adamax-content-engine

Automated daily pipeline that finds the best AI/ML topic from the last 24 hours, writes a punchy 30–45 second explainer script, generates a narrated Remotion video with audio-synced animations, and delivers it to Telegram — zero manual steps.

Supports a fully custom animation path (`--compositor`) where the pipeline pauses before rendering, you approve an animation brief, and a bespoke per-topic `CustomVideo.tsx` is dropped in before render.

---

## What it does

One command drives the entire loop:

```bash
python run.py --gemini
```

1. **Scrape** — hits 7 ML subreddits + arXiv, collects ~21 fresh candidates
2. **Rank** — LLM scores on visual richness, engineer value, freshness; keyword-deduplicates against 30-post history
3. **Generate** — single Pydantic-validated LLM call outputs script, narration, layout params, scene plan in one shot (`content_generator.py`)
4. **Verify** — NLI entailment pass checks hard claims against source; CONTRADICTED claims trigger a scripter rewrite (max 2 retries)
5. **Narrate** — Gemini TTS renders each segment separately; PCM chunks stitched into WAV with per-segment timecodes
6. **Align** — optional Whisper word-alignment produces frame-accurate cue triggers
7. **Render** — Remotion reads props JSON and renders 1080×1920 MP4 with spring-synced animations
8. **Deliver** — Telegram receives video + caption + hashtags as separate messages; topic committed to history on confirmed delivery

---

## Pipeline modes

```
Standard (default):
  scraper → ranker → content_generator
          → narrator → word_aligner → animator → notifier

With compositor pause (custom animation):
  scraper → ranker → content_generator
          → [narration review pause] → narrator → word_aligner
          → [compositor pause: animation brief + file drop] → animator → notifier
```

### Custom topic (skip scraper + ranker)

```bash
python run.py --gemini --custom --title "..." --summary "..."
```

### Custom narration (bypass LLM rewrite, go straight to TTS)

```bash
python run.py --gemini --custom --narration '{"hook":"...","concept_1":"...","concept_2":"...","takeaway_cta":"..."}'
```

When `--narration` is set:
- Pipeline pauses and shows the exact script before TTS — you confirm or Ctrl+C to edit
- Word-count validation in `content_generator` is skipped (narration gets replaced anyway)

### Custom tone (replaces default voice directive)

```bash
python run.py --gemini --custom --tone "Machine-gun pace. No pauses. Numbers hit hard."
```

### Compositor (bespoke animation per video)

```bash
python run.py --gemini --custom --compositor --title "..." --narration '{...}'
```

Pipeline pauses before animator and prints full narration + frame timings per segment. You share the context with Claude to get an animation concept brief, approve it, then Claude writes `CustomVideo.tsx`. Drop the file in the printed path, press Enter, pipeline renders via `CustomVideo` composition instead of the template system.

To resume from a specific stage after a compositor pause:

```bash
python run.py --gemini --compositor --stage animator
```

---

## Visual layer (Remotion)

The render engine lives in `remotion/src/`. Every beat maps to one of 12 layout templates dispatched by `SceneRouter`:

| Template | Used for |
|---|---|
| `MetricFocus` | Single hero stat — huge number + supporting label + context + chips |
| `DataGrid` | 2–4 metric cards in a CSS grid |
| `TriStat` | Three metrics stacked with left accent bars |
| `BarComparison` | Horizontal bar chart, bars animate to width, one highlighted |
| `ComparisonSplit` | Side-by-side A vs B panels, slides in from edges |
| `KineticBridge` | 2–5 keywords pop in sequentially — never a static screen |
| `StatementSlam` | 2–3 punchy statement lines spring in with stagger |
| `PipelineFlow` | Step-by-step architecture nodes with connectors |
| `CodeDiff` | Before/after code blocks, after block springs in per-line |
| `TimelineFlow` | Chronological milestones with vertical spine |
| `LeaderboardRank` | Ranked table, rows animate in reverse (winner lands last) |
| `TakeawayScene` | Outro — floating ambient dots + word-reveal headline + CTA chip + progress border |

### Camera system

All beats are stacked vertically on an infinite canvas at `y = index × 1920px`. A spring-damped camera pans between them on narration segment boundaries. Beat-local animations always start from `frame 0` relative to when the camera arrives.

### Anti-dead-air

- **Sequence persistence** — if a beat has no content, the nearest valid beat renders at `opacity: 0.22 + blur(3px)` instead of black
- **KineticBridge** — explicit bridge beats pulse keywords continuously
- **Beat/timing guard** — `animator.py` warns if `beats.length ≠ timing segments`, which misfires the camera pan schedule

### Shared motion primitives (`_shared.tsx`, `springIn.ts`)

```
Spring presets:   CRISP (28, 220) · HERO (28, 180) · SNAP (40, 300)
Animation utils:  slideUp · scaleIn · popIn · staggerDelay
Continuous motion: useBreath (0.25 Hz, ±1.2% scale) · useAudioMetrics (FFT bass/mid/high)
```

---

## Content strategy (BRIEF_PROMPT_V3.md)

Three content formats that outperform generic AI news:

| Format | Hook pattern | Best for |
|---|---|---|
| **Cheat Code** | "Most devs don't know you can do X with Y" | Free alternatives to paid tools |
| **Hidden Cost Reveal** | "You're paying $X/month. This does the same for $0." | Open-source model releases |
| **Reframe** | "Everyone is talking about X. Nobody is saying what it means for builders." | Non-obvious implications |

Target audience: **indie developers, technical creators, builders** — not general tech curious.
Video length: **30–45 seconds hard limit** (75–86 word narration budget).

See `BRIEF_PROMPT_V3.md` for the full prompt to paste into any LLM to generate a ready-to-run command.

---

## Analytics

The pipeline auto-captures a skeleton analytics entry after every run. Fill in actual Instagram performance numbers manually:

```bash
python run.py --log-stats     # interactive: fill views, saves, watch time for pending videos
python run.py --analytics     # print performance table + pending skeletons
```

Analytics feed back into the ranker as soft priors — layouts and topic types that performed well get a mild signal boost.

---

## Terminal examples

### Full pipeline

```bash
# Daily driver — Gemini for all stages
python run.py --gemini

# Custom topic, custom narration, compositor pause for bespoke animation
python run.py --gemini --custom --compositor \
  --title "Google Just Killed Your AI API Bill" \
  --summary "Gemma 4 released, 27B params, Apache 2.0, runs locally, matches GPT-4o" \
  --tone "Machine-gun pace. Numbers hit like punches." \
  --narration '{"hook":"...","concept_1":"...","concept_2":"...","takeaway_cta":"..."}'
```

### Resume from a stage

```bash
python run.py --gemini --stage narrator
python run.py --gemini --compositor --stage animator
python run.py --stage notifier
```

### Quota and diagnostics

```bash
python run.py --check-quota   # today's Gemini quota status
python run.py --rca           # day-level RCA: per-stage cost, failed runs, retry cost
```

### Remotion

```bash
cd remotion
npx remotion studio                          # live preview in browser
npx remotion render src/index.ts VideoComposition ../output/video.mp4 \
  --props=../output/remotion_props.json --concurrency=4
```

---

## Setup

```bash
# 1. Python deps
pip install -r requirements.txt
pip install instructor google-generativeai   # for --gemini mode

# 2. Remotion deps
cd remotion && npm install && cd ..

# 3. Env
cp .env.example .env
# Required: GEMINI_API_KEYS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# Optional: OPENROUTER_API_KEY, ANTHROPIC_API_KEY, SUBREDDITS, CRT_ABERRATION

# 4. Run
python run.py --gemini
```

Optional — Whisper word alignment (higher-quality animation cues):
```bash
pip install openai-whisper
```

---

## Output files

```
output/
├── candidates.json         scraped topic pool (~21 candidates)
├── topic.json              selected topic + why_picked reasoning
├── script.json             hook, concept_bullets, takeaway, caption, hashtags
├── spoken_narration.json   spoken audio text per segment
├── verify_report.json      NLI fact-check: claims, verdicts, retry count
├── scene_plan.json         beat list with template hint per beat
├── params.json             ScenePayload JSON per beat (input to Remotion)
├── narration_timing.json   per-segment timecodes {start, end, duration}
├── narration.wav           stitched TTS audio (24 kHz 16-bit mono PCM)
├── word_timings.json       Whisper word-level timestamps (optional)
├── remotion_props.json     merged props passed to Remotion --props
├── video.mp4               final rendered video
├── analytics.json          per-video performance log (views, saves, watch time)
├── picked_history.json     last 30 delivered topics (dedup guard)
├── audit.json              token usage and cost per stage
├── gemini_quota.json       daily Gemini quota state + run-level log
└── pipeline.log            full debug log

output/compositions/
└── YYYY-MM-DD_slug/
    └── CustomVideo.tsx     compositor drop target for bespoke animation
```

---

## Project structure

```
adamax-content-engine/
├── run.py                        pipeline runner + CLI entry point
├── cue_definitions.json          animation trigger map (segment + word cues)
├── BRIEF_PROMPT_V3.md            LLM prompt for generating pipeline-ready commands
├── GEMINI_DESIGN_BRAINSTORM.md   full template audit for motion design research
├── pipeline/
│   ├── claude_client.py          unified LLM call layer (all providers)
│   ├── scraper.py                Reddit + arXiv fetcher
│   ├── ranker.py                 LLM topic selector + analytics priors
│   ├── content_generator.py      single-shot Pydantic-validated script + layout generator
│   ├── narrator.py               segmented narration rewriter + Gemini TTS stitcher
│   ├── word_aligner.py           Whisper word-level timestamp extractor
│   ├── animator.py               Remotion props assembler + render runner (+ compositor routing)
│   ├── notifier.py               Telegram delivery (video + caption + hashtags)
│   ├── analytics.py              performance tracker + ranker feedback loop
│   ├── auditor.py                token usage tracker
│   ├── quota.py                  Gemini daily quota tracker + RCA reporter
│   └── logger.py                 structured logging
└── remotion/
    ├── src/
    │   ├── Root.tsx               composition registry (VideoComposition + CustomVideo)
    │   ├── VideoComposition.tsx   beat loop + spring camera system
    │   ├── SceneRouter.tsx        dispatches 12 layout templates
    │   ├── CameraViewport.tsx     infinite canvas + BeatZone + spring camera
    │   ├── CustomVideo.tsx        bespoke per-topic animation scaffold
    │   ├── layouts/
    │   │   ├── MetricFocus.tsx
    │   │   ├── DataGrid.tsx
    │   │   ├── TriStat.tsx
    │   │   ├── BarComparison.tsx
    │   │   ├── ComparisonSplit.tsx
    │   │   ├── KineticBridge.tsx
    │   │   ├── StatementSlam.tsx
    │   │   ├── PipelineFlow.tsx
    │   │   ├── CodeDiff.tsx
    │   │   ├── TimelineFlow.tsx
    │   │   ├── LeaderboardRank.tsx
    │   │   ├── TakeawayScene.tsx
    │   │   └── _shared.tsx        COLOR tokens, FONT, SectionLabelRow, useBreath
    │   ├── hooks/
    │   │   ├── useCameraY.ts      spring-damped infinite-canvas camera
    │   │   ├── useBeatFrame.ts    beat-local frame context
    │   │   ├── useCue.ts          word-cue animation trigger
    │   │   └── useAudioMetrics.ts FFT-based audio reactivity
    │   └── utils/
    │       └── springIn.ts        slideUp / scaleIn / popIn + stagger utils
    └── public/
        └── narration.wav          copied here by animator.py before render
```
