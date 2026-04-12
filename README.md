# adamax-content-engine

Automated daily pipeline that finds the sharpest AI/ML topic from the last 24 hours, writes a 25–35 second explainer script, generates TTS narration, and renders a fully animated 1080×1920 Reel — zero manual steps.

Built for **AdaMax**: a daily feed for indie developers, ML engineers, and technical builders.

---

## Architecture overview

```
scraper → ranker → content_generator → narrator → word_aligner
       → brief_generator → [COMPOSITOR PAUSE] → animator → notifier
```

Every stage writes to `output/` as JSON. Stages are independently resumable via `--stage`. All LLM calls route through `pipeline/claude_client.py` with token auditing.

---

## Pipeline modes

### 1. Full auto (daily driver)

Scrapes Reddit + arXiv, ranks topics by brand gravity and engineer value, generates script + layout, renders and delivers to Telegram.

```bash
python run.py --gemini
```

### 2. Custom topic (skip scraper + ranker)

Provide your own title, summary, narration, and tone. Pipeline starts at `content_generator`.

```bash
python run.py --gemini --custom \
  --title "Self-Host ChatGPT UI With Open WebUI" \
  --summary "Open WebUI runs a ChatGPT interface locally with Ollama..." \
  --tone "Calm and measured. Speak like a senior engineer." \
  --narration '{"hook":"ChatGPT. Self-hosted. Free.","concept_1":"...","concept_2":"...","takeaway_cta":"Save this. You will need the command later."}'
```

### 3. Compositor mode — bespoke animation per video

The full Path 2 pipeline. After TTS and brief generation the pipeline **pauses and prints the full animation brief inline**. You paste it into a Claude session, get a custom `CustomVideo.tsx`, drop it at the printed path, press Enter, pipeline renders.

```bash
python run.py --gemini --custom --compositor \
  --title "..." \
  --summary "..." \
  --tone "..." \
  --narration '{...}'
```

**What happens at the compositor pause:**
1. Pipeline prints the complete animation brief inline — no `cat` command needed
2. Brief includes: beat specs, exact frame offsets, narration per beat, drop path embedded
3. Paste the entire brief into Claude → get `CustomVideo.tsx`
4. Drop file at the exact path shown, press Enter → render proceeds

### 4. Single-shot mode

Replaces `scripter + verifier + scene_planner + param_extractor` with one Pydantic-validated LLM call. Faster, fewer tokens.

```bash
python run.py --gemini --single-shot
```

### 5. Resume from a stage

```bash
python run.py --gemini --custom --compositor --stage narrator --title "..."
python run.py --gemini --custom --compositor --stage brief_generator --title "..."
python run.py --gemini --custom --compositor --stage animator --title "..."
```

---

## Stage reference

| Stage | File | What it does |
|---|---|---|
| `scraper` | `scraper.py` | Hits 7 ML subreddits + arXiv, collects ~21 candidates |
| `ranker` | `ranker.py` | LLM scores on brand gravity, engineer value, freshness; deduplicates vs 30-post history |
| `content_generator` | `content_generator.py` | Single Pydantic-validated call → script + narration + layout params + scene plan |
| `narrator` | `narrator.py` | Segmented Gemini TTS with 7-key rotation; stitches PCM chunks to WAV with timecodes |
| `word_aligner` | `word_aligner.py` | Optional Whisper word-level timestamps for frame-accurate cue triggers |
| `brief_generator` | `brief_generator.py` | Reads params + timing → `animation_brief.json` + `compositor_prompt.md` + `drop_path.txt` |
| `animator` | `animator.py` | Assembles Remotion props JSON, copies narration.wav, runs `npx remotion render` |
| `notifier` | `notifier.py` | Sends `video.mp4` + caption to Telegram |

---

## Path 2: Brief Generator + Compositor

The compositor system is the core of the animation quality loop. It enforces 7 hard rules **in code** (not prompts) before a frame is ever written:

| Rule | Enforcement |
|---|---|
| Beat 1 text at frame 1 | `validate_beat()` rejects any beat with `text_frame > 1` for beat_1 |
| ≥2 animation events per beat | All spec builders inject minimum 2 events with 45–90f spacing |
| ComparisonSplit winning side pulses | `spec_comparison_split()` always adds `pulse_frames` to the right panel |
| PipelineFlow steps activate sequentially | Frame offsets from narration timing, not all at once |
| TerminalScene key command gets pulse | `pulse_line` + `pulse_frames` always set |
| TakeawayScene CTA ≤8 words | Locked to one of 4 BRIEF_V4 options; question CTAs blocked |
| No beat exceeds narration duration | `duration` field is the hard cap in frames |

