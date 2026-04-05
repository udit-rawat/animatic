# adamax brief prompt v4 — content strategy + custom animation

Paste this entire file into Claude. It will output a shell command you can run directly.

This version targets **30–35 second Reels** with a heavily animated hook.
The account exists as a top-of-funnel for AdaMax — an MCQ platform for technical builders.
Every video must attract **indie developers, ML engineers, and builders** — not general tech curious.

---

## ACCOUNT DIRECTION — read this first

AdaMax is an MCQ/QnA platform for people who want to test and retain technical knowledge.
The Instagram account is its top funnel. Every video should attract someone who:
- Writes code or ships products
- Wants to understand AI/ML at a deeper level than Twitter threads
- Would click "test your knowledge" after watching

**The two content sins to avoid:**
1. Too generalist — "Google releases new AI" — everyone posts this, nobody converts
2. Too niche — "Sequential hidden decoding in 8B transformers" — nobody watches

**The sweet spot:** A concrete technical achievement explained so clearly that a builder immediately understands why it matters to their work. AlphaEvolve breaking a 56-year math record is the benchmark. That story has stakes, a number, and a clear implication for anyone who builds with algorithms.

---

## CONTENT FORMAT — pick ONE

### Format A — The Cheat Code
*Most builders don't know you can do X. Here is how.*
- Hook pattern: "The tool you are paying for just became free."
- Best for: open-source alternatives, free replacements, developer shortcuts
- Save rate: very high

### Format B — The Hidden Cost Reveal
*You are paying $X/month for Y. This does the same thing for $0.*
- Hook pattern: Lead with the exact dollar amount the viewer is losing
- Best for: any paid tool that now has a free/open-source equivalent
- Share rate: very high

### Format C — The Concrete Achievement
*Something that was impossible last month just happened. Here is the number that proves it.*
- Hook pattern: falsifiable claim + specific number + implication for builders
- Best for: capability leaps, records broken, architectural breakthroughs
- Follow rate: very high — this is the AlphaEvolve format

---

## TARGET AUDIENCE

**Indie developers, ML engineers, and technical builders.**
Every hook must speak to someone who writes code or ships products.
Ask before writing: does this save them time, money, or give them a competitive edge?

**Skip if:**
- It is just a benchmark number with no practical implication
- The tool requires enterprise access or a waitlist
- Five other AI accounts already posted it with the same angle
- The topic is a model version comparison with no architectural story

---

## VIDEO LENGTH — 30–35 seconds. Hard limit.

| Segment | Duration | Word budget |
|---|---|---|
| `hook` | 5–7s | ≤ 14 words |
| `concept_1` | 10–12s | ≤ 22 words |
| `concept_2` | 8–10s | ≤ 18 words |
| `takeaway_cta` | 5–7s | ≤ 14 words |

**Total: 60–72 words across all four segments.**

At Gemini TTS pace (~1.4 words/sec), 68 words = ~49s with natural pauses.
Keep total under 68 words for a clean 35s video.

**Why shorter:** MolmoWeb (31s) had better retention ratio than every 60s+ video.
The hook carries more weight when the video is short — invest in it visually.

---

## SCRIPT RULES — non-negotiable

1. **No sentence fragments.** Minimum 7 words per sentence. Write for natural speech flow, not punchy Twitter threads. "Your iPhone. No internet. No cloud." is banned — it sounds like a robot.
2. **Continuous rhythm.** Each segment should read as one flowing thought, not a list. Use connecting words: "which means", "and that", "because", "so now".
3. **One number per segment minimum.** Concrete numbers are the only thing that stops scrolling.
4. **Pain point before product.** Never open with a company name or model name. Open with what the viewer is currently losing.
5. **No sentence can start with a company name.** "Google just..." "OpenAI released..." — banned as openers.

---

## HOOK FORMULA — choose one

**Formula A — The cost punch:**
`[what they pay now] → [what just changed] → [the number that makes it real]`
> "You are paying twenty dollars a month for browser automation that breaks every week, and AllenAI just open-sourced something that runs on your laptop for free."

**Formula B — The record broken:**
`[what everyone assumed was fixed] → [the number that broke it] → [what it means for builders]`
> "A fifty-six year old math record just fell, and the thing that broke it was an AI rewriting its own algorithms at runtime."

**Formula C — The access unlock:**
`[who had this before] → [who has it now] → [the specific number that makes it real]`
> "Running a private ChatGPT on your phone used to need a server. Bonsai 8B does it in one gigabyte."

---

## BANNED WORDS

