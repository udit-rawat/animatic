"""
LLM client — five modes, priority order:

  1. Handoff  (manual Claude chat session via file-based pause)
     Set FORCE_PROVIDER=handoff. Writes prompt to a file, polls for output.

  2. Gemini API  (primary — up to 4 rotating keys)
     Set GEMINI_API_KEYS=key1,key2,key3,key4  (comma-separated)
     OR  GEMINI_API_KEY=key  (single key)
     Key rotation: exhausted keys are skipped automatically.
     All keys exhausted → falls back to OpenRouter.

  3. OpenRouter  (fallback — free models, per-stage routing)
     Set OPENROUTER_API_KEY in .env.

  4. Anthropic SDK  (CI / GitHub Actions)
     Set ANTHROPIC_API_KEY in .env or as a GitHub secret.

  5. Claude CLI  (last resort — broken inside an active Claude Code session)

Priority when FORCE_PROVIDER is not set:
  GEMINI_API_KEYS / GEMINI_API_KEY > OPENROUTER_API_KEY > ANTHROPIC_API_KEY > claude CLI

Per-stage Gemini model defaults (overridable via env):
  ranker   → gemini-2.5-flash   (fast reasoning, 250 RPD free)
  scripter → gemini-2.5-flash   (structured output, 250 RPD free)
  narrator → gemini-2.5-flash   (text rewrite, 250 RPD free)
  animator → gemini-2.5-pro     (code generation, best quality, 100 RPD free)
  TTS      → gemini-2.5-flash-preview-tts (audio output, always Gemini)
"""
import json
import os
import re
import subprocess
import time

from pipeline import logger as _logger_mod

# ── Model config ──────────────────────────────────────────────────────────────
CLAUDE_MODEL       = "claude-sonnet-4-6"
GEMINI_MODEL       = "gemini-2.5-flash"          # global fallback
DEFAULT_MAX_TOKENS = 4096

GEMINI_STAGE_DEFAULTS = {
    "ranker":   "gemini-2.5-flash",
    "scripter": "gemini-2.5-flash",
    "narrator": "gemini-2.5-flash",
    "animator": "gemini-2.5-pro",               # heaviest stage — best model
}

OPENROUTER_STAGE_DEFAULTS = {
    "ranker":   "meta-llama/llama-3.3-70b-instruct:free",
    "scripter": "meta-llama/llama-3.3-70b-instruct:free",
    "animator": "qwen/qwen3-coder:free",
}
OPENROUTER_FALLBACK = "meta-llama/llama-3.3-70b-instruct:free"

# Handoff file paths
_OUTPUT_DIR        = os.path.join(os.path.dirname(__file__), "..", "output")
_HANDOFF_PROMPT    = os.path.join(_OUTPUT_DIR, "handoff_{stage}_prompt.txt")
_HANDOFF_OUTPUT    = os.path.join(_OUTPUT_DIR, "handoff_{stage}_output.txt")
_HANDOFF_TIMEOUT   = 900   # 15 minutes


def _gemini_model_for(stage: str) -> str:
    if os.environ.get("GEMINI_MODEL"):
        return os.environ["GEMINI_MODEL"]
    stage_key = f"GEMINI_MODEL_{stage.upper()}"
    return os.environ.get(stage_key, GEMINI_STAGE_DEFAULTS.get(stage, GEMINI_MODEL))


def _openrouter_model_for(stage: str) -> str:
    if os.environ.get("OPENROUTER_MODEL"):
        return os.environ["OPENROUTER_MODEL"]
    stage_key = f"OPENROUTER_MODEL_{stage.upper()}"
    return os.environ.get(stage_key, OPENROUTER_STAGE_DEFAULTS.get(stage, OPENROUTER_FALLBACK))


def _get_all_gemini_keys() -> list[str]:
    """Return all configured Gemini API keys (supports both multi and single key)."""
    multi = os.environ.get("GEMINI_API_KEYS", "")
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]
    single = os.environ.get("GEMINI_API_KEY", "")
    return [single] if single else []


