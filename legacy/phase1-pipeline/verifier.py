"""
verifier.py — NLI entailment fact-checker inserted between scripter and scene_planner.

Two-pass verification loop:
  Pass 1 (Claim Extraction): extract 3-5 hard verifiable claims from the script.
  Pass 2 (Entailment Check): classify each claim against topic.summary as ground truth.
    SUPPORTED    — explicitly backed by the source summary.
    CONTRADICTED — conflicts with the source summary. HARD FAIL → triggers rewrite.
    UNVERIFIABLE — not mentioned in the summary (ground truth is a snippet, not the
                   full paper, so this is a WARNING only — does NOT trigger rewrite).

Retry loop:
  If any CONTRADICTED claim is found, the failing reasons are injected back into the
  scripter as a CORRECTION_DIRECTIVE and the script is rewritten.
  MAX_RETRIES = 2. After 2 failures, accepts the version with the fewest
  CONTRADICTED claims and logs a warning rather than blocking the pipeline.

Outputs:
  output/script.json       — overwritten with the validated (or best-effort) script
  output/verify_report.json — full audit trail: claims, verdicts, retry count
"""
import json
import os
import re

from pipeline import claude_client

TOPIC_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "verify_report.json")

MAX_RETRIES = 2


# ── Prompt builders ───────────────────────────────────────────────────────────

def _claim_extraction_prompt(script: dict) -> str:
    hook    = script.get("hook", "")
    bullets = script.get("concept_bullets", [])
    takeaway = script.get("takeaway", "")
    return f"""\
You are a fact-extraction assistant. Your job is to identify hard, verifiable claims
from a short video script. A verifiable claim is a specific assertion that can be
proven true or false — a number, a named architecture, a benchmark result, a specific
technique or variable name.

SCRIPT TO ANALYSE:
  hook:          {hook}
  concept_1:     {bullets[0] if bullets else ""}
  concept_2:     {bullets[1] if len(bullets) > 1 else ""}
  takeaway:      {takeaway}

Extract 3 to 5 hard verifiable claims. Each claim must be:
- A single, atomic assertion (one fact per claim)
- Specific — include the exact number, name, or delta if present
- NOT a vague description or opinion

GOOD examples:
  "Flash Attention 3 reduces prefill latency by 40%"
  "MALLOC_ARENA_MAX=2 reduces RSS memory growth"
  "The before state used 3GB/hour RSS; the after state is flat"

BAD examples:
  "The technique is very fast"
  "Memory usage improves significantly"

Return ONLY valid JSON:
{{"claims": ["<claim 1>", "<claim 2>", "<claim 3>"]}}
"""


def _entailment_prompt(claims: list[str], topic: dict) -> str:
    claims_block = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(claims))
    return f"""\
You are a strict NLI (Natural Language Inference) fact-checker.
Your ground truth is the source summary below. You must classify each claim
against ONLY what is stated in the source. Do not use outside knowledge.

SOURCE TITLE:   {topic.get('title', '')}
SOURCE SUMMARY: {topic.get('summary', '')}

CLAIMS TO VERIFY:
{claims_block}

For each claim, output exactly one of:
  SUPPORTED    — the source summary explicitly supports this claim
  CONTRADICTED — the source summary explicitly conflicts with this claim
  UNVERIFIABLE — the source summary does not mention this at all

IMPORTANT RULES:
- Be strict: "explicitly supports" means the summary directly states or clearly implies it.
- If the claim contains a specific number not in the summary → UNVERIFIABLE (not CONTRADICTED).
- Only mark CONTRADICTED if the summary states something that directly conflicts.
- Provide a short reason (1 sentence) for each verdict.

Return ONLY valid JSON:
{{
  "results": [
    {{"claim": "<exact claim>", "status": "SUPPORTED|CONTRADICTED|UNVERIFIABLE", "reason": "<1 sentence>"}},
    ...
  ],
  "passed": <true if zero CONTRADICTED claims, false otherwise>
}}
"""


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    raw = re.sub(r",\s*([\]}])", r"\1", raw)
    return json.loads(raw)


# ── Verification passes ───────────────────────────────────────────────────────

def extract_claims(script: dict) -> list[str]:
    prompt   = _claim_extraction_prompt(script)
    last_err = None
    for attempt in range(1, 4):
        try:
            raw    = claude_client.call(prompt, stage="verifier", json_mode=True)
            result = _parse_json(raw)
            claims = result.get("claims", [])
            assert len(claims) >= 2, "Too few claims extracted"
            return claims
        except (json.JSONDecodeError, AssertionError, ValueError) as e:
            last_err = e
            print(f"  [verifier] claim extraction attempt {attempt}/3 failed: {e}")
    raise RuntimeError(f"Verifier claim extraction failed: {last_err}")


