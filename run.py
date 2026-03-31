import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

STAGES = ["scraper", "ranker", "scripter", "verifier", "scene_planner", "narrator", "word_aligner", "param_extractor", "animator", "notifier"]

# Single-shot pipeline: replaces scripter+verifier+scene_planner+param_extractor
# with one Pydantic-validated call. Activate with --single-shot.
STAGES_SINGLE_SHOT = ["scraper", "ranker", "content_generator", "narrator", "word_aligner", "animator", "notifier"]

# Custom pipeline: skips scraper+ranker entirely — topic comes from CLI.
STAGES_CUSTOM = ["content_generator", "narrator", "word_aligner", "animator", "notifier"]

OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")
TOPIC_PATH  = os.path.join(OUTPUT_DIR, "topic.json")
SCRIPT_PATH = os.path.join(OUTPUT_DIR, "script.json")
PARAMS_PATH = os.path.join(OUTPUT_DIR, "params.json")


def apply_provider(provider: str, model: str | None):
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


def _write_custom_topic(title: str, summary: str):
    """Write a topic.json from CLI args, bypassing scraper + ranker."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    topic = {
        "title":      title,
        "summary":    summary,
        "source":     "custom",
        "why_picked": "Provided via --custom flag.",
    }
    with open(TOPIC_PATH, "w") as f:
        json.dump(topic, f, indent=2)
    print(f"[custom] topic.json written → {title}")


def _intervention_checkpoint() -> bool:
    """
    Print script + beat layout plan, ask user to confirm before TTS + render.
    Returns True to continue, False to abort.
    """
    print("\n" + "═" * 60)
    print("  INTERVENTION CHECKPOINT")
    print("═" * 60)

    # Topic
    if os.path.exists(TOPIC_PATH):
        with open(TOPIC_PATH) as f:
            topic = json.load(f)
        print(f"\n  TOPIC : {topic.get('title', '?')}\n")

    # Narration
    spoken_path = os.path.join(OUTPUT_DIR, "spoken_narration.json")
    script_path = SCRIPT_PATH
    if os.path.exists(spoken_path):
        with open(spoken_path) as f:
            spoken = json.load(f)
        print("  NARRATION:")
        for key, text in spoken.items():
            label = key.upper().replace("_", " ")
            # word-wrap at 56 chars
            words, line, lines = text.split(), "", []
            for w in words:
                if len(line) + len(w) + 1 > 56:
                    lines.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                lines.append(line)
            print(f"    [{label}]")
            for l in lines:
                print(f"      {l}")
            print()
    elif os.path.exists(script_path):
        with open(script_path) as f:
            script = json.load(f)
        print(f"  HOOK    : {script.get('hook', '')}")
        for i, b in enumerate(script.get("concept_bullets", []), 1):
            print(f"  BULLET {i}: {b}")
        print(f"  TAKEAWAY: {script.get('takeaway', '')}\n")

    # Beat layouts
    if os.path.exists(PARAMS_PATH):
        with open(PARAMS_PATH) as f:
            params = json.load(f)
        print("  BEAT LAYOUTS:")
        for beat_key in sorted(params):
            d = params[beat_key].get("data", {})
            layout = d.get("layout", "?")
            label  = d.get("section_label", "")
            extra  = ""
            if layout == "MetricFocus":
                hero = d.get("hero", {})
                extra = f"  hero={hero.get('value','?')} {hero.get('label','')}"
            elif layout == "PipelineFlow":
                steps = d.get("steps", [])
                extra = f"  steps={len(steps)} dir={d.get('flow_direction','?')}"
            elif layout == "ComparisonSplit":
                lh = d.get("left",  {}).get("heading", "?")
                rh = d.get("right", {}).get("heading", "?")
                extra = f"  {lh} vs {rh}"
            elif layout == "TakeawayScene":
                extra = f"  \"{d.get('headline', '')[:50]}\""
            print(f"    {beat_key}: {layout} [{label}]{extra}")

    print("\n" + "═" * 60)
    try:
        ans = input("  Continue to TTS + render? [y/n] → ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    print("═" * 60 + "\n")
    return ans == "y"


def run_stage(name: str):
    from pipeline.logger import get as get_log
    get_log().info(f"Stage START: {name}")
    print(f"\n--- Running: {name} ---")
    if name == "scraper":
        from pipeline.scraper import main
    elif name == "ranker":
        from pipeline.ranker import main
    elif name == "content_generator":
        from pipeline.content_generator import main
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
    elif name == "word_aligner":
        from pipeline.word_aligner import main
    elif name == "notifier":
        from pipeline.notifier import main
    else:
        raise ValueError(f"Unknown stage: {name}")
    main()


def main():
    parser = argparse.ArgumentParser(description="adamax-content-engine pipeline")
    parser.add_argument("--stage", choices=STAGES, help="Run a single stage")
    parser.add_argument(
        "--provider",
        choices=["claude", "openrouter", "anthropic", "gemini", "handoff"],
    )
    parser.add_argument("--model", help="Override OpenRouter model for all stages")
    parser.add_argument("--handoff-animator", action="store_true")
    parser.add_argument("--hop", action="store_true")
    parser.add_argument("--single-shot", action="store_true")
    parser.add_argument(
        "--gemini", action="store_true",
        help="Run full pipeline on Gemini only (gemini-2.5-flash-lite).",
    )
    parser.add_argument("--check-quota", action="store_true")
    parser.add_argument("--rca", action="store_true")
    parser.add_argument("--log-stats",  action="store_true",
                        help="Log performance stats for the last posted video.")
    parser.add_argument("--analytics",  action="store_true",
                        help="Print analytics summary table.")

    # ── Custom content path ───────────────────────────────────────────────────
    parser.add_argument(
        "--custom", action="store_true",
        help=(
            "Skip scraper + ranker. Provide topic via --title and --summary. "
            "Runs single-shot content_generator directly."
        ),
    )
    parser.add_argument("--title",   default="", help="Topic title (required with --custom)")
    parser.add_argument("--summary", default="", help="Topic summary or context (used with --custom)")

    # ── Intervention checkpoint ───────────────────────────────────────────────
    parser.add_argument(
        "--checkpoint", action="store_true",
        help=(
            "Pause after content generation, print script + beat layout plan, "
            "and ask for confirmation before TTS + render."
        ),
    )

    args = parser.parse_args()

    if args.gemini:
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEYS")):
            print("[ERROR] --gemini requires GEMINI_API_KEY or GEMINI_API_KEYS in .env", file=sys.stderr)
            sys.exit(1)
        os.environ["FORCE_PROVIDER"] = "gemini"
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

    if args.check_quota:
        from pipeline.quota import print_status
        print_status(verbose=True)
        return

    if args.rca:
        from pipeline.quota import print_status, print_rca
        print_status(verbose=True)
        print_rca()
        return

    if args.log_stats:
        from pipeline.analytics import log_stats_interactive
        log_stats_interactive()
        return

    if args.analytics:
        from pipeline.analytics import print_summary
        print_summary()
        return

    # ── Custom mode: validate + write topic.json ──────────────────────────────
    if args.custom:
        if not args.title:
            print("[ERROR] --custom requires --title", file=sys.stderr)
            sys.exit(1)
        _write_custom_topic(args.title, args.summary)
        os.environ["PIPELINE_MODE"] = "single_shot"

    from pipeline.logger import setup as log_setup
    log = log_setup()

    from pipeline.claude_client import get_mode
    mode = get_mode()
    log.info(f"Pipeline starting — LLM mode: {mode}")
    print(f"\n🔧 LLM mode: {mode}\n")

    if _is_gemini_active() and not args.stage:
        try:
            from pipeline.quota import print_status, get_status
            print_status(verbose=True)
            s = get_status()
            if not s["can_run_minimal"]:
                print("[ERROR] Gemini quota too low to attempt a full run.", file=sys.stderr)
                sys.exit(1)
        except Exception:
            pass

    if getattr(args, "single_shot", False):
        os.environ["PIPELINE_MODE"] = "single_shot"

    # ── Stage selection ───────────────────────────────────────────────────────
    if args.stage:
        stages_to_run = [args.stage]
    elif args.custom:
        stages_to_run = STAGES_CUSTOM
    elif getattr(args, "single_shot", False):
        stages_to_run = STAGES_SINGLE_SHOT
    else:
        stages_to_run = STAGES
    run_type = args.stage if args.stage else "full"

    # Checkpoint fires after content generation, before TTS + render.
    # Content stages = everything up to and including content_generator /
    # param_extractor. Post-content stages = narrator onwards.
    POST_CONTENT = {"narrator", "word_aligner", "animator", "notifier"}
    checkpoint_needed = args.checkpoint and not args.stage

    run_id = None
    if _is_gemini_active():
        try:
            from pipeline.quota import start_run
            run_id = start_run(run_type)
        except Exception:
            pass

    failed_stage = None
    for stage in stages_to_run:

        # ── Intervention checkpoint ───────────────────────────────────────────
        if checkpoint_needed and stage == "narrator":
            if not _intervention_checkpoint():
                print("\n[checkpoint] Aborted by user — TTS + render skipped.")
                if run_id is not None:
                    try:
                        from pipeline.quota import end_run
                        end_run(run_id, outcome="aborted", failed_stage="checkpoint")
                    except Exception:
                        pass
                return

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
