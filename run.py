import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

STAGES = ["scraper", "ranker", "scripter", "animator", "notifier"]


def run_stage(name: str):
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
    args = parser.parse_args()

    stages_to_run = [args.stage] if args.stage else STAGES

    for stage in stages_to_run:
        try:
            run_stage(stage)
        except Exception as e:
            print(f"\n[ERROR] Stage '{stage}' failed: {e}", file=sys.stderr)
            sys.exit(1)

    # Print token audit after full pipeline run (skip for single-stage invocations
    # so the output stays clean during development)
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