def check_entailment(claims: list[str], topic: dict) -> dict:
    prompt   = _entailment_prompt(claims, topic)
    last_err = None
    for attempt in range(1, 4):
        try:
            raw    = claude_client.call(prompt, stage="verifier", json_mode=True)
            result = _parse_json(raw)
            assert "results" in result and "passed" in result
            # Normalise status values to uppercase
            for r in result["results"]:
                r["status"] = r["status"].strip().upper()
            # Recompute passed — never trust the LLM's boolean, derive it ourselves
            contradicted = [r for r in result["results"] if r["status"] == "CONTRADICTED"]
            result["passed"] = len(contradicted) == 0
            return result
        except (json.JSONDecodeError, AssertionError, KeyError, ValueError) as e:
            last_err = e
            print(f"  [verifier] entailment check attempt {attempt}/3 failed: {e}")
    raise RuntimeError(f"Verifier entailment check failed: {last_err}")


def _build_correction_directive(results: list[dict]) -> str:
    failed = [r for r in results if r["status"] == "CONTRADICTED"]
    lines  = ["The following claims were CONTRADICTED by the source material and MUST be removed or corrected:"]
    for r in failed:
        lines.append(f'  - Claim: "{r["claim"]}"')
        lines.append(f'    Reason: {r["reason"]}')
    lines.append("Rewrite the script using only facts that can be supported by the source summary.")
    return "\n".join(lines)


def _count_contradicted(results: list[dict]) -> int:
    return sum(1 for r in results if r["status"] == "CONTRADICTED")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    from pipeline.scripter import generate_script

    with open(TOPIC_PATH) as f:
        topic = json.load(f)
    with open(SCRIPT_PATH) as f:
        script = json.load(f)

    report = {
        "topic":   topic.get("title", ""),
        "retries": 0,
        "passes":  [],
        "outcome": None,
    }

    best_script      = script
    best_contradicted = None

    for attempt in range(MAX_RETRIES + 1):
        print(f"\n[verifier] Pass {attempt + 1}/{MAX_RETRIES + 1} — extracting claims...")
        claims = extract_claims(script)
        print(f"  Claims extracted: {len(claims)}")
        for c in claims:
            print(f"    · {c}")

        print("[verifier] Running entailment check...")
        verdict = check_entailment(claims, topic)

        # Log results
        n_supported    = sum(1 for r in verdict["results"] if r["status"] == "SUPPORTED")
        n_unverifiable = sum(1 for r in verdict["results"] if r["status"] == "UNVERIFIABLE")
        n_contradicted = _count_contradicted(verdict["results"])

        for r in verdict["results"]:
            symbol = {"SUPPORTED": "✓", "UNVERIFIABLE": "?", "CONTRADICTED": "✗"}.get(r["status"], "?")
            print(f"  {symbol} [{r['status']}] {r['claim']}")
            if r["status"] != "SUPPORTED":
                print(f"      → {r['reason']}")

        print(f"  Summary: {n_supported} supported  {n_unverifiable} unverifiable  {n_contradicted} contradicted")

        pass_record = {
            "attempt":      attempt + 1,
            "claims":       claims,
            "results":      verdict["results"],
            "n_contradicted": n_contradicted,
            "passed":       verdict["passed"],
        }
        report["passes"].append(pass_record)

        # Track best version (fewest contradictions)
        if best_contradicted is None or n_contradicted < best_contradicted:
            best_contradicted = n_contradicted
            best_script       = script

        if verdict["passed"]:
            print(f"[verifier] ✓ PASSED — zero contradicted claims.")
            if n_unverifiable > 0:
                print(f"[verifier] ⚠ {n_unverifiable} UNVERIFIABLE claim(s) — ground truth is a snippet, treating as warnings.")
            report["outcome"] = "PASSED"
            report["retries"] = attempt
            break

        # Failed — decide whether to retry
        if attempt < MAX_RETRIES:
            print(f"[verifier] ✗ FAILED — {n_contradicted} contradicted claim(s). Rewriting script (retry {attempt + 1}/{MAX_RETRIES})...")
            correction = _build_correction_directive(verdict["results"])
            script = generate_script(topic, correction=correction)
            report["retries"] += 1
        else:
            print(f"[verifier] ✗ EXHAUSTED {MAX_RETRIES} retries. Accepting best version ({best_contradicted} contradiction(s)) with warning.")
            script = best_script
            report["outcome"] = f"ACCEPTED_WITH_WARNINGS ({best_contradicted} contradicted)"

    # Save validated script
    with open(SCRIPT_PATH, "w") as f:
        json.dump(script, f, indent=2)

    # Save audit report
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Verified script saved → {SCRIPT_PATH}")
    print(f"✓ Verify report saved  → {REPORT_PATH}")
    print(f"  Outcome: {report['outcome']}  |  Retries: {report['retries']}")
    return script


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