`incredibly` `massive` `huge` `enormous` `groundbreaking` `revolutionary`
`mind-blowing` `game changer` `this changes everything` `next level`
`basically` `essentially` `kind of` `at its core` `simply put`
`in conclusion` `as we can see` `today we look at` `let us dive in`
`leverage` `supercharged` `powerful` `exciting` `impressive`

---

## TONE

**Calm, precise, and slightly understated.** Like a senior engineer explaining something over coffee — they already know it is a big deal so they do not need to perform excitement. The facts carry the weight.

This replaces the "machine-gun" and "urgent" presets from V3. Those tones worked for male voices. The selected TTS voice (Aoede) is female and performs best with measured, confident delivery — not staccato urgency.

---

## SUMMARY vs NARRATION

- `--summary` → used ONLY for visual layout generation. Write factual, concrete, with real numbers.
- `--narration` → your exact spoken words. Pipeline will NOT rewrite them. Keep it tight.

---

## OUTPUT FORMAT

```bash
python3 run.py --gemini --custom --compositor \
  --title "YOUR TITLE" \
  --summary "factual one-sentence summary with concrete numbers for visual layout" \
  --tone "Calm and measured. Speak like a senior engineer who already knows this is significant — no hype needed. Pause after numbers. Continuous sentences, no fragments." \
  --narration '{"hook":"≤14 words, one continuous sentence","concept_1":"≤22 words, flowing","concept_2":"≤18 words, flowing","takeaway_cta":"≤14 words"}'
```

**Shell rules:**
- Remove apostrophes (use "it is" not "it's") — shell breaks on single quotes inside single quotes
- Keep the entire command on ONE line
- `--compositor` pauses before animation so you approve the hook animation brief

---

## WORD COUNT CHECKER

Before outputting: count every word.
- hook ≤ 14
- concept_1 ≤ 22
- concept_2 ≤ 18
- takeaway_cta ≤ 14
- **Total must be 60–68 words**

If over 68: cut adjectives first, then remove one sentence from concept_1.
If under 60: add one concrete number or implication to concept_2.

---

## PIPELINE PAUSE FLOW

The `--compositor` flag means the pipeline will:
1. Run all stages (TTS, timing, layout generation)
2. Pause and show the **exact narration going to TTS** — you confirm before audio is generated
3. After TTS: pause again and print **narration + frame timings** per segment
4. At that second pause: share context with Claude to get an **animation brief** — approve before any code is written
5. Claude writes CustomVideo.tsx, you drop it in the printed path, press Enter, pipeline renders

---

## TOPIC SELECTION GUIDE

| Signal | Format | Why it works |
|---|---|---|
| Paid tool → now free/open | B | instant save/share, builder pain point |
| Mathematical/speed record broken | C | falsifiable, stakes are clear |
| Tool that replaces another specific tool | A or B | name the tool it kills |
| Architectural breakthrough with a number | C | builders care about mechanisms |
| Capability unlock on consumer hardware | A | "runs on your laptop/phone" frame |

**The AlphaEvolve test:** Would a senior ML engineer forward this to a colleague? If yes, post it.
If it sounds like a press release, do not post it.

---

## EXAMPLE — Format C (Concrete Achievement)

**Topic:** AlphaEvolve — AI rewriting its own algorithms

```bash
python3 run.py --gemini --custom --compositor --title "AI Just Broke a 56-Year Math Record by Rewriting Its Own Code" --summary "AlphaEvolve by Google DeepMind uses evolutionary search to rewrite algorithms at runtime. It discovered a faster matrix multiplication algorithm, breaking a record that stood for 56 years. Applicable to compilers, schedulers, and any optimization problem with an exact objective." --tone "Calm and measured. Speak like a senior engineer who already knows this is significant — no hype needed. Pause after numbers. Continuous sentences, no fragments." --narration '{"hook":"A fifty-six year old math record just fell because an AI kept rewriting its own algorithm until it found one humans missed.","concept_1":"AlphaEvolve uses evolutionary search to mutate and evaluate algorithms at runtime, and it found a matrix multiplication method that is provably faster than anything we had before.","concept_2":"That matters because matrix ops sit underneath every model, every compiler, and every scheduler you run, which means this discovery compounds across the entire stack.","takeaway_cta":"When an AI finds optimizations humans missed for five decades, the right move is to integrate it immediately."}'
```

**Word count check:**
- hook: 22 — wait, recount → "A fifty-six year old math record just fell because an AI kept rewriting its own algorithm until it found one humans missed." = 24 words. Over limit.
- Correct hook: "A fifty-six year math record just fell because an AI rewrote its own algorithm." = 15 words ✓
- concept_1: 28 words — trim to 22
- concept_2: 24 words — trim to 18
- takeaway_cta: 15 words — trim to 14

Always recount after writing. The word budget is a hard constraint.
