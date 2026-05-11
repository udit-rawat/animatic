# Reel Production Deterministic Playbook

Purpose: make high-retention technical reels with fewer re-renders by locking content, narration, layout, animation, and QA before final export.

This document is based on the sparse/MoE reel failure modes:
- Hook did not explain the topic in the first 3 seconds.
- Analogy appeared before the viewer knew what the reel was about.
- Absolute-positioned layers overlapped at runtime.
- One continuous narration file drifted away from manually timed animation.
- Final 49-53 seconds became a static infographic.
- Validation happened after render instead of before render-critical checkpoints.

## Non-Negotiable Production Contract

Every reel must satisfy these constraints before final render:

- The first 3 seconds must state the topic and the visual premise directly.
- No analogy can appear before the core mechanism is named.
- Narration must be split into scene-locked or phrase-locked segments.
- Animation beats must be keyed to segment start times, not guessed global timestamps.
- Each scene needs one hero object, one support object, and one bottom-third anchor.
- No critical text inside top `0-220px`, bottom `1500-1920px`, or right `850-1080px`.
- No major scene can stay visually static for more than 1.5 seconds.
- The final 4 seconds must contain an active CTA animation, not a held card.
- Lint must be clean before render.
- Extract frame checks must happen at hook, transition, dense layout, CTA, and final frame.

## Voice Clone Input Standard

If using a cloned real voice, record a dedicated "narration calibration pack":

- Record at 48 kHz WAV, 24-bit if possible.
- Use the same mic, distance, gain, room, and tone every time.
- Speak 6-8 inches from mic with pop filter.
- Keep true peak below `-3 dB`.
- Target raw spoken RMS around `-23 dB` to `-18 dB`.
- Record in one clean mono voice only. No room echo, music, fans, typing, or chair noise.
- Capture at least 10 minutes for local zero-shot testing.
- Capture 30-60 minutes for stronger SaaS or fine-tuned cloning.
- Capture one "reel voice" style only: calm, technical, human, concise.

Recommended voice style:

```text
Voice persona: technical founder explaining a hard idea to smart developers.
Tone: calm, focused, conversational, not salesy.
Pacing: steady, 145-160 WPM, with short pauses after conceptual turns.
Energy: controlled urgency in the hook, warmer explanation in the middle, decisive CTA.
Avoid: robotic system-report delivery, fake influencer hype, long dead silences, fast disclaimer pacing.
```

## Script Architecture

Use this exact content spine:

1. `Hook`: name the surprising mechanism immediately.
2. `Pain`: show why the default behavior is wasteful or unintuitive.
3. `Mechanism`: explain the core system in simple terms.
4. `Dispatch`: show one concrete input moving through the mechanism.
5. `Proof`: use one real number, product, model, benchmark, or implementation fact.
6. `Correction`: clarify the misconception.
7. `CTA`: ask one useful mental-model question.

Do not start with:

- "If you have ever..."
- "Most people do not know..."
- "This changes everything..."
- A generic analogy.
- A benchmark without context.

Good hook template:

```text
{Technical object} has one trick.
It does not {wasteful default behavior}.
It {specific mechanism} instead.
```

Example:

```text
Mixture of Experts has one trick.
It does not run the whole model for every token.
It routes each token through a smaller path.
```

## Narration Rules

Narration must be written as segments, not one paragraph.

Each segment must include:

- `id`
- `start`
- `duration`
- `text`
- `visual_hit`

Example:

```json
{
  "id": "s03_router",
  "start": 13.55,
  "duration": 7.85,
  "text": "MoE adds a router. The router scores the specialists, picks the top two, and the rest stay dark.",
  "visual_hit": {
    "router_appears": 13.95,
    "scan_starts": 17.70,
    "top_two_lock": 18.35
  }
}
```

Guidelines:

