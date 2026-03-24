"""
Gemini daily quota tracker + day-level run auditor.

Persists to output/gemini_quota.json. Resets automatically each calendar day.

Free tier limit: 20 RPD (requests per day) per model.

Quota cost per stage:
  scraper   — 0  (no LLM)
  ranker    — 1
  scripter  — 1
  animator  — 1–3  (up to MAX_RETRIES=3 on Manim errors)
  narrator  — 1
  mixer     — 0  (no LLM)
  notifier  — 0  (no LLM)
  ─────────────────────────
  minimal   — 3  (ranker + scripter + animator×1, no narrator)
  typical   — 5  (+ 1 animator retry + narrator)
  worst     — 6  (all 3 animator retries + narrator)

Hidden quota drains to watch for:
  - RPM backoff retries (429 rate-limit) still count against daily RPD quota
  - Running the full pipeline more than once per day doubles all costs
  - Each animator retry = 1 extra quota call, regardless of whether it renders
"""
import json
import os
from datetime import date, datetime

QUOTA_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "gemini_quota.json")

DAILY_LIMIT_PER_KEY  = 20   # Google free tier: 20 RPD per API key
CALLS_MINIMAL_RUN    = 3
CALLS_TYPICAL_RUN    = 5
CALLS_WORST_RUN      = 6


def _effective_limit() -> int:
    """Total daily limit across all configured Gemini keys."""
    try:
        from pipeline.claude_client import _get_all_gemini_keys
        n = len(_get_all_gemini_keys())
    except Exception:
        n = 1
    return max(n, 1) * DAILY_LIMIT_PER_KEY


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _load() -> dict:
    today = date.today().isoformat()
    if os.path.exists(QUOTA_PATH):
        try:
            with open(QUOTA_PATH) as f:
                data = json.load(f)
            if data.get("date") == today:
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {"date": today, "calls": 0, "by_stage": {}, "runs": []}