### Animation brief flow

```
params.json + narration_timing.json + cue_definitions.json
        ↓
  brief_generator.py
        ↓
  animation_brief.json   — per-beat spec (template, duration, events, text_frame)
  compositor_prompt.md   — paste-ready Claude prompt with all beat specs
  drop_path.txt          — absolute path to drop CustomVideo.tsx
        ↓
  [COMPOSITOR PAUSE — full brief printed inline]
        ↓
  Paste into Claude → CustomVideo.tsx written
        ↓
  Drop at path → press Enter → animator renders
```

### Compositor role (when you paste the brief into Claude)

- **Coder, not creative director.** The brief is the creative decision.
- ONE file: `CustomVideo.tsx`, self-contained, all data hardcoded.
- Imports from `remotion`, `react`, `./layouts/` only.
- Each beat: `<Sequence from={beatStartFrame} durationInFrames={duration}>`.
- Drop path is embedded at the bottom of the brief — no separate terminal lookup needed.

---

## Visual layer — Remotion

The render engine is in `remotion/src/`. Two render paths:

### Path 1 — Template system (`VideoComposition`)

Beats map to layout templates dispatched by `SceneRouter`. Spring-damped camera pans between beats on narration boundaries.

### Path 2 — Compositor (`CustomVideo`)

Bespoke `CustomVideo.tsx` per topic, written by Claude from the animation brief. Full control over every frame. No template constraints.

### Layout templates (14 total)

| Template | Best for |
|---|---|
| `MetricFocus` | Hero stat — large number + label + context + chips |
| `DataGrid` | 2–4 metric cards in grid |
| `TriStat` | Three metrics stacked with accent bars |
| `BarComparison` | Horizontal bars, canvas-rendered with GPU glow + rounded caps + specular shimmer |
| `ComparisonSplit` | Side-by-side A vs B panels |
| `KineticBridge` | Sequential keyword pop-in — no static screen |
| `StatementSlam` | 2–3 punchy lines with spring stagger |
| `PipelineFlow` | Architecture nodes with sequential activation |
| `CodeDiff` | Before/after code blocks, per-line spring entrance |
| `TimelineFlow` | Chronological milestones with canvas-rendered neon spine |
| `LeaderboardRank` | Ranked rows, animate in reverse (winner lands last) |
| `TakeawayScene` | Outro — word-reveal headline + CTA + progress border + ambient orbs |
| `TerminalScene` | macOS terminal window — type-in, blinking cursor, pulse on key command |
| `HookR3F` | Three.js hook beat with 3D elements |

### Camera system (Path 1)

Beats stacked vertically at `y = index × 1920px`. Spring-damped camera (`useCameraY`) pans on narration boundaries. Beat-local frame context via `useBeatFrame` so animations always start at `frame 0` regardless of beat position.

### Animation primitives (`_shared.tsx`)

Phase 2 primitives — importable in any compositor-written `CustomVideo.tsx`:

```ts
usePulseAt(frame, pulseFrames, color, radius?)   // boxShadow glow string
useSlideIn(frame, direction, startFrame, distance?) // { opacity, transform }
useHighlightAt(frame, highlightFrame)              // { scale, active, opacity }
countUp(value, progress)                           // formatted count-up string
useBreath(frame, fps)                              // { scale, opacityShift } — 0.25 Hz ambient
```

Spring presets (`springIn.ts`):

```ts
SPRING_HEAVY  // damping 12, stiffness 150 — hook hero elements, visible overshoot
SPRING_MEDIUM // damping 18, stiffness 220 — concept cards, single-frame overshoot
SPRING_SOFT   // damping 28, stiffness 300 — secondary text, clean landing
```

### Canvas rendering

`BarComparison` and `TimelineFlow` use `<canvas>` elements instead of CSS divs for:
- Rounded bar caps via `ctx.roundRect()`
- GPU `shadowBlur` glow (zero CSS cost)
- Specular shimmer via `ctx.createLinearGradient()` with skew transform

### Audio reactivity

`useAudioMetrics()` provides 5-frame smoothed FFT bins:
```ts
{ rms, bassEnergy, midEnergy, highEnergy }
```
Injected as CSS custom properties `--audio-rms / --audio-bass / --audio-mid / --audio-high` at root.

### Safe area padding

All 14 templates use `paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72` to clear phone notch and bottom navigation bar.

---

## Content strategy — BRIEF_PROMPT_V4.md

**Target:** 25–35 second Reels. Word budget 50–60 total across 4 segments.

