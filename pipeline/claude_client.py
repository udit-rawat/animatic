"""
Claude client — three modes, auto-detected from environment:

  1. Claude CLI (default, local)
     No API keys needed. Uses `claude -p` subprocess via active Claude Code session.
     Set nothing — this is the fallback.

  2. OpenRouter (benchmark / free models)
     Set OPENROUTER_API_KEY in .env.
     Optionally set OPENROUTER_MODEL (default: deepseek/deepseek-chat:free)

  3. Anthropic SDK (GitHub Actions / CI)
     Set ANTHROPIC_API_KEY in .env or as a GitHub secret.

Priority: OpenRouter > Anthropic SDK > Claude CLI
All calls go through call() — pipeline stages are unaware of the mode.
"""
import json
import os
import subprocess

# ── Model config ──────────────────────────────────────────────────────────────
CLAUDE_MODEL       = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 8096

# Per-stage OpenRouter models — each picked for its strength.
# Override any via env vars (e.g. OPENROUTER_MODEL_ANIMATOR=qwen/qwen3-coder:free)
# OPENROUTER_MODEL overrides ALL stages (useful for quick full-pipeline benchmarks)
OPENROUTER_STAGE_DEFAULTS = {
    "ranker":   "deepseek/deepseek-r1:free",                  # best reasoning
    "scripter": "meta-llama/llama-3.3-70b-instruct:free",     # best creative writing
    "animator": "qwen/qwen3-coder:free",                       # best code gen
}
OPENROUTER_FALLBACK = "deepseek/deepseek-r1:free"


def _openrouter_model_for(stage: str) -> str:
    """Pick the right model for this stage, respecting env overrides."""
    if os.environ.get("OPENROUTER_MODEL"):          # single override for all stages
        return os.environ["OPENROUTER_MODEL"]
    stage_key = f"OPENROUTER_MODEL_{stage.upper()}"
    return os.environ.get(stage_key, OPENROUTER_STAGE_DEFAULTS.get(stage, OPENROUTER_FALLBACK))

_usage_log: list[dict] = []


# ── Mode 1: Claude CLI (local Claude Code session) ────────────────────────────

def _call_cli(prompt: str, stage: str) -> str:
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=180,   # 3 minutes max — hang protection
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"[{stage}] claude CLI timed out after 180s. "
            "Check your Claude Code session is active and retry."
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"[{stage}] claude CLI failed (exit {result.returncode}):\n{result.stderr}"
        )
    _usage_log.append({"stage": stage, "mode": "claude_cli", "cost_usd": 0.0})
    return result.stdout.strip()


# ── Mode 2: OpenRouter (free/cheap third-party models) ───────────────────────

def _call_openrouter(prompt: str, stage: str, max_tokens: int) -> str:
    import urllib.request
    model = _openrouter_model_for(stage)
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/udit-rawat/adamax-content-engine",
            "X-Title": "adamax-content-engine",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())

    text        = data["choices"][0]["message"]["content"]
    usage       = data.get("usage", {})
    input_tok   = usage.get("prompt_tokens", 0)
    output_tok  = usage.get("completion_tokens", 0)
    # OpenRouter returns cost in the response for paid models; free models = $0
    cost_usd    = float(data.get("usage", {}).get("cost", 0.0))

    _usage_log.append({
        "stage": stage,
        "mode": f"openrouter/{model}",
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cost_usd": round(cost_usd, 6),
    })
    return text


# ── Mode 3: Anthropic SDK (GitHub Actions / CI) ───────────────────────────────

def _call_sdk(prompt: str, stage: str, max_tokens: int) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    usage       = response.usage
    cost_usd    = (usage.input_tokens * 3.00 + usage.output_tokens * 15.00) / 1_000_000
    _usage_log.append({
        "stage": stage,
        "mode": "anthropic_sdk",
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": round(cost_usd, 6),
    })
    return response.content[0].text


# ── Public interface ──────────────────────────────────────────────────────────

def get_mode() -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        if os.environ.get("OPENROUTER_MODEL"):
            return f"openrouter/all={os.environ['OPENROUTER_MODEL']}"
        return (
            f"openrouter/per-stage ("
            f"ranker={_openrouter_model_for('ranker')}, "
            f"scripter={_openrouter_model_for('scripter')}, "
            f"animator={_openrouter_model_for('animator')})"
        )
    if os.environ.get("ANTHROPIC_API_KEY"):
        return f"anthropic_sdk ({CLAUDE_MODEL})"
    return f"claude_cli ({CLAUDE_MODEL})"


def call(prompt: str, stage: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return _call_openrouter(prompt, stage, max_tokens)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_sdk(prompt, stage, max_tokens)
    return _call_cli(prompt, stage)


def get_usage_log() -> list[dict]:
    return list(_usage_log)


def reset_usage_log():
    _usage_log.clear()