_usage_log: list[dict] = []


class _GeminiQuotaExhausted(Exception):
    """Raised when ALL configured Gemini keys are exhausted for today."""

class _GeminiRPMLimited(Exception):
    """Raised when a key exhausts all RPM retries — rotate to next key."""


# ── Mode 1: Handoff (manual Claude session) ───────────────────────────────────

def _call_handoff(prompt: str, stage: str) -> str:
    """
    Save the prompt to a file and wait for the user to drop the output file.

    Workflow:
      1. Pipeline writes  output/handoff_{stage}_prompt.txt
      2. User opens Claude Code, reads the file, generates output
      3. Claude (or user) writes output/handoff_{stage}_output.txt
      4. Pipeline resumes automatically
    """
    log = _logger_mod.get()
    os.makedirs(_OUTPUT_DIR, exist_ok=True)

    prompt_path = _HANDOFF_PROMPT.format(stage=stage)
    output_path = _HANDOFF_OUTPUT.format(stage=stage)

    # Write the prompt with instructions embedded at the top
    with open(prompt_path, "w") as f:
        f.write(f"# ═══ CLAUDE HANDOFF — {stage.upper()} STAGE ═══\n")
        f.write(f"# \n")
        f.write(f"# Instructions for Claude:\n")
        f.write(f"#   Read the prompt below and generate the output.\n")
        f.write(f"#   Write ONLY the raw output (no commentary) to:\n")
        f.write(f"#   {os.path.abspath(output_path)}\n")
        f.write(f"# \n")
        f.write(f"# ═══════════════════════════════════════════════\n\n")
        f.write(prompt)

    log.info(f"[{stage}] Handoff prompt saved — waiting for manual output")

    hop_mode = os.environ.get("HANDOFF_HOP_MODE") == "1"
    abs_output = os.path.abspath(output_path)
    abs_prompt = os.path.abspath(prompt_path)

    sep = "═" * 62
    print(f"\n╔{sep}╗")
    print(f"║  ⚡ HOP — {stage.upper()} stage paused")
    print(f"╠{sep}╣")
    print(f"║  1. Copy the prompt below into Claude chat:")
    print(f"║     cat \"{abs_prompt}\"")
    print(f"║")
    print(f"║  2. Once Claude gives you the code, run in a new terminal:")
    print(f"║     pbpaste > \"{abs_output}\"")
    print(f"║")
    print(f"║  Pipeline resumes automatically. No timeout.")
    print(f"╚{sep}╝\n")

    # Poll indefinitely in hop mode, respect timeout otherwise
    poll_interval = 5
    elapsed = 0
    while True:
        if os.path.exists(output_path) and os.path.getmtime(output_path) >= os.path.getmtime(prompt_path):
            with open(output_path) as f:
                content = f.read().strip()
            if content:
                log.info(f"[{stage}] Handoff output received — {len(content)} chars")
                print(f"\n✅ Handoff output received ({len(content)} chars) — resuming pipeline.\n")
                os.remove(prompt_path)
                _usage_log.append({"stage": stage, "mode": "handoff/claude", "cost_usd": 0.0})
                return content
        time.sleep(poll_interval)
        elapsed += poll_interval
        if not hop_mode and elapsed >= _HANDOFF_TIMEOUT:
            raise RuntimeError(
                f"[{stage}] Handoff timed out after {_HANDOFF_TIMEOUT//60} minutes. "
                f"Output not found: {output_path}"
            )
        if elapsed % 60 == 0:
            print(f"  ⏳ Still waiting... ({elapsed//60}m)  →  pbpaste > \"{abs_output}\"")


# ── Mode 2: Gemini API (with key rotation) ────────────────────────────────────