def _save(data: dict):
    os.makedirs(os.path.dirname(os.path.abspath(QUOTA_PATH)), exist_ok=True)
    with open(QUOTA_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Call tracking ─────────────────────────────────────────────────────────────

def record_call(stage: str):
    """Increment daily call count after each successful Gemini API request."""
    data = _load()
    data["calls"] += 1
    data["by_stage"][stage] = data["by_stage"].get(stage, 0) + 1
    _save(data)


def mark_exhausted():
    """Called when ALL keys are exhausted for the day."""
    data = _load()
    data["calls"] = _effective_limit()
    data["exhausted"] = True
    _save(data)


# ── Per-key rotation tracking ─────────────────────────────────────────────────

def _key_id(key: str) -> str:
    """Safe identifier — last 8 chars only, never stores the full key."""
    return key.strip()[-8:] if key else "unknown"


def mark_key_exhausted(key: str):
    """Mark a specific Gemini key as exhausted for today."""
    data = _load()
    kid = _key_id(key)
    if "exhausted_keys" not in data:
        data["exhausted_keys"] = []
    if kid not in data["exhausted_keys"]:
        data["exhausted_keys"].append(kid)
    _save(data)


def is_key_exhausted(key: str) -> bool:
    """Return True if this key is already known to be exhausted today."""
    return _key_id(key) in _load().get("exhausted_keys", [])


# ── Run-level auditing ────────────────────────────────────────────────────────

def start_run(run_type: str) -> int:
    """
    Record the start of a pipeline run. Returns a run_id for use with end_run().
    run_type: 'full' or a stage name like 'animator'.
    """
    data = _load()
    if "runs" not in data:
        data["runs"] = []
    run_id = len(data["runs"]) + 1
    data["runs"].append({
        "run":          run_id,
        "type":         run_type,
        "started":      _now_str(),
        "calls_before": data["calls"],
        "outcome":      "in_progress",
    })
    _save(data)
    return run_id


def end_run(run_id: int, outcome: str, failed_stage: str | None = None):
    """
    Record the outcome of a pipeline run.
    outcome: 'success' | 'failed' | 'aborted'
    failed_stage: stage name if outcome is 'failed'
    """
    data = _load()
    for run in data.get("runs", []):
        if run["run"] == run_id:
            run["ended"]       = _now_str()
            run["calls_after"] = data["calls"]
            run["calls_used"]  = data["calls"] - run["calls_before"]
            run["outcome"]     = outcome
            if failed_stage:
                run["failed_stage"] = failed_stage
            break
    _save(data)


# ── Status & reporting ────────────────────────────────────────────────────────

def get_status() -> dict:
    data = _load()
    used      = data["calls"]
    limit     = _effective_limit()
    exhausted_keys = data.get("exhausted_keys", [])
    # Re-derive all_exhausted from current key list — stored flag goes stale when
    # new keys are added after the flag was set.
    try:
        from pipeline.claude_client import _get_all_gemini_keys
        all_keys      = _get_all_gemini_keys()
        non_exhausted = [k for k in all_keys if _key_id(k) not in exhausted_keys]
        all_exhausted = len(all_keys) > 0 and len(non_exhausted) == 0
    except Exception:
        all_exhausted = data.get("exhausted", False)
    remaining = 0 if all_exhausted else max(0, limit - used)
    return {
        "date":             data["date"],
        "used":             used,
        "limit":            limit,
        "limit_per_key":    DAILY_LIMIT_PER_KEY,
        "remaining":        remaining,
        "exhausted":        all_exhausted,
        "exhausted_keys":   exhausted_keys,
        "keys_exhausted":   len(exhausted_keys),
        "by_stage":         data.get("by_stage", {}),
        "runs":             data.get("runs", []),
        "can_run_minimal":  remaining >= CALLS_MINIMAL_RUN,
        "can_run_typical":  remaining >= CALLS_TYPICAL_RUN,
        "runs_possible":    remaining // CALLS_TYPICAL_RUN,
    }


def print_status(verbose: bool = True):
    s = get_status()
    filled = round((s["used"] / s["limit"]) * 20) if s["limit"] else 0
    bar    = "█" * filled + "░" * (20 - filled)

    try:
        from pipeline.claude_client import _get_all_gemini_keys
        from pipeline.quota import _key_id
        keys   = _get_all_gemini_keys()
        n_keys = len(keys)
    except Exception:
        keys   = []
        n_keys = 1

    print(f"\n📊 Gemini Daily Quota  [{s['date']}]  [{n_keys} key(s) × {s['limit_per_key']} RPD = {s['limit']} total]")
    print(f"   [{bar}]  {s['used']}/{s['limit']} calls used  |  {s['remaining']} remaining")

    # Per-key status
    if verbose and keys:
        exhausted_ids = set(s.get("exhausted_keys", []))
        for i, k in enumerate(keys, 1):
            kid    = _key_id(k)
            status = "exhausted" if kid in exhausted_ids else "OK"
            icon   = "❌" if kid in exhausted_ids else "✅"
            print(f"   {icon} Key {i} (...{kid}): {status}")

    if verbose and s["by_stage"]:
        stage_parts = "  ".join(f"{k}:{v}" for k, v in sorted(s["by_stage"].items()))
        print(f"   By stage → {stage_parts}")

    if s["remaining"] == 0:
        tag = " (all keys exhausted)" if s["exhausted"] else ""
        print(f"   ❌ Quota exhausted{tag} — resets tomorrow")
        print( "   → Fallback: python3 run.py --provider openrouter")
    elif not s["can_run_minimal"]:
        print(f"   ⚠️  Only {s['remaining']} call(s) left — not enough for a full run (need {CALLS_MINIMAL_RUN}+)")
        print( "   → Fallback: python3 run.py --provider openrouter")
    elif not s["can_run_typical"]:
        print(f"   ⚠️  {s['remaining']} calls left — enough for 1 minimal run (no retries/narrator)")
        print( "   → Tip: if animator fails, switch to --provider openrouter")
    else:
        print(f"   ✅ Quota OK — ~{s['runs_possible']} full run(s) possible today")
    print()


def print_rca():
    """Print a day-level run audit + root cause analysis."""
    s = get_status()
    runs = s["runs"]

    print(f"\n🔍 Gemini Quota RCA  [{s['date']}]")
    print(f"   Total calls used: {s['used']}/{s['limit']}")
    print()

    if not runs:
        print("   No run data recorded today (runs started before auditing was installed).")
        print("   Future runs will be tracked automatically.\n")
        return

    # Per-run table
    print(f"   {'#':<4} {'Time':>8}  {'Type':<12} {'Calls':>6}  {'Outcome':<10}  {'Note'}")
    print(f"   {'─'*4} {'─'*8}  {'─'*12} {'─'*6}  {'─'*10}  {'─'*30}")
    total_calls = 0
    for r in runs:
        calls   = r.get("calls_used", "?")
        outcome = r.get("outcome", "?")
        note    = ""
        if outcome == "failed":
            note = f"failed at {r.get('failed_stage', '?')}"
        elif outcome == "success":
            note = "video delivered ✅"
        elif outcome == "in_progress":
            note = "still running / crashed"
        icon = {"success": "✅", "failed": "❌", "aborted": "⚠️", "in_progress": "🔄"}.get(outcome, "?")
        started = r.get("started", "?")
        print(f"   {r['run']:<4} {started:>8}  {r['type']:<12} {str(calls):>6}  {icon} {outcome:<8}  {note}")
        if isinstance(calls, int):
            total_calls += calls
    print(f"   {'─'*4} {'─'*8}  {'─'*12} {'─'*6}  {'─'*10}")
    print(f"   {'':4} {'':8}  {'TRACKED':12} {total_calls:>6}")

    untracked = s["used"] - total_calls
    if untracked > 0:
        print(f"   {'':4} {'':8}  {'UNTRACKED':12} {untracked:>6}  (calls before auditing was installed)")

    # Root cause flags
    print()
    print("   📌 Root Cause Flags:")
    flags = []

    # Flag: multiple successful full runs in one day
    success_full = [r for r in runs if r.get("outcome") == "success" and r.get("type") == "full"]
    if len(success_full) >= 2:
        flags.append(
            f"DUPLICATE RUNS: {len(success_full)} full pipeline runs completed today "
            f"(×{len(success_full)} quota multiplier). Pipeline is intended to run once/day."
        )

    # Flag: failed runs that still burned quota
    failed_runs = [r for r in runs if r.get("outcome") == "failed"]
    wasted = sum(r.get("calls_used", 0) for r in failed_runs)
    if wasted > 0:
        stages = [r.get("failed_stage", "?") for r in failed_runs]
        flags.append(
            f"FAILED RUNS BURNED {wasted} CALL(S): "
            + ", ".join(f"run#{r['run']} failed at {r.get('failed_stage','?')} "
                        f"({r.get('calls_used',0)} calls)" for r in failed_runs)
        )

    # Flag: animator retries
    anim_calls = s["by_stage"].get("animator", 0)
    anim_runs  = sum(1 for r in runs if "animator" in r.get("type", "") or r.get("type") == "full")
    if anim_calls > anim_runs:
        flags.append(
            f"ANIMATOR RETRIES: {anim_calls} animator calls across ~{anim_runs} run(s) "
            f"→ ~{anim_calls - anim_runs} extra call(s) from Manim code errors."
        )

    if not flags:
        flags.append("No unusual patterns detected.")

    for flag in flags:
        print(f"   • {flag}")

    print()
    print("   💡 Recommendations:")
    recs = [
        "Run the pipeline once per day — use GitHub Actions on a schedule to enforce this.",
        "When animator fails on retry 1, switch to --provider openrouter for remaining retries.",
        "Use --check-quota before starting a debug/manual run to verify you have headroom.",
    ]
    for rec in recs:
        print(f"   → {rec}")
    print()
