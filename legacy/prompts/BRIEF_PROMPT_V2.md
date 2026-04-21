# adamax brief prompt v2 — custom narration + tone

Use this prompt when you want full control over what is spoken in the video.
The pipeline will still generate all visuals (layout, animations, beat timing) automatically —
you are only providing the voice script and delivery tone.

Paste this entire file into Claude, Grok, or any LLM. It will output a shell command you can run directly.

---

## WHAT YOU ARE WRITING

A spoken voiceover for a 60-second AI explainer Reel. Four segments:

| Segment | Duration | Purpose |
|---|---|---|
| `hook` | 5–8s | Stop the scroll. Broken assumption or desire + proof number. |
| `concept_1` | 10–15s | The mechanism — what it is at the code/architecture level. |
| `concept_2` | 12–18s | The implication — what changes for how engineers build. |
| `takeaway_cta` | 8–12s | Save-trigger first (rule/number/command), then provocation. |

**Total word count: 130–145 words across all four segments.**

---

## HOOK PATTERNS (pick the one that fits)

**Pattern A — Mechanism / contradiction:**
`[what was assumed true] → [what this breaks] → [the number]`
> "Every 1-bit LLM kept embeddings at 16-bit. Bonsai closes that. 1.15 GB. Your iPhone."

**Pattern B — Capability / desire:**
`[desire engineers have] → [it now exists] → [proof number]`
> "Private ChatGPT. Your iPhone. No internet. 1.15 GB. 44 tokens per second."

**Pattern C — Leak / drama / controversy:**
`[the reveal] → [why it matters] → [the number that makes it real]`
> "Anthropic accidentally published 3,000 internal files. One of them named Mythos. A model above Opus."

---

## BANNED WORDS (do not use in any segment)

`incredibly` `massive` `huge` `enormous` `groundbreaking` `revolutionary`
`mind-blowing` `next level` `this changes everything` `game changer`
`basically` `essentially` `kind of` `at its core` `simply put`
`in conclusion` `as we can see` `today we look at` `let's dive in`

---

## TONE OPTIONS

Pick one or write your own. This controls how the TTS voice delivers the script.

| Tone name | Description to use |
|---|---|
| **default** | *(omit --tone flag)* — Sharp ML engineer, urgent but grounded |
| **deadpan** | `"Flat and dry. No excitement. State facts like you've seen it all before. Brief pauses after numbers."` |
| **urgent** | `"Fast, breathless, like breaking news. Short sentences. Hit numbers hard. No pause."` |
| **skeptical** | `"Measured and slightly cynical. Emphasize the contradiction. Raise an eyebrow on the hook."` |
| **hype** | `"High energy, punchy, like a product launch. Big pauses for drama. Numbers land like reveals."` |
| **deep-tech** | `"Slow and precise. Pause after every technical term. Treat the audience as PhD-level peers."` |

---

## OUTPUT FORMAT

The LLM should output a shell command in this exact format:

```bash
python3 run.py --gemini --custom \
  --title "YOUR TITLE HERE" \
  --summary "one sentence summary for visual layout generation" \
  --tone "YOUR TONE DESCRIPTION" \
  --narration '{
    "hook":        "YOUR HOOK (≤28 words)",
    "concept_1":   "YOUR CONCEPT 1 (≤36 words)",
    "concept_2":   "YOUR CONCEPT 2 (≤45 words)",
    "takeaway_cta":"YOUR TAKEAWAY (≤28 words, save-trigger first)"
  }'
```

**Important:**
- `--summary` is used ONLY for visual layout generation (which template, which numbers on screen). Write a factual summary with concrete numbers.
- `--narration` is your exact spoken words. The pipeline will NOT rewrite them.
- `--tone` replaces the default voice directive entirely. Make it specific — the TTS model reads it literally.

---

## EXAMPLE OUTPUT (Anthropic Mythos leak topic)

```bash
python3 run.py --gemini --custom \
  --title "Anthropic's Secret 'Step Change' Model Just Leaked" \
  --summary "Anthropic's internal Claude Mythos model was accidentally exposed via a config error that made 3,000 files public. Mythos sits above Opus, with step-change improvements in reasoning and coding. The leak revealed it leads all models in cyber capabilities and could enable large-scale attacks. Extremely expensive, invite-only testing with enterprise customers." \
  --tone "Flat and measured. State each fact like it is already confirmed. No excitement — the facts are dramatic enough. Slight pause after 'Mythos' and after 'cyberattacks'." \
  --narration '{
    "hook":        "Anthropic published 3,000 internal files by accident. One named a model above Opus. They called it a step change.",
    "concept_1":   "Mythos leaked from a misconfigured CMS. The draft blog post said it leads every other model in cyber capabilities. Could enable large-scale attacks. Anthropic confirmed it exists.",
    "concept_2":   "It is invite-only. Extremely compute-intensive. Anthropic is privately warning governments. The model is real — just not yours yet.",
    "takeaway_cta":"Rule: when a lab calls something a step change above Opus, take the cyber warning seriously. Mythos is not released. The leak is."
  }'
```

---

## WORD COUNT CHECKER

Before you output the command, count words in each segment:
- hook ≤ 28 words
- concept_1 ≤ 36 words  
- concept_2 ≤ 45 words
- takeaway_cta ≤ 28 words
- **Total must be 130–145 words**

If under 130: expand concept_1 or concept_2 with one more concrete detail.
If over 145: cut adverbs first, then adjectives, then subordinate clauses.
