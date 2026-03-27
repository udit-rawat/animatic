import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

STAGES = ["scraper", "ranker", "scripter", "verifier", "scene_planner", "narrator", "param_extractor", "animator", "notifier"]


def apply_provider(provider: str, model: str | None):
    """
    Sets FORCE_PROVIDER env var so claude_client uses the right LLM backend.
    Does NOT pop GEMINI_API_KEY — narrator TTS always needs it regardless of provider.
    """
    if provider == "claude":
        os.environ["FORCE_PROVIDER"] = "claude"

    elif provider == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("[ERROR] --provider openrouter requires OPENROUTER_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "openrouter"

    elif provider == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            print("[ERROR] --provider gemini requires GEMINI_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "gemini"

    elif provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("[ERROR] --provider anthropic requires ANTHROPIC_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "anthropic"

    elif provider == "handoff":
        os.environ["FORCE_PROVIDER"] = "handoff"

    if model:
        os.environ["OPENROUTER_MODEL"] = model
        if provider != "openrouter":
            print(f"[WARN] --model flag only applies to OpenRouter mode, ignored for '{provider}'")


def _is_gemini_active() -> bool:
    force = os.environ.get("FORCE_PROVIDER")
    if force:
        return force == "gemini"
    return bool(os.environ.get("GEMINI_API_KEY"))


def run_stage(name: str):
    from pipeline.logger import get as get_log
    get_log().info(f"Stage START: {name}")
    print(f"\n--- Running: {name} ---")
    if name == "scraper":
        from pipeline.scraper import main
    elif name == "ranker":
        from pipeline.ranker import main
    elif name == "scripter":
        from pipeline.scripter import main
    elif name == "animator":
        from pipeline.animator import main
    elif name == "verifier":
        from pipeline.verifier import main
    elif name == "scene_planner":
        from pipeline.scene_planner import main
    elif name == "param_extractor":
        from pipeline.param_extractor import main
    elif name == "narrator":
        from pipeline.narrator import main
    elif name == "notifier":
        from pipeline.notifier import main
    else:
        raise ValueError(f"Unknown stage: {name}")
    main()


def main():
    parser = argparse.ArgumentParser(description="adamax-content-engine pipeline")
    parser.add_argument(
        "--stage",
        choices=STAGES,
        help="Run a single stage instead of the full pipeline",
    )
    parser.add_argument(
        "--provider",
        choices=["claude", "openrouter", "anthropic", "gemini", "handoff"],
        help=(
            "LLM provider to use. "
            "gemini = Gemini API, free tier (needs GEMINI_API_KEY). "
            "claude = Claude Code CLI session (default, no key needed). "
            "openrouter = free/cheap models via OpenRouter (needs OPENROUTER_API_KEY). "
            "anthropic = Anthropic SDK (needs ANTHROPIC_API_KEY)."
        ),
    )
    parser.add_argument(
        "--model",
        help=(
            "Override the OpenRouter model for all stages "
            "(e.g. deepseek/deepseek-r1:free). "
            "Only applies with --provider openrouter."
        ),
    )
    parser.add_argument(
        "--handoff-animator",
        action="store_true",
        help=(
            "Run the full pipeline with Gemini except the animator stage, "
            "which pauses and waits for you to paste the prompt into a Claude session."
        ),
    )
    parser.add_argument(
        "--hop",
        action="store_true",
        help=(
            "Run the full pipeline, pause at animator with NO timeout. "
            "Copy the prompt to Claude chat, get the code, then: pbpaste > output/handoff_animator_output.txt"
        ),
    )
    parser.add_argument(
        "--gemini",
        action="store_true",
        help=(
            "Run the full pipeline end-to-end on Gemini only. "
            "Uses gemini-2.5-flash-lite for all stages. "
            "No handoff, no OpenRouter, fully automated."
        ),
    )
    parser.add_argument(
        "--check-quota",
        action="store_true",
        help="Show Gemini daily quota status and exit (no pipeline run).",
    )
    parser.add_argument(
        "--rca",
        action="store_true",
        help="Show day-level run audit + root cause analysis for quota spend, then exit.",
    )
    args = parser.parse_args()

    if args.gemini:
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEYS")):
            print("[ERROR] --gemini requires GEMINI_API_KEY or GEMINI_API_KEYS in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "gemini"
        # Set stage-optimal models (overridable via .env)
        os.environ.setdefault("GEMINI_MODEL_RANKER",          "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_SCRIPTER",        "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_VERIFIER",         "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_SCENE_PLANNER",   "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_NARRATOR",        "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_PARAM_EXTRACTOR", "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_ANIMATOR",        "gemini-2.5-flash-lite")

    if args.provider:
        apply_provider(args.provider, args.model)

    if args.handoff_animator:
        os.environ["FORCE_PROVIDER_ANIMATOR"] = "handoff"

    if args.hop:
        os.environ["FORCE_PROVIDER_ANIMATOR"] = "handoff"
        os.environ["HANDOFF_HOP_MODE"] = "1"

    # ── Quota / RCA check ─────────────────────────────────────────────────────
    if args.check_quota:
        from pipeline.quota import print_status
        print_status(verbose=True)
        return

    if args.rca:
        from pipeline.quota import print_status, print_rca
        print_status(verbose=True)
        print_rca()
        return

    from pipeline.logger import setup as log_setup
    log = log_setup()

    from pipeline.claude_client import get_mode
    mode = get_mode()
    log.info(f"Pipeline starting — LLM mode: {mode}")
    print(f"\n🔧 LLM mode: {mode}\n")

    # Auto-print quota status before a Gemini full-pipeline run so the user
    # knows upfront if they're likely to hit the daily limit mid-run.
    if _is_gemini_active() and not args.stage:
        try:
            from pipeline.quota import print_status, get_status
            print_status(verbose=True)
            s = get_status()
            if not s["can_run_minimal"]:
                print("[ERROR] Gemini quota too low to attempt a full run.", file=sys.stderr)
                print("        Run with --provider openrouter as a fallback.", file=sys.stderr)
                sys.exit(1)
        except Exception:
            pass  # quota check is non-critical — never block the pipeline

    stages_to_run = [args.stage] if args.stage else STAGES
    run_type = args.stage if args.stage else "full"

    # Record run start (Gemini-only — other providers don't have quota concerns)
    run_id = None
    if _is_gemini_active():
        try:
            from pipeline.quota import start_run
            run_id = start_run(run_type)
        except Exception:
            pass

    failed_stage = None
    for stage in stages_to_run:
        try:
            run_stage(stage)
        except Exception as e:
            failed_stage = stage
            from pipeline.logger import get as get_log
            get_log().error(f"Stage FAILED: {stage} — {e}", exc_info=True)
            print(f"\n[ERROR] Stage '{stage}' failed: {e}", file=sys.stderr)
            if run_id is not None:
                try:
                    from pipeline.quota import end_run
                    end_run(run_id, outcome="failed", failed_stage=stage)
                except Exception:
                    pass
            sys.exit(1)

    if run_id is not None:
        try:
            from pipeline.quota import end_run
            end_run(run_id, outcome="success")
        except Exception:
            pass

    if not args.stage:
        try:
            from pipeline.auditor import build_report, print_report, save_report
            report = build_report()
            print_report(report)
            save_report(report)
        except Exception as e:
            print(f"[WARN] Audit failed: {e}", file=sys.stderr)

    print("\n✅ Pipeline complete.")


if __name__ == "__main__":
    main()
