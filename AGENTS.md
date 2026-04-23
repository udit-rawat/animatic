# adamax-content-engine — Codex Project Context

## Git Rules (no exceptions)
- Never add co-author lines to commits. All commits are authored solely by the repo owner.
- Never run `git commit` without showing the proposed one-line message first and receiving explicit approval.
- Never run `git push` without approval in the same message exchange.
- "push it" or "go ahead" approves that single operation only — not future ones.
- Before any git operation (commit, push, tag), state what you are about to do and wait.

## Project Summary
Automated daily AI short-form video pipeline. Runs once per day, end-to-end:

1. **scraper** — Fetches top posts from configured subreddits + arXiv papers (no API keys, public endpoints only)
2. **ranker** — Codex picks the single best topic for a 60-second short-form explainer
3. **scripter** — Codex writes a structured script: hook / concept bullets / takeaway / CTA + caption + hashtags
4. **fact_checker** — NLI entailment pass between scripter and scene_planner (2-retry correction loop)
5. **scene_planner** — Classifies each beat into a template hint (hook / stats_grid / pipeline / comparison / timeline / takeaway)
6. **param_extractor** — Codex generates a `BeatLayout` JSON tree (LayoutNode schema) for each beat
7. **narrator** — TTS narration via ElevenLabs/Gemini rotation with timing alignment
8. **animator** — Remotion render bridge: assembles props JSON, invokes `npx remotion render`
9. **notifier** — Sends final video + caption to Telegram

## Rendering Engine — Motion Design v2
Branch `feature/motion-design-v2`. Archived architecture doc now lives at `legacy/docs/MOTION_DESIGN_V2_TDD.md`.

### Pillar 1 — Generative Component Engine
- `LayoutNode` schema: self-describing JSON trees replace all fixed templates
- `LayoutRenderer.tsx`: single recursive component dispatches to 10 primitive nodes
  (`column`, `row`, `grid`, `TerminalPrompt`, `TerminalText`, `StatBox`, `LabelValueCard`, `CodeBlock`, `Chip`, `Divider`, `Spacer`)
- `param_extractor.py` outputs `BeatLayout` JSON; `_validate_beat_layout()` with 3-attempt retry + Option-A static fallback
- Old `BeatRouter` and 6 fixed beat files deleted

### Pillar 2 — Infinite Canvas & Camera
- `VirtualCanvas`: 1080 × (n_beats × 1920) absolute canvas — all beats rendered simultaneously
- `useCameraY()`: spring pans between beats (damping 180, stiffness 320), Ken Burns 0→8px drift, velocity output
- `BeatFrameContext` / `useBeatFrame()`: beat-local frame offsets without `<Sequence>` time-clamping
- `CameraViewport`: overflow-hidden viewport, applies `translateY(-cameraY)`

### Pillar 3 — Audio Reactivity
- `useAudioMetrics()`: 5-frame smoothing window over 256 FFT bins → `rms`, `bassEnergy`, `midEnergy`, `highEnergy`
- CSS custom properties `--audio-rms / --audio-bass / --audio-mid / --audio-high` injected at root
- `TerminalText` neon glow: `calc(var(--audio-rms) * 40px + 8px)`
- `LabelValueCard` border pulse: `calc(var(--audio-bass) * 30px + 12px)`
- `MatrixBackground`: deterministic falling katakana/ASCII columns (sin-seeded, no `Math.random()`)

### Pillar 4 — CRT Post-Processing
- `CRTWrapper`: 4-layer effect stack wrapping `CameraViewport`
  - z=100 Scanlines (always, zero GPU cost)
  - z=101 Vignette (always)
  - z=102 Chromatic aberration (gated: `|cameraVelocity| > 15` AND `CRT_ABERRATION=1` env var)
  - z=103 Screen grain (gated: `highEnergy > 0.1`, 64×64 deterministic sin/cos tile)

### Output contract
- `output/params.json` — BeatLayout JSON (new format, replaces flat template fields)
- `output/remotion_props.json` — merged props passed to Remotion via `--props`
- `output/video.mp4` — final deliverable (unchanged path)

## Model & Quality
- Always use `Codex-sonnet-4-6` (latest Sonnet series)
- All Codex calls must use `max_tokens=8096` minimum
- Never downgrade model or reduce token budget to save cost

## Architecture Decisions
- All LLM calls use `Codex -p --output-format json --model Codex-sonnet-4-6` via subprocess
- No Anthropic API key needed — authentication is handled by the active Codex session
- Run the pipeline from within a Codex session: `! python run.py`
- Subreddits are env-configurable via `SUBREDDITS` in `.env`
- Output paths are hardcoded: `output/` for data, `remotion/` for the rendering engine
- Only `output/script.json` and `output/video.mp4` are the "final" deliverables; intermediate JSONs kept for debugging
- `CRT_ABERRATION=1` env var enables chromatic aberration in renders (disabled by default — slow in Puppeteer)

## Token Auditing
- Every Codex CLI call is routed through `pipeline/claude_client.py`
- Cost is extracted from the JSON envelope (`cost_usd` field) returned by `--output-format json`
- Usage is accumulated in-process and printed at end of full pipeline run
- Audit saved to `output/audit.json` after each run

## Environment Variables
See `.env.example`. Required:
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — for delivery
- `SUBREDDITS` — comma-separated list, e.g. `r/MachineLearning,r/LocalLLaMA` (optional, has default)
- `CRT_ABERRATION` — set to `1` to enable chromatic aberration in Remotion renders (optional, default off)