def _call_gemini_with_key(prompt: str, stage: str, max_tokens: int, api_key: str, json_mode: bool = False) -> str:
    """Single Gemini call using a specific API key. Raises _GeminiQuotaExhausted if this key is exhausted."""
    import urllib.request
    import urllib.error
    log = _logger_mod.get()
    model = _gemini_model_for(stage)
    key_id = api_key[-8:]
    log.debug(f"[{stage}] Gemini call — model: {model}, key: ...{key_id}, prompt: {len(prompt)} chars")
    t0 = time.time()

    gen_config: dict = {"maxOutputTokens": max_tokens}
    if json_mode:
        gen_config["responseMimeType"] = "application/json"
        # Disable thinking for simple JSON stages — thinking tokens count against
        # maxOutputTokens, leaving too little budget for the actual response.
        gen_config["thinkingConfig"] = {"thinkingBudget": 0}
    else:
        # For code-generation stages (animator): cap thinking at 2k tokens.
        # Higher budgets cause Gemini to take 5-10+ min per call (hangs urllib).
        gen_config["thinkingConfig"] = {"thinkingBudget": 2048}

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config,
    }).encode()

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    wait_times = [30, 60, 120]
    data = None
    for attempt, wait in enumerate(wait_times + [None], start=1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                body = e.read().decode("utf-8", errors="replace")
                if "free_tier_requests" in body:
                    log.warning(f"[{stage}] Gemini key ...{key_id} daily quota exhausted")
                    print(f"⚠️  Gemini key ...{key_id} exhausted — trying next key...")
                    try:
                        from pipeline import quota as _q
                        _q.mark_key_exhausted(api_key)
                    except Exception:
                        pass
                    raise _GeminiQuotaExhausted(body)
                if wait is not None:
                    log.warning(f"[{stage}] Gemini RPM limit (key ...{key_id}) — waiting {wait}s")
                    print(f"⏳ Gemini rate limited — waiting {wait}s...")
                    time.sleep(wait)
                else:
                    log.warning(f"[{stage}] Gemini key ...{key_id} RPM exhausted — rotating to next key")
                    print(f"⚠️  Gemini key ...{key_id} RPM exhausted — trying next key...")
                    raise _GeminiRPMLimited(body) from e
            else:
                body = e.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"[{stage}] Gemini HTTP {e.code}: {body[:400]}") from e

    # gemini-2.5-* thinking models return multiple parts:
    #   parts[0] = thought/reasoning (thought=True) — NOT the answer
    #   parts[1] = actual response text
    # Always pick the first non-thought part to get the real output.
    _parts = data["candidates"][0]["content"]["parts"]
    _output_parts = [p["text"] for p in _parts if not p.get("thought", False) and "text" in p]
    text = _output_parts[0] if _output_parts else _parts[0]["text"]
    usage = data.get("usageMetadata", {})
    input_tok  = usage.get("promptTokenCount", 0)
    output_tok = usage.get("candidatesTokenCount", 0)
    elapsed = round(time.time() - t0, 1)
    log.debug(f"[{stage}] Gemini success in {elapsed}s — key ...{key_id}, in:{input_tok} out:{output_tok}")
    _usage_log.append({
        "stage":        stage,
        "mode":         f"gemini/{model}/key...{key_id}",
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cost_usd":     0.0,
    })
    try:
        from pipeline import quota as _q
        _q.record_call(stage)
    except Exception:
        pass
    return text