- Keep most sentences under 12 words.
- One technical term per sentence.
- Explain with concrete nouns: token, router, expert, path, weights.
- Avoid abstract filler: magic, insane, crazy, game-changing.
- If a phrase needs a visual hit, isolate it in the segment.
- Do not compress a slow raw TTS file into a short target unless the speedup is under 8%.

## Layout Rules

Canvas:

- `1080x1920`
- Active box: approximately `72px <= x <= 850px`, `220px <= y <= 1500px`
- Watermark: `x=72`, `y≈1470`, never under CTA cards.

Scene layout:

- Headline top-left, not centered.
- Hero object below headline, never overlapping baseline.
- Support object either right side within safe reserve or bottom third.
- Bottom-third anchor must be useful: timeline, state strip, CTA, terminal, rail, or active queue.

Layering:

```css
.background { z-index: 0; }
.decorative-motion { z-index: 1; }
.hero-object { z-index: 2; }
.support-panels { z-index: 3; }
.labels-and-counters { z-index: 4; }
.token-particles { z-index: 5; }
.headline { z-index: 6; }
.watermark { z-index: 10; }
```

Avoid:

- Floating text over busy animation.
- Reusing the same physical space across overlapping timeline windows.
- `from()` on elements whose CSS opacity is `0`; use `fromTo()`.
- Animating the same property on the same selector in overlapping windows.
- Lower CTA cards that collide with the watermark.

## Animation Rules

Every scene needs continuous purposeful motion:

- Hook: major visual event by `0.8s`.
- Mechanism scene: scanning, routing, scoring, or state transition.
- Proof scene: counter or path change that visually proves the number.
- Takeaway scene: contrasting states remain alive through CTA.

Motion density standard:

- No static hold longer than 1.5s.
- At least one primary object moves every 1.0s.
- Ambient movement is not enough; the concept object must move.
- CTA must animate until final fade.

Use semantic visual hits:

- "fires" -> shockwave.
- "router" -> diamond materializes.
- "scores" -> scan beam.
- "top two" -> two experts lock active.
- "narrower path" -> spotlight/path compression.
- "not memory" -> all weights remain visible.
- "actually ran" -> terminal question types in.

## Audio Sync Rules

Use segmented TTS:

- One WAV per scene, or one generated `narration.wav` assembled from scene segments.
- Keep `stretch_short_segments=false` unless a segment is only slightly long.
- If raw segment exceeds target by more than 8%, rewrite the text instead of speeding it up.
- Save `narration_timing.json`.
- Animation timings must reference segment start times.

Bad:

```js
tl.to(".router", {...}, 12.7); // guessed from one long narration file
```

Good:

```js
const S3 = 13.55;
tl.from(".scene3 .router", {...}, S3 + 0.4);
tl.to(".scene3 .router-scan", {...}, S3 + 4.15);
```

## Render QA Checklist

Before render:

- HyperFrames lint: `0 errors, 0 warnings`.
- Confirm narration file exists.
- Confirm root `data-duration` equals spec duration.
- Confirm no hidden element depends on `from()` to become visible.
- Confirm no CTA overlaps watermark.

After first render, extract frames:

```bash
ffmpeg -hide_banner -loglevel error -y -ss 1.0  -i output/REEL.mp4 -frames:v 1 /private/tmp/reel_01.png
ffmpeg -hide_banner -loglevel error -y -ss 3.0  -i output/REEL.mp4 -frames:v 1 /private/tmp/reel_03.png
ffmpeg -hide_banner -loglevel error -y -ss 4.0  -i output/REEL.mp4 -frames:v 1 /private/tmp/reel_04.png
ffmpeg -hide_banner -loglevel error -y -ss 49.5 -i output/REEL.mp4 -frames:v 1 /private/tmp/reel_495.png
ffmpeg -hide_banner -loglevel error -y -ss 52.0 -i output/REEL.mp4 -frames:v 1 /private/tmp/reel_52.png
```

Review:

