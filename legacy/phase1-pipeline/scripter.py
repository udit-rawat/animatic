import json
import os

from pipeline import claude_client

INPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")


def build_prompt(topic: dict, correction: str | None = None) -> str:
    correction_block = ""
    if correction:
        correction_block = f"""
CORRECTION DIRECTIVE — a previous draft was rejected by the fact-checker.
You MUST fix the following before writing the new script:
{correction}
Do NOT repeat any of the hallucinated or contradicted claims above.

"""
    return f"""\
You are writing on-screen text for a 25–35 second AI explainer reel for Instagram.
Target: GitHub repos, X launches, and AI tool releases people can run TODAY.
These strings render as LARGE TEXT on a dark screen — immediately readable, creating
curiosity or surprise. NOT stage directions. NOT narration. Just the words on screen.

AUDIENCE: Technically-curious Instagram users — not just ML engineers.
They know ChatGPT, OpenAI, Google, Meta, Llama, Gemini.
Write so both an engineer AND a smart non-technical founder can follow along.

DISTRIBUTION MECHANIC: Instagram pushes content via SHARES and SAVES.
SAVES are the #1 signal — people save content they want to act on later.
"How to use X" and "you can run this today" content gets saved. Write for that.

CONTENT PRIORITY — in order:
1. NEW GITHUB REPO / AI TOOL: something built on Llama, GPT-4, Claude, Gemini, or Stable Diffusion
   that went viral on GitHub or X in the last 48 hours. Hook = what it does + famous model reference.
   Script structure: hook (what it does, famous model) → install command → what you can build → pull it today.
2. MODEL RELEASE / BREAKTHROUGH: new model from famous lab with a specific surprising number.
3. RESEARCH PAPER: only if it has a concrete trick + public demo.

TOPIC: {topic['title']}
SUMMARY: {topic['summary']}
{correction_block}OUTPUT RULES — 25–35 SECOND TARGET (every word must earn its place):

hook (≤8 words spoken aloud):
  Open with a DRAMATIC REVERSAL or SURPRISING FACT — not a pain point.
  The hook must include either: (a) a well-known brand name / model (Llama, GPT-4, Claude),
  or (b) a specific number that defies expectation, or (c) a dramatic reversal ("just killed",
  "just broke", "replaced by", "runs on your laptop").
  DO NOT open with "Your GPU is..." or generic friction. Make it about something HAPPENING NOW.
  GOOD: "Someone built local GPT-4 — with Llama 4. Free."
  GOOD: "Google's AI just broke a 56-year-old math record."
  GOOD: "119 billion parameters. Only 6 billion fire. One model."
  BAD:  "Your GPU is idle but your latency is 400ms. Why?"  ← pain-point, no brand
  BAD:  "52GB RSS. VRAM untouched."  ← too niche, no hook

concept_bullets[0] (≤14 words total):
  The mechanism — what exactly this repo/model/tool does. Name it directly.
  For a GitHub repo: what problem it solves and which famous model powers it.
  One sentence. Concrete. Tech journalist tone — not a hacker in Slack.

concept_bullets[1] (≤14 words total):
  For a REPO topic: the install or run command — copy-pasteable, ≤14 words.
    Example: "pip install agentkit && agentkit run --model llama4"
  For a MODEL topic: the quantified result. ONLY numbers from the SUMMARY. No invented benchmarks.
  For a PAPER topic: the concrete trick in one sentence.

concept_bullets[2] (≤14 words total):
  What the viewer can BUILD or DO with this — right now, on their own machine.
  Frame as an action: "Build a local X that replaces Y — no API key needed."
  This is the save-trigger bullet. Make it feel achievable today.

takeaway (≤10 words):
  For a REPO topic: repo name + "Pull it. Run it." — the viewer should know exactly what to search.
  For any topic: a statement that reframes what they thought they knew.
  Aim for the feeling of "I need to send this to someone" OR "I need to save this."
  GOOD: "Pull it. Run it. No API key. No subscription." (repo)
  GOOD: "The open-source gap just closed. Closed models have one year."
  GOOD: "You've been paying for inference you could run locally."
  BAD:  "What else in your stack are you not measuring?"  ← no shareability

HALLUCINATION RULES (critical):
- ONLY use specific numbers if they appear in the SUMMARY.
- If the SUMMARY has no benchmark numbers, DO NOT invent them.
- Never write "0ms", "100x", "500ms" unless those exact numbers are in the SUMMARY.

NEVER write "VISUAL:", "Scene:", "Animation:", "Show", "Display", or any production note.
Tone: confident, precise, slightly urgent — like a tech journalist breaking a story, not an
engineer documenting a fix. The viewer should feel like they caught something important early.

CAPTION: 2-3 sentences for Instagram. Lead with the dramatic claim + brand name.
Close with a question that makes people comment or tag someone.
HASHTAGS: exactly 5, mix of broad (#AI #OpenSource) and specific to the topic.

Respond with ONLY valid JSON:
{{
  "hook": "<curiosity gap — ≤12 words>",
  "concept_bullets": [
    "<mechanism — ≤18 words with concrete component names>",
    "<result — ≤18 words, ONLY real numbers from SUMMARY or qualitative>",
    "<implication — ≤18 words about what this unlocks or changes>"
  ],
  "takeaway": "<aha-moment + open question — ≤15 words>",
  "cta": "",
  "caption": "...",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
}}
"""


def extract_json(raw: str) -> dict:
    import re
    # Strip markdown fences
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    # Find first { ... } block
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        candidate = raw[start:end]
    else:
        candidate = raw.strip()
    # Repair: remove trailing commas before ] or }
    candidate = re.sub(r',\s*([\]}])', r'\1', candidate)
    return json.loads(candidate)


def generate_script(topic: dict, correction: str | None = None) -> dict:
    """Generate script JSON. Pass correction= to inject fact-checker feedback."""
    prompt   = build_prompt(topic, correction=correction)
    last_err = None
    for attempt in range(1, 4):
        try:
            raw    = claude_client.call(prompt, stage="scripter", json_mode=True)
            script = extract_json(raw)
            return script
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_err = e
            print(f"[scripter] JSON parse failed (attempt {attempt}/3): {e} — retrying...")
    raise RuntimeError(f"Scripter failed after 3 attempts. Last error: {last_err}")


def main():
    with open(INPUT_PATH) as f:
        topic = json.load(f)

    script = generate_script(topic)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(script, f, indent=2)

    print(f"Script saved → {OUTPUT_PATH}")
    print(f"Hook: {script['hook']}")
    return script


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
