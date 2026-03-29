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
- At least 2–3 specific numbers (latency, memory savings, accuracy delta, parameter count, throughput gain — real benchmarks only)
- The exact mechanism causing the effect — not "it is faster" but WHY it is faster at a systems level
- A before/after or A-vs-B comparison if one exists
- The practical implication — what should an engineer actually do differently after knowing this

The brief must NOT contain:
- Hype words: "revolutionary", "game-changing", "groundbreaking", "incredible"
- Vague claims with no numbers attached
- Unexplained jargon — if you use a technical term, define it in one clause
- Anything that cannot be verified from a paper, benchmark, or official repo

Target length: 80–120 words. Dense. Every sentence must carry a fact.

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
  --summary "Standard attention materialises the full N×N attention matrix in HBM, costing O(N²) memory and dominated by memory bandwidth. Flash Attention 2 tiles Q, K, V in SRAM and fuses the softmax+matmul into a single kernel, never writing the full matrix to HBM. Result: 2–4× wall-clock speedup on A100, 5–20× memory reduction at 32K context. At 7B scale with 128K context, standard attention OOMs on a single 80GB GPU. Flash Attention 2 fits in 40GB. The implementation is a drop-in replacement via torch.nn.functional.scaled_dot_product_attention in PyTorch 2.0+."
```