- `1s`: topic is obvious.
- `3s`: hook is still readable.
- `4s`: no hero/headline overlap.
- `49.5s`: CTA has started and is moving.
- `52s`: final frame is readable and watermark is clean.

Metadata check:

```bash
ffprobe -v error \
  -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels \
  -of default=noprint_wrappers=1 output/REEL.mp4
```

## Deterministic Reel Prompt Template

Use this prompt before building any new reel:

```text
Build a 1080x1920 HyperFrames reel.

Topic:
{one-line topic}

Core thesis:
{one falsifiable sentence}

Audience:
Developers / AI builders. Assume smart but not already expert in this subtopic.

Hook rule:
The first 3 seconds must make the topic obvious. Do not start with an analogy, benchmark, or conditional opener.

Narration:
Write 6-7 scene-locked narration segments with start, duration, text, and visual_hit. Keep a steady human technical voice. No robotic system report. No hype. If a segment is too long for its timing, rewrite it instead of speeding up TTS.

Visual system:
Dark graphite technical interface. Sparse color. Use cyan only for active/optimized paths, red only for waste/error, amber only for stored weights or caution. Keep @ada.max24 at bottom-left, clean and unobstructed.

Safe zones:
No critical text in y=0-220, y=1500-1920, x=850-1080.

Scene contract:
Every scene must have one hero object, one support object, one bottom-third anchor, and no static hold over 1.5s.

Animation contract:
Use semantic hits. Key animation timings to narration segment starts. Include active final CTA motion through the last second.

QA contract:
Before final answer, lint clean, generate segmented narration, render, ffprobe, and extract/check frames at 1s, 3s, 4s, final CTA start, and final frame.
```

## Voice Cloning Integration Plan

Current recommended options:

| Option | Cost | Strength | Caveat | Recommendation |
| --- | ---: | --- | --- | --- |
| Chatterbox TTS | Free local | Open-source, MIT license, supports cloning from a short reference clip | Needs local Python/GPU setup; quality must be tested against your voice | First experiment |
| OpenVoice V2 | Free local | MIT licensed, explicitly free for commercial use, multilingual voice cloning | More engineering effort; may need post-processing | Good fallback if Chatterbox voice match is weak |
| ElevenLabs Instant Voice Clone | Low SaaS cost | Fastest usable production path, commercial license on paid Starter tier | Monthly credit limits and hosted dependency | Best low-friction paid path |
| ElevenLabs Professional Voice Clone | Higher SaaS cost | Better identity consistency | Creator tier or above; more setup | Use if the account voice becomes core brand asset |
| F5-TTS | Free local for testing | Strong open-source TTS ecosystem | Pretrained models are CC-BY-NC, so avoid for commercial/brand reels unless licensing is resolved | Research only for this pipeline |

Preferred pipeline:

1. Record a clean reference pack.
2. Generate one test reel narration using local Chatterbox or SaaS clone.
3. Listen for pronunciation, cadence, and fatigue.
4. Save the best clone as `assets/voices/adamax_reference.wav`.
5. Add a new TTS provider script that accepts scene segments and outputs `narration.wav` plus `narration_timing.json`.
6. Keep Gemini/ElevenLabs as fallback until the cloned voice consistently beats them.

Folder convention:

```text
assets/voices/
  adamax_reference_raw.wav
  adamax_reference_clean.wav
  adamax_reference_10s.wav
  adamax_reference_60s.wav

cache/voice_clones/
  chatterbox/
  elevenlabs/

output/hyperframes_custom/<date>_<slug>/
  narration.wav
  narration_timing.json
```

Acceptance bar for cloned voice:

- Sounds like the real speaker within 3 seconds.
- Does not flatten emphasis on technical terms.
- Does not randomly change speed between scenes.
- Pronounces model names and code terms correctly.
- Does not introduce mouth clicks, metallic artifacts, or room tone pumping.
- Beats Aoede on trust, not just novelty.
