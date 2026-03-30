# adamax content brief — paste this into any LLM

You are generating a technical brief for a 60-second short-form AI explainer video.
The audience ranges from Python developers with no ML background to senior data scientists.
The non-expert must understand the WHAT. The expert must feel the WHY is worth their time.
The video will be posted on Instagram Reels / YouTube Shorts.

---

## YOUR TOPIC

[REPLACE THIS LINE WITH YOUR TOPIC]

---

## YOUR JOB

Research the topic above and produce a dense technical brief.
Then output a ready-to-run CLI command at the bottom.

---

## BRIEF REQUIREMENTS

The brief must contain:
- The single most surprising or counterintuitive fact about this topic
- At least 2–3 specific numbers (latency, memory savings, accuracy delta, throughput, cost — real benchmarks only)
- The exact mechanism causing the effect — not "it is faster" but WHY at a systems level
- One of the following if it exists in the topic:
  - A before/after or A-vs-B with measurable delta → good for "comparison" or "bar" layout
  - A ranked benchmark result across 3+ models/systems → good for "leaderboard" layout
  - A chronological arc with key dates and metrics → good for "timeline" layout
  - A code snippet that changed (old API → new API, or the fix) → good for "codediff" layout
  - 2-3 distinct numbers that measure different dimensions of the same thing → good for "tristat" layout
- The practical implication — what should an engineer do differently after knowing this

The brief must NOT contain:
- Hype words: "revolutionary", "game-changing", "groundbreaking", "incredible"
- Vague claims with no numbers attached
- Unexplained jargon — if you use a technical term, define it in one clause
- Anything that cannot be verified from a paper, benchmark, or official repo

Target length: 80–120 words. Dense. Every sentence must carry a fact.

---

## LAYOUT HINT (optional but recommended)

After your brief, add one line suggesting the best visual layout.

**Decision guide — pick the MOST SPECIFIC match:**

| Signal in your brief | Layout |
|---|---|
| Each item has only ONE number, gap size is the story | `bar` |
| TWO systems, EACH described by 2+ different metrics | `comparison` |
| 2-3 fundamentally different measurements about ONE system | `tristat` |
| Ranked table of 3-6 models scored on one benchmark | `leaderboard` |
| Chronological arc with dated milestones | `timeline` |
| Sequential process with a named bottleneck | `pipeline` |
| Before/after code snippet | `codediff` |
| Single hero number defines everything | `metric` |

**Do NOT use `comparison` if each side only has one number — use `bar` instead.**

Layout options with required data:

- `LAYOUT: comparison` — TWO sides, each with 2-4 different metrics (e.g. latency + accuracy + cost per side)
- `LAYOUT: bar` — 2-5 items on ONE numeric metric; include the numeric values + unit (e.g. "382 tok/s vs 232 tok/s")
- `LAYOUT: leaderboard` — include rank number, model name, and score for each row (3-6 rows)
- `LAYOUT: timeline` — include dates + key metric at each milestone (3-5 milestones)
- `LAYOUT: tristat` — 2-3 different-dimension numbers about the same system (e.g. total params + active params + price)
- `LAYOUT: codediff` — include the actual simplified before/after code lines (≤50 chars each, max 5 before / 3 after)
- `LAYOUT: pipeline` — name the 3-5 sequential stages and which one is the bottleneck
- `LAYOUT: metric` — single hero number that defines the insight

---

## OUTPUT FORMAT

Produce exactly this at the end — nothing else after it:

```bash
python3 run.py --gemini --checkpoint --custom \
  --title "YOUR CONCISE TITLE HERE (max 10 words)" \
  --summary "YOUR DENSE TECHNICAL BRIEF HERE (80-120 words, no line breaks, no quotes inside)"
```

---

## EXAMPLE OUTPUT (do not copy — for format reference only)

```bash
python3 run.py --gemini --checkpoint --custom \
  --title "Flash Attention 2 vs Standard Attention" \
  --summary "Standard attention materialises the full N×N attention matrix in HBM, costing O(N²) memory and dominated by memory bandwidth. Flash Attention 2 tiles Q, K, V in SRAM and fuses the softmax+matmul into a single kernel, never writing the full matrix to HBM. Result: 2-4x wall-clock speedup on A100, 5-20x memory reduction at 32K context. At 7B scale with 128K context, standard attention OOMs on a single 80GB GPU. Flash Attention 2 fits in 40GB. The implementation is a drop-in replacement via torch.nn.functional.scaled_dot_product_attention in PyTorch 2.0+."
```
