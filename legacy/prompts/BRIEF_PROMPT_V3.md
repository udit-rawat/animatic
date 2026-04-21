# adamax brief prompt v3 — content strategy + custom animation

Paste this entire file into Claude. It will output a shell command you can run directly.

This version targets **30–45 second Reels** with high save + share rates.
The pipeline pauses before animation so you can approve a custom hook animation brief.

---

## CONTENT STRATEGY

Do NOT make generic AI news Reels. Pick ONE of these three formats:

### Format A — The Cheat Code
*Most [audience] don't know you can do X with Y. Here's how.*
- Best for: open-source tools, free alternatives, developer tricks
- Hook pattern: "The $X/month tool you're using just became free."
- Save rate: very high (they'll do it later)
- Example topics: local AI replacing paid APIs, free alternatives to Cursor/Copilot/ElevenLabs

### Format B — The Hidden Cost Reveal
*You're paying $X/month for Y. This does the same thing for $0.*
- Best for: any paid tool that now has a free/open-source equivalent
- Hook pattern: Lead with the dollar amount they're currently losing
- Share rate: very high (makes sender look smart)
- Example topics: any time a major lab open-sources something that was paid

### Format C — The Reframe
*Everyone is talking about X. Nobody is talking about what it means for [specific audience].*
- Best for: major releases where the real implication is non-obvious
- Hook pattern: Surface the thing no other account is saying
- Comment rate: high (people have strong opinions)
- Example topics: capability leaps, model releases with hidden implications

---

## TARGET AUDIENCE

**Indie developers, technical creators, and builders** — not general tech curious.
Every hook should speak to someone who writes code or ships products.
Ask: does this save them time, money, or give them a competitive edge?

---

## VIDEO LENGTH

**30–45 seconds. Hard limit.**

| Segment | Duration | Word budget |
|---|---|---|
| `hook` | 4–6s | ≤ 18 words |
| `concept_1` | 8–12s | ≤ 28 words |
| `concept_2` | 8–10s | ≤ 22 words |
| `takeaway_cta` | 6–8s | ≤ 18 words |

**Total: 75–90 words across all four segments.**

At Gemini TTS pace (~1.4 words/sec), 86 words = ~61s. Keep total under 80 words for a 45s video.

---

## HOOK PATTERNS (pick the one that fits the format)

**Pattern A — The cost punch:**
`[$amount] → [what it bought] → [now free/cheaper] → [proof]`
> "You were paying twenty dollars a month for this. Google just made it free. Gemma 4. Download it now."

**Pattern B — The specific contradiction:**
`[what everyone believes] → [what just changed] → [the number that proves it]`
> "Every offline AI needed a server. Gemma 4 runs on your laptop. One point one five gigabytes."

**Pattern C — The non-obvious take:**
`[what the news says] → [what it actually means] → [for your specific audience]`
> "Four hundred million downloads. That is not a stat. That is every developer on earth picking a side."

---

## BANNED WORDS

`incredibly` `massive` `huge` `enormous` `groundbreaking` `revolutionary`
`mind-blowing` `game changer` `this changes everything` `next level`
`basically` `essentially` `kind of` `at its core` `simply put`
`in conclusion` `as we can see` `today we look at` `let's dive in`
`leverage` `supercharged` `powerful`

---

## TONE PRESETS

| Tone | Description |
|---|---|
| **machine-gun** | `"Machine-gun pace. No pauses. Every sentence lands hard. Numbers hit like punches."` |
| **deadpan** | `"Flat and dry. State facts like you have seen it all. Slight pause after numbers."` |
| **urgent** | `"Breaking news energy. Short sentences. Breathless. No room to breathe between points."` |
| **skeptical** | `"Measured and slightly cynical. Raise an eyebrow on the hook. Let the facts speak."` |

---

## SUMMARY vs NARRATION

- `--summary` → used ONLY for visual layout generation (what templates, what numbers on screen). Write factual, concrete, with real numbers.
- `--narration` → your exact spoken words. Pipeline will NOT rewrite them. Keep it tight.

---

## OUTPUT FORMAT

```bash
python3 run.py --gemini --custom --compositor \
  --title "YOUR TITLE" \
  --summary "factual one-sentence summary with concrete numbers for visual layout" \
  --tone "YOUR TONE DESCRIPTION" \
  --narration '{"hook":"≤18 words","concept_1":"≤28 words","concept_2":"≤22 words","takeaway_cta":"≤18 words"}'
```

**Important:**
- Remove apostrophes from narration (use "it is" not "it's") — shell will break otherwise
- Keep the entire command on ONE line — no line breaks inside `--narration`
- `--compositor` flag pauses before animation so you can approve the animation brief

---

## WORD COUNT CHECKER

Before outputting: count every word.
- hook ≤ 18
- concept_1 ≤ 28
- concept_2 ≤ 22
- takeaway_cta ≤ 18
- **Total must be 75–86 words**

If over 86: cut adjectives first, then subordinate clauses, then combine sentences.
If under 75: add one concrete detail or number to concept_1.

---

## PIPELINE PAUSE FLOW

The `--compositor` flag means the pipeline will:
1. Run all stages (TTS, timing, layout generation)
2. Pause and show you the **exact narration going to TTS** — you confirm before audio is generated
3. After TTS: pause again and print **narration + frame timings** for each segment
4. At that second pause: share the context with Claude to get an **animation concept brief** (color, motion plan per section) — approve it before any code is written
5. Claude writes the CustomVideo.tsx, you drop it in the printed path, press Enter, pipeline renders

---

## EXAMPLE — Format B (Hidden Cost Reveal)

**Topic:** Gemma 4 by Google — free open-source model replacing paid APIs

```bash
python3 run.py --gemini --custom --compositor --title "Google Just Killed Your AI API Bill" --summary "Google released Gemma 4, a 27B open-source model under Apache 2.0. Runs locally, matches GPT-4o on reasoning benchmarks, 400M downloads of previous versions. Replaces paid API calls for most developer use cases." --tone "Machine-gun pace. No pauses. Every sentence lands hard. Numbers hit like punches." --narration '{"hook":"You are paying per API call. Google just open-sourced a model that matches GPT-4o. Runs on your machine. Free.","concept_1":"Gemma 4. Twenty-seven billion parameters. Apache license. Runs locally. Complex reasoning, planning, agents — it handles all of it. Four hundred million downloads of older versions.","concept_2":"No more API bills. No data leaving your machine. Deploy it yourself in three commands. Your costs just dropped to zero.","takeaway_cta":"Rule: when Google open-sources a GPT-4o competitor, you move the same day. Gemma 4 is live. Go."}'
```

**Word count check:**
- hook: 17 ✓
- concept_1: 26 ✓
- concept_2: 20 ✓
- takeaway_cta: 17 ✓
- Total: 80 words → ~57s ✓

---

## TOPIC SELECTION GUIDE

When scanning AI news, filter for:

| Signal | Why it works |
|---|---|
| Paid tool → now free | Format B, instant save/share |
| Closed model → now open | Format B or C |
| Size/speed record broken | Format C with the specific number |
| Tool that replaces another tool | Format A or B, name the tool it kills |
| Capability that was impossible last month | Format C, "nobody is talking about" frame |

**Skip if:**
- It is just a benchmark improvement with no practical implication
- The tool requires enterprise access or waitlist
- Five other AI accounts already posted it with the same angle
