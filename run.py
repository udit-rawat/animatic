import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

STAGES = ["scraper", "ranker", "scripter", "animator", "notifier"]


def apply_provider(provider: str, model: str | None):
    """
    Override LLM provider via CLI flag instead of editing .env.
    Manipulates env vars so claude_client auto-detection picks the right mode.
    """
    if provider == "claude":
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)

    elif provider == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("[ERROR] --provider openrouter requires OPENROUTER_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ.pop("ANTHROPIC_API_KEY", None)   # ensure OpenRouter wins priority

    elif provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("[ERROR] --provider anthropic requires ANTHROPIC_API_KEY in .env", file=sys.stderr)
            sys.exit(1)
        os.environ.pop("OPENROUTER_API_KEY", None)  # ensure Anthropic wins priority

    if model:
        # Overrides all per-stage model vars — useful for single-model benchmarks
        os.environ["OPENROUTER_MODEL"] = model
        if provider != "openrouter":
            print(f"[WARN] --model flag only applies to OpenRouter mode, ignored for '{provider}'")


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
        choices=["claude", "openrouter", "anthropic"],
        help=(
            "LLM provider to use. "
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
    args = parser.parse_args()

    if args.provider:
        apply_provider(args.provider, args.model)

    from pipeline.logger import setup as log_setup
    log = log_setup()

    from pipeline.claude_client import get_mode
    mode = get_mode()
    log.info(f"Pipeline starting — LLM mode: {mode}")
    print(f"\n🔧 LLM mode: {mode}\n")

    stages_to_run = [args.stage] if args.stage else STAGES

    for stage in stages_to_run:
        try:
            run_stage(stage)
        except Exception as e:
            from pipeline.logger import get as get_log
            get_log().error(f"Stage FAILED: {stage} — {e}", exc_info=True)
            print(f"\n[ERROR] Stage '{stage}' failed: {e}", file=sys.stderr)
            sys.exit(1)

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