def _call_gemini(prompt: str, stage: str, max_tokens: int, json_mode: bool = False) -> str:
    """
    Try each configured Gemini key in order.
    - Rotates to next key ONLY on daily quota exhaustion (_GeminiQuotaExhausted).
    - On RPM limit (_GeminiRPMLimited): waits 2 min and retries the SAME key once
      before rotating. This exhausts one key at a time rather than scattering load.
    """
    import time
    from pipeline import quota as _q
    log = _logger_mod.get()
    keys = _get_all_gemini_keys()
    if not keys:
        raise RuntimeError("No GEMINI_API_KEY or GEMINI_API_KEYS configured.")

    for key in keys:
        if _q.is_key_exhausted(key):
            continue
        try:
            return _call_gemini_with_key(prompt, stage, max_tokens, key, json_mode=json_mode)
        except _GeminiQuotaExhausted:
            continue   # daily limit hit — move to next key
        except _GeminiRPMLimited:
            # RPM limit after full backoff — wait 2 more minutes, retry same key once
            log.warning(f"[{stage}] RPM still exhausted on ...{key[-8:]} — waiting 2 min before one more attempt")
            print(f"⏳ RPM limit — waiting 2 min before retrying ...{key[-8:]}...")
            time.sleep(120)
            try:
                return _call_gemini_with_key(prompt, stage, max_tokens, key, json_mode=json_mode)
            except (_GeminiQuotaExhausted, _GeminiRPMLimited):
                log.warning(f"[{stage}] ...{key[-8:]} still failing after extra wait — rotating to next key")
                continue   # now rotate

    # All keys exhausted
    n = len(keys)
    _q.mark_exhausted()
    print(f"⚠️  All {n} Gemini key(s) exhausted/RPM-limited — falling back to OpenRouter...")
    raise _GeminiQuotaExhausted(f"All {n} configured Gemini keys are exhausted for today.")


# ── Mode 3: OpenRouter ────────────────────────────────────────────────────────

def _call_openrouter(prompt: str, stage: str, max_tokens: int, _model: str | None = None) -> str:
    import urllib.request
    import urllib.error
    log = _logger_mod.get()
    model = _model or _openrouter_model_for(stage)
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    wait_times = [30, 60, 120]
    for attempt, wait in enumerate(wait_times + [None], start=1):
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
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                if model != OPENROUTER_FALLBACK:
                    log.warning(f"[{stage}] OpenRouter 404 for '{model}' — retrying with {OPENROUTER_FALLBACK}")
                    print(f"⚠️  OpenRouter model not found ({model}) — switching to {OPENROUTER_FALLBACK}...")
                    return _call_openrouter(prompt, stage, max_tokens, _model=OPENROUTER_FALLBACK)
                err_body = e.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"[{stage}] OpenRouter 404 even for fallback model: {err_body[:200]}") from e
            elif e.code == 429 and wait is not None:
                log.warning(f"[{stage}] OpenRouter 429 — waiting {wait}s before retry {attempt+1}")
                print(f"⏳ Rate limited by OpenRouter — waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

    text      = data["choices"][0]["message"]["content"]
    usage     = data.get("usage", {})
    cost_usd  = float(data.get("usage", {}).get("cost", 0.0))
    _usage_log.append({
        "stage":         stage,
        "mode":          f"openrouter/{model}",
        "input_tokens":  usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "cost_usd":      round(cost_usd, 6),
    })
    return text


# ── Mode 4: Anthropic SDK ─────────────────────────────────────────────────────

def _call_sdk(prompt: str, stage: str, max_tokens: int) -> str:
    log = _logger_mod.get()
    log.debug(f"[{stage}] SDK call starting — prompt: {len(prompt)} chars")
    t0 = time.time()
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    usage    = response.usage
    elapsed  = round(time.time() - t0, 1)
    cost_usd = (usage.input_tokens * 3.00 + usage.output_tokens * 15.00) / 1_000_000
    log.debug(f"[{stage}] SDK success in {elapsed}s — in:{usage.input_tokens} out:{usage.output_tokens} ${cost_usd:.4f}")
    _usage_log.append({
        "stage":         stage,
        "mode":          "anthropic_sdk",
        "input_tokens":  usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd":      round(cost_usd, 6),
    })
    return response.content[0].text


# ── Mode 5: Claude CLI ────────────────────────────────────────────────────────
_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def kill_claude_processes() -> list[int]:
    import psutil
    killed = []
    current = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.pid == current:
                continue
            name    = (proc.info["name"] or "").lower()
            cmdline = " ".join(proc.info["cmdline"] or []).lower()
            if "claude" in name or ("claude" in cmdline and "-p" in cmdline):
                proc.kill()
                killed.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def _call_cli(prompt: str, stage: str) -> str:
    log = _logger_mod.get()
    log.debug(f"[{stage}] CLI call — detached, prompt: {len(prompt)} chars")
    t0 = time.time()

    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("CLAUDE")}
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=300,
            start_new_session=True, env=env,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"[{stage}] claude CLI timed out after 300s.")

    elapsed = round(time.time() - t0, 1)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "")[:400]
        log.error(f"[{stage}] CLI failed in {elapsed}s (exit {result.returncode})\n{err}")
        raise RuntimeError(f"[{stage}] claude CLI failed (exit {result.returncode}):\n{err}")

    raw = _ANSI_ESCAPE.sub("", result.stdout).strip()
    log.debug(f"[{stage}] CLI success in {elapsed}s — {len(raw)} chars")
    _usage_log.append({"stage": stage, "mode": "claude_cli", "cost_usd": 0.0})
    return raw


