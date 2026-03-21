"""
Claude Code CLI wrapper.
All LLM calls go through here using `claude -p --output-format json`
so token cost is tracked per stage without any API key.
Authentication is handled by the active Claude Code session.
"""
import json
import subprocess

MODEL = "claude-sonnet-4-6"

_usage_log: list[dict] = []


def call(prompt: str, stage: str, max_tokens: int = 8096) -> str:
    """
    Send prompt to Claude via CLI and return the text response.
    Cost is recorded against the given stage name.
    """
    result = subprocess.run(
        [
            "claude",
            "-p", prompt,
            "--model", MODEL,
            "--output-format", "json",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"[{stage}] claude CLI failed (exit {result.returncode}):\n{result.stderr}"
        )

    raw = result.stdout.strip()

    # Parse the JSON envelope from --output-format json
    try:
        envelope = json.loads(raw)
        text = envelope.get("result", "") or envelope.get("content", "") or raw
        cost_usd = float(envelope.get("cost_usd", 0.0))
    except (json.JSONDecodeError, ValueError):
        # Fallback: treat entire stdout as plain text, no cost data
        text = raw
        cost_usd = 0.0

    _usage_log.append({
        "stage": stage,
        "cost_usd": round(cost_usd, 6),
    })

    return text


def get_usage_log() -> list[dict]:
    return list(_usage_log)


def reset_usage_log():
    _usage_log.clear()