### Content formats

| Format | Hook pattern | Save trigger |
|---|---|---|
| **Format D — Repo Drop** | Famous model + "run it today" | Highest — "how to use it" content |
| **Format A — Cheat Code** | "Most devs don't know you can do X" | High — free alternative unlock |
| **Format B — Hidden Cost Reveal** | "You're paying $X/month. This does it for $0." | Very high — builder pain point |
| **Format C — Concrete Achievement** | Falsifiable claim + specific number + builder implication | High — stakes are clear |

Default to **Format D** unless the story is genuinely Format C tier. 4 repo drops for every 1 record-broken post.

### Word budgets (hard cap)

| Segment | Duration | Word limit |
|---|---|---|
| `hook` | 5–7s | ≤10 words |
| `concept_1` | 7–9s | ≤14 words |
| `concept_2` | 9–12s | ≤18 words |
| `takeaway_cta` | 5–7s | ≤8 words |
| **Total** | **25–35s** | **50–60 words** |

### Hook formula

**First 3 words must contain a number, brand name, or command.**

```
GOOD: "400B params. One H100."
GOOD: "pip install open-webui"
GOOD: "Meta just dropped."
BAD:  "Open source AI..."
```

**V4.1 visual rule: Frame 0 must have text.** Text renders before 0.3s. No intro. No logo. No fade-in on opacity.

### CTA rotation (4 options)

| Option | Pattern | Format |
|---|---|---|
| 1 — Repo CTA | `"[RepoName]. Pull it. Run it."` | D |
| 2 — Share trigger | `"Send this to the guy still paying twenty a month."` | B |
| 3 — Hard cut | End on sharpest number. No instruction. Silence = rewatch. | C |
| 4 — Save trigger | `"Save this. You will need the command later."` | D when concept_2 has install command |

### V4.1 AWT rules

- Visual change every **2–3 seconds** — no screen holds over 3s
- No question CTAs — questions kill last-3s completion
- Caption: 1 declarative sentence + runnable artifact. Zero hashtags.
- Tone: calm/measured (2 of 3 videos) or deadpan/dry (1 of 3). Never repeat tone back-to-back.

---

## Layout rotation

`output/layout_history.json` tracks the last used layout. `content_generator` injects a rotation hint into the LLM prompt to prevent consecutive duplicate layouts, which IG treats as low-effort content.

---

## TTS system

Gemini TTS with 7-key rotation. Model chain:

```
Primary:  gemini-2.5-flash-preview-tts
Fallback: gemini-2.5-pro-preview-tts
```

403 errors are **per-key**, not per-model. Rotation logic tracks `denied_keys` set and only skips a model when all keys return 403.

Voice: **Aoede** — flat, measured, performs best with calm/measured tone.

---

## Analytics + feedback loop

```bash
python run.py --log-stats    # interactive: fill views, saves, watch time for pending videos
python run.py --analytics    # print performance table + pending skeletons
```

Analytics feed back into the ranker as soft priors — layouts and topic types that performed well get a mild signal boost on the next run.

---

## Token auditing

Every Claude/Gemini call is routed through `pipeline/claude_client.py`. Cost extracted from the JSON envelope and accumulated in-process. Full audit saved to `output/audit.json` after each run.

```bash
python run.py --rca    # per-stage cost breakdown, failed runs, retry cost
```

---

## Setup

```bash
# Python deps
pip install -r requirements.txt

# Remotion deps
cd remotion && npm install && cd ..

# Env
cp .env.example .env
```

