"""
Claude client — dual mode:
  - Local (Claude Code session): uses `claude -p` CLI subprocess, no API key needed
  - CI / GitHub Actions: uses Anthropic SDK directly via ANTHROPIC_API_KEY secret

Mode is selected automatically: if ANTHROPIC_API_KEY is present in env → SDK mode.
All calls go through `call()` so token cost is tracked identically in both modes.
"""
import json
import os
import subprocess

MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 8096

_usage_log: list[dict] = []


# ── SDK mode (CI) ────────────────────────────────────────────────────────────

def _call_sdk(prompt: str, stage: str, max_tokens: int) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    input_cost  = usage.input_tokens  * 3.00  / 1_000_000
    output_cost = usage.output_tokens * 15.00 / 1_000_000
    _usage_log.append({
        "stage": stage,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": round(input_cost + output_cost, 6),
    })
    return response.content[0].text


# ── CLI mode (local Claude Code session) ─────────────────────────────────────

def _call_cli(prompt: str, stage: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"[{stage}] claude CLI failed (exit {result.returncode}):\n{result.stderr}"
        )
    raw = result.stdout.strip()
    try:
        envelope = json.loads(raw)
        text     = envelope.get("result") or envelope.get("content") or raw
        cost_usd = float(envelope.get("cost_usd", 0.0))
    except (json.JSONDecodeError, ValueError):
        text     = raw
        cost_usd = 0.0
    _usage_log.append({"stage": stage, "cost_usd": round(cost_usd, 6)})
    return text


# ── Public interface ──────────────────────────────────────────────────────────

def call(prompt: str, stage: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_sdk(prompt, stage, max_tokens)
    return _call_cli(prompt, stage)


def get_usage_log() -> list[dict]:
    return list(_usage_log)


def reset_usage_log():
    _usage_log.clear()
