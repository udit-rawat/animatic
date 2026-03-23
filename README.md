# adamax-content-engine

Fully automated daily pipeline that scrapes AI/ML content, picks the best topic, writes a script, generates a Manim animation synced to a voiceover, and delivers the final video to Telegram — zero manual steps.

---

## Pipeline

```
scraper → ranker → scripter → narrator → animator → mixer → notifier
```

**scraper** — Pulls the top 24h posts from 7 ML subreddits + 3 arXiv papers using public endpoints, no API keys. Produces `output/candidates.json` with ~21 ranked candidates.

**ranker** — LLM-as-judge scores each candidate on four dimensions: visual potential (can it be shown as clean Manim animations?), engineer value (actionable today?), freshness (new in last 72h?), and focus (fully explainable in 60s?). Picks one winner. Skips any topic in `output/picked_history.json` (last 30 picks). Writes `output/topic.json`.

**scripter** — Writes a structured 60s script: hook / 4 concept bullets / takeaway / CTA + social caption + hashtags. Writes `output/script.json`.

**narrator** — Two sub-steps. First, an LLM pass rewrites the visual script into a segmented spoken narration — one section per script part (hook, concept_1…N, takeaway_cta). Second, each section is converted to audio via Gemini TTS independently, durations are measured, and the PCM chunks are stitched into `output/narration.wav`. Timing for every section is saved to `output/narration_timing.json`.

**animator** — Reads `script.json` + `narration_timing.json`. Builds a Manim prompt that includes the exact timecodes for every section (`[start → end  dur=Xs]`). LLM generates a complete Manim Python scene where each visual segment uses `self.wait()` to match the pre-recorded narration timing. Renders via `manim -qh`, auto-retries up to 3× with the error fed back to the LLM. Produces `output/video.mp4`.

**mixer** — ffmpeg merges `video.mp4` + `narration.wav` → `output/video_final.mp4`. Applies a `setpts` time-stretch as a safety net if the video and audio durations drift slightly.

**notifier** — Sends `video_final.mp4` + caption + hashtags + token audit table to Telegram. Saves the picked topic to `picked_history.json` only after a confirmed successful delivery.

---

## LLM Layer

All LLM calls route through `pipeline/claude_client.py`. Stages are provider-agnostic. Active provider is controlled by `FORCE_PROVIDER` env var or the `--provider` CLI flag.

**Providers (in priority order):** Gemini → OpenRouter → Anthropic SDK → Claude CLI

**Gemini** is the primary provider. Supports up to 4 API keys configured via `GEMINI_API_KEYS` (comma-separated). Keys rotate automatically when one exhausts its daily 20 RPD quota — total capacity scales linearly (4 keys = 80 RPD). Per-key exhaustion is tracked in `output/gemini_quota.json` and persists across runs within the same calendar day.

**OpenRouter** is the fallback. Per-stage model routing via `OPENROUTER_MODEL_RANKER`, `OPENROUTER_MODEL_SCRIPTER`, `OPENROUTER_MODEL_ANIMATOR`. Falls back to `OPENROUTER_FALLBACK` model on 404.

**Handoff mode** (`--provider handoff` or `--handoff-animator`) pauses the animator stage, writes the generated prompt to `output/handoff_animator_prompt.txt`, and polls for `output/handoff_animator_output.txt` every 5s. Allows a manual Claude session (with extended thinking) to generate high-quality Manim code while the pipeline auto-resumes.

**Gemini TTS** is always used for narration regardless of the LLM provider. `GEMINI_API_KEY` must be set.

---

## Audio/Video Sync Design

The narrator runs **before** the animator. This is intentional: narration timings are the source of truth. The animator prompt receives the actual audio durations per section and is instructed to write Manim `self.wait()` calls that match them exactly. The result is frame-accurate sync without post-processing tricks.

---

## Quota Management

`pipeline/quota.py` tracks daily Gemini API usage in `output/gemini_quota.json`. Resets each calendar day. Tracks total calls, per-stage breakdown, per-key exhaustion, and a run-level audit log.

`python3 run.py --check-quota` — prints current quota bar and per-key status.
`python3 run.py --rca` — full run-level table with root cause flags (duplicate runs, failed-run waste, animator retry cost).

---

## Output Artifacts

```
output/
├── candidates.json         — scraped topic pool
├── topic.json              — selected topic + why_picked
├── script.json             — hook, bullets, takeaway, CTA, caption, hashtags
├── narration_timing.json   — per-section timecodes {start, end, duration, text}
├── narration.wav           — stitched TTS audio (24kHz 16-bit mono PCM)
├── video.mp4               — raw Manim render
├── video_final.mp4         — final synced video (sent to Telegram)
├── picked_history.json     — last 30 delivered topics (dedup guard)
├── audit.json              — token usage per stage
├── gemini_quota.json       — daily quota state with run-level audit
└── pipeline.log            — full debug log
```

---

## Project Structure

```
adamax-content-engine/
├── run.py                    — pipeline runner + CLI entry point
├── pipeline/
│   ├── claude_client.py      — unified LLM call layer (Gemini key rotation, OpenRouter, handoff)
│   ├── scraper.py            — Reddit + arXiv fetcher
│   ├── ranker.py             — LLM topic selector with history dedup
│   ├── scripter.py           — video script writer
│   ├── narrator.py           — segmented narration writer + Gemini TTS stitcher
│   ├── animator.py           — timing-aware Manim code generator + renderer
│   ├── mixer.py              — ffmpeg audio/video merger with drift correction
│   ├── notifier.py           — Telegram delivery + history commit
│   ├── auditor.py            — token usage tracker + box-drawn table
│   ├── quota.py              — Gemini daily quota tracker + RCA reporter
│   └── logger.py             — structured logging
├── manim_scripts/
│   └── scene.py              — generated Manim scene (overwritten each run)
└── output/                   — all generated artifacts
```