Required env vars:
```
GEMINI_API_KEYS=key1,key2,key3,...   # comma-separated, 7 recommended for rotation
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Optional:
```
SUBREDDITS=r/MachineLearning,r/LocalLLaMA   # defaults to 7 ML subreddits
CRT_ABERRATION=1                             # enable chromatic aberration (slow in Puppeteer)
OPENROUTER_API_KEY=...                       # for --provider openrouter
ANTHROPIC_API_KEY=...                        # for --provider anthropic
```

Optional — Whisper word alignment (frame-accurate animation cues):
```bash
pip install openai-whisper
```

---

## Output files

```
output/
├── candidates.json         scraped topic pool (~21 candidates)
├── topic.json              selected topic + why_picked reasoning
├── script.json             hook, concept_bullets, takeaway, caption
├── spoken_narration.json   exact spoken audio text per segment
├── verify_report.json      NLI fact-check: claims, verdicts, retry count
├── scene_plan.json         beat list with template hint per beat
├── params.json             ScenePayload JSON per beat (input to Remotion)
├── animation_brief.json    per-beat animation spec (brief_generator output)
├── compositor_prompt.md    paste-ready Claude prompt for compositor session
├── drop_path.txt           absolute path to drop CustomVideo.tsx
├── narration_timing.json   per-segment timecodes {start, end, duration}
├── narration.wav           stitched TTS audio (24 kHz 16-bit mono PCM)
├── word_timings.json       Whisper word-level timestamps (optional)
├── remotion_props.json     merged props passed to Remotion --props
├── video.mp4               final rendered video
├── analytics.json          per-video performance log
├── picked_history.json     last 30 delivered topics (dedup guard)
├── audit.json              token usage and cost per stage
├── gemini_quota.json       daily Gemini quota state
├── pipeline.log            full debug log
└── layout_history.json     last used layout (rotation guard)

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
├── BRIEF_PROMPT_V4.md            content strategy prompt — paste into Claude to get run command
├── pipeline/
│   ├── claude_client.py          unified LLM call layer (claude / gemini / openrouter / anthropic)
│   ├── scraper.py                Reddit + arXiv fetcher (no API keys)
│   ├── ranker.py                 LLM topic selector + web search grounding + analytics priors
│   ├── content_generator.py      single-shot Pydantic-validated script + layout + scene plan
│   ├── scripter.py               legacy multi-stage scripter (pre-single-shot)
│   ├── verifier.py               NLI entailment fact-checker (2-retry correction loop)
│   ├── scene_planner.py          beat → template classifier
│   ├── param_extractor.py        BeatLayout JSON generator with 3-attempt retry
│   ├── narrator.py               Gemini TTS with 7-key rotation + WAV stitching
│   ├── word_aligner.py           Whisper word-level timestamp extractor
│   ├── brief_generator.py        animation brief + compositor prompt generator (Path 2)
│   ├── animator.py               Remotion props assembler + render runner + compositor routing
│   ├── notifier.py               Telegram delivery (video + caption)
│   ├── analytics.py              performance tracker + ranker feedback loop
│   ├── auditor.py                token usage + cost tracker
│   ├── quota.py                  Gemini daily quota tracker + RCA reporter
│   └── logger.py                 structured logging
└── remotion/
    ├── src/
    │   ├── Root.tsx               composition registry
    │   ├── VideoComposition.tsx   beat loop + spring camera (Path 1)
    │   ├── SceneRouter.tsx        dispatches 14 layout templates
    │   ├── CameraViewport.tsx     infinite canvas + spring camera + CRT post-processing
    │   ├── CustomVideo.tsx        bespoke per-topic animation (Path 2, overwritten per run)
    │   ├── types.ts               SceneData union types for all 14 templates
    │   ├── layouts/
    │   │   ├── _shared.tsx        COLOR tokens, FONT, animation primitives, spring presets
    │   │   ├── MetricFocus.tsx
    │   │   ├── DataGrid.tsx
    │   │   ├── TriStat.tsx
    │   │   ├── BarComparison.tsx  canvas-rendered bars — GPU glow, rounded caps, shimmer
    │   │   ├── ComparisonSplit.tsx
    │   │   ├── KineticBridge.tsx
    │   │   ├── StatementSlam.tsx
    │   │   ├── PipelineFlow.tsx
    │   │   ├── CodeDiff.tsx
    │   │   ├── TimelineFlow.tsx   canvas-rendered spine — neon fill, sub-pixel line
    │   │   ├── LeaderboardRank.tsx
    │   │   ├── TakeawayScene.tsx
    │   │   ├── TerminalScene.tsx  macOS terminal — type-in, cursor, pulse on key command
    │   │   └── HookR3F.tsx        Three.js 3D hook beat
    │   ├── hooks/
    │   │   ├── useCameraY.ts      spring-damped camera (damping 180, stiffness 320)
    │   │   ├── useBeatFrame.ts    beat-local frame context (no Sequence time-clamping)
    │   │   ├── useCue.ts          word-cue animation trigger
    │   │   └── useAudioMetrics.ts 5-frame smoothed FFT — rms, bass, mid, high
    │   └── utils/
    │       └── springIn.ts        slideUp / scaleIn / popIn / staggerDelay + SPRING presets
    └── public/
        └── narration.wav          copied here by animator.py before render
```

---

## Diagnostics

```bash
python run.py --check-quota    # today's Gemini quota status per key
python run.py --rca            # per-stage cost, failed runs, retry cost
python run.py --analytics      # performance table + pending skeletons

# Remotion live preview
cd remotion && npx remotion studio
```