# ── Public interface ──────────────────────────────────────────────────────────

def get_mode() -> str:
    force = os.environ.get("FORCE_PROVIDER")
    if force == "handoff":
        return "handoff (manual Claude session)"
    if force == "claude":
        return f"claude_cli ({CLAUDE_MODEL})"
    if force == "anthropic":
        return f"anthropic_sdk ({CLAUDE_MODEL})"
    if force == "openrouter":
        if os.environ.get("OPENROUTER_MODEL"):
            return f"openrouter/all={os.environ['OPENROUTER_MODEL']}"
        return (
            f"openrouter/per-stage ("
            f"ranker={_openrouter_model_for('ranker')}, "
            f"scripter={_openrouter_model_for('scripter')}, "
            f"animator={_openrouter_model_for('animator')})"
        )
    keys = _get_all_gemini_keys()
    if force == "gemini" or keys:
        n = len(keys)
        key_info = f"{n} key(s)"
        if os.environ.get("GEMINI_MODEL"):
            return f"gemini/all={os.environ['GEMINI_MODEL']} [{key_info}]"
        return (
            f"gemini/per-stage [{key_info}] ("
            f"ranker={_gemini_model_for('ranker')}, "
            f"scripter={_gemini_model_for('scripter')}, "
            f"narrator={_gemini_model_for('narrator')}, "
            f"animator={_gemini_model_for('animator')})"
        )
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


def call(prompt: str, stage: str, max_tokens: int = DEFAULT_MAX_TOKENS, json_mode: bool = False) -> str:
    # Per-stage override takes priority over global provider
    # e.g. FORCE_PROVIDER_ANIMATOR=handoff lets you handoff just the animator
    force = os.environ.get(f"FORCE_PROVIDER_{stage.upper()}") or os.environ.get("FORCE_PROVIDER")

    if force == "handoff":
        return _call_handoff(prompt, stage)
    if force == "claude":
        return _call_cli(prompt, stage)
    if force == "openrouter":
        return _call_openrouter(prompt, stage, max_tokens)
    if force == "anthropic":
        return _call_sdk(prompt, stage, max_tokens)

    # Gemini with key rotation + OpenRouter fallback
    keys = _get_all_gemini_keys()
    if force == "gemini" or keys:
        try:
            return _call_gemini(prompt, stage, max_tokens, json_mode=json_mode)
        except _GeminiQuotaExhausted:
            if os.environ.get("OPENROUTER_API_KEY"):
                return _call_openrouter(prompt, stage, max_tokens)
            raise RuntimeError(
                f"[{stage}] All Gemini keys exhausted and no OPENROUTER_API_KEY fallback set."
            )

    if os.environ.get("OPENROUTER_API_KEY"):
        return _call_openrouter(prompt, stage, max_tokens)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_sdk(prompt, stage, max_tokens)
    return _call_cli(prompt, stage)


def get_usage_log() -> list[dict]:
    return list(_usage_log)


def reset_usage_log():
    _usage_log.clear()
