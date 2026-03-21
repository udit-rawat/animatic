"""
Shared Anthropic SDK wrapper.
Routes all Claude calls through one place so token usage is tracked
across the entire pipeline run and reported by the auditor.
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8096

# Sonnet 4.6 pricing (USD per million tokens)
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00

_client: Anthropic | None = None
_usage_log: list[dict] = []


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment / .env")
        _client = Anthropic(api_key=api_key)
    return _client


def call(prompt: str, stage: str, max_tokens: int = MAX_TOKENS) -> str:
    """
    Send a single-turn prompt to Claude and return the text response.
    Token usage is recorded against the given stage name.
    """
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    usage = response.usage
    input_tok = usage.input_tokens
    output_tok = usage.output_tokens
    cost = (input_tok * INPUT_COST_PER_M / 1_000_000) + (output_tok * OUTPUT_COST_PER_M / 1_000_000)

    _usage_log.append({
        "stage": stage,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cost_usd": round(cost, 6),
    })

    return response.content[0].text


def get_usage_log() -> list[dict]:
    return list(_usage_log)


def reset_usage_log():
    _usage_log.clear()
