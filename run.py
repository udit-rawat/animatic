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
STAGES_CUSTOM = ["content_generator", "narrator", "word_aligner", "brief_generator", "animator", "notifier"]

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


def _narration_preview_pause():
    """
    Show the final spoken_narration.json that will go to TTS.
    User must confirm before narrator runs. Abort = Ctrl+C.
    """
    narration_path = os.path.join(OUTPUT_DIR, "spoken_narration.json")
    if not os.path.exists(narration_path):
        return

    with open(narration_path) as f:
        narration = json.load(f)

    print("\n" + "═" * 70)
    print("  📢  NARRATION REVIEW  —  this is the exact script going to TTS")
    print("═" * 70)
    for seg in ["hook", "concept_1", "concept_2", "takeaway_cta"]:
        text = narration.get(seg, "")
        if text:
            print(f"\n  [{seg}]")
            print(f"  \"{text}\"")
    print("\n" + "═" * 70)
    print("  Review the script above. If it looks good, press Enter to continue.")
    print("  To abort and edit, press Ctrl+C.\n")

    try:
        input("  Continue to TTS → ")
    except (EOFError, KeyboardInterrupt):
        print("\n[narration] Aborted — edit spoken_narration.json and re-run with --stage narrator")
        sys.exit(0)


def _print_veo2_prompts(topic_title: str, narration_data: dict, timing_data: dict) -> None:
    """
    Read params.json for animation_hook beats and print one Veo2 video prompt per beat.
    Also saves to output/veo2_prompts.txt for Telegram delivery.
    """
    params_path = os.path.join(OUTPUT_DIR, "params.json")
    if not os.path.exists(params_path):
        return
    with open(params_path) as f:
        params = json.load(f)

    beats = params.get("beats", [])
    scenes = params.get("scenes", {})
    hook_beats = []
    for beat in beats:
        bid  = f"beat_{beat['beat']}"
        scene = scenes.get(bid, {})
        if scene.get("template_variant") == "animation_hook":
            narr  = narration_data.get(
                ["hook", "concept_1", "concept_2", "takeaway_cta"][beat["beat"] - 1], ""
            )
            timing = timing_data.get(
                ["hook", "concept_1", "concept_2", "takeaway_cta"][beat["beat"] - 1], {}
            )
            dur = timing.get("duration", 6.0)
            hook_beats.append((bid, scene, narr, round(dur)))

    if not hook_beats:
        return

    prompts = []
    print("\n" + "═" * 70)
    print("  🎬  VEO2 PROMPTS — generate these animation clips")
    print("═" * 70)
    for bid, scene, narr, dur in hook_beats:
        layout = scene.get("data", {}).get("layout", "unknown")
        prompt = (
            f"Portrait video, 1080x1920, {dur} seconds, black background, no text, no UI.\n"
            f"Topic: {topic_title}\n"
            f"Scene: {layout} beat — visually represents \"{narr}\"\n"
            f"Style: dark cinematic, neon cyan accent #00E5FF, technical/sci-fi aesthetic. "
            f"Slow camera push-in. Ambient particle drift. No cuts. Loop-friendly ending."
        )
        prompts.append(f"[{bid}]\n{prompt}")
        print(f"\n  [{bid}]")
        print(f"  {prompt}\n")
    print("═" * 70 + "\n")

    # Save for notifier to pick up
    veo2_path = os.path.join(OUTPUT_DIR, "veo2_prompts.txt")
    with open(veo2_path, "w") as f:
        f.write(f"🎬 Veo2 prompts — {topic_title}\n\n")
        f.write("\n\n---\n\n".join(prompts))


def _compositor_pause() -> str:
    """
    Pause pipeline before animator. Print all context file paths so the user
    can feed them to Claude and generate a custom CustomVideo.tsx.
    Returns the path where the file must be dropped.
    """
    import re as _re
    from datetime import date as _date

    # Build slug from topic title
    topic_title = "video"
    if os.path.exists(TOPIC_PATH):
        with open(TOPIC_PATH) as f:
            topic_title = json.load(f).get("title", "video")
    slug = _re.sub(r"[^a-z0-9]+", "-", topic_title.lower()).strip("-")[:40]
    today = _date.today().isoformat()
    comp_dir  = os.path.join(OUTPUT_DIR, "compositions", f"{today}_{slug}")
    drop_path = os.path.join(comp_dir, "CustomVideo.tsx")
    os.makedirs(comp_dir, exist_ok=True)

    # ── Load narration + timing for inline display ───────────────────────────
    narration_path = os.path.join(OUTPUT_DIR, "spoken_narration.json")
    timing_path    = os.path.join(OUTPUT_DIR, "narration_timing.json")
    narration_data = {}
    timing_data    = {}
    if os.path.exists(narration_path):
        with open(narration_path) as f:
            narration_data = json.load(f)
    if os.path.exists(timing_path):
        with open(timing_path) as f:
            timing_data = json.load(f)

    total_dur = max(
        (v.get("end", 0) for v in timing_data.values()), default=0
    ) if timing_data else 0

    print("\n" + "═" * 70)
    print("  ⏸  COMPOSITOR PAUSE  —  generate a custom CustomVideo.tsx")
    print("═" * 70)
    print(f"\n  TOPIC: {topic_title}")
    print(f"  DURATION: {total_dur:.1f}s\n")

    if narration_data:
        print("  NARRATION + TIMING")
        print("  ─────────────────────────────────────────────────────────────")
        segment_order = ["hook", "concept_1", "concept_2", "takeaway_cta"]
        for seg in segment_order:
            text   = narration_data.get(seg, "")
            timing = timing_data.get(seg, {})
            if not text:
                continue
            start  = timing.get("start", 0)
            end    = timing.get("end", start + timing.get("duration", 0))
            s_from = round(start * 30)
            s_to   = round(end   * 30)
            print(f"\n  [{seg}]  frames {s_from}–{s_to}  ({start:.1f}s – {end:.1f}s)")
            print(f"  \"{text}\"")
        print()

    print("  ─────────────────────────────────────────────────────────────")

    # Use drop_path written by brief_generator if available
    drop_path_file = os.path.join(OUTPUT_DIR, "drop_path.txt")
    if os.path.exists(drop_path_file):
        with open(drop_path_file) as f:
            drop_path = f.read().strip()
        os.makedirs(os.path.dirname(drop_path), exist_ok=True)

    # Print full compositor_prompt.md inline if brief_generator already ran
    prompt_path = os.path.join(OUTPUT_DIR, "compositor_prompt.md")
    if os.path.exists(prompt_path):
        print("\n" + "═" * 70)
        print("  ANIMATION BRIEF — paste everything below into your Claude session:")
        print("═" * 70 + "\n")
        with open(prompt_path) as f:
            print(f.read())
        print("═" * 70)
        print(f"\n  Full brief also at: {os.path.join(OUTPUT_DIR, 'animation_brief.json')}")
        print(f"\n  DROP FILE HERE:  {drop_path}\n")

        # ── Veo2 prompts for animation_hook beats ────────────────────────────
        _print_veo2_prompts(topic_title, narration_data, timing_data)
    else:
        print("  Prompt Claude with the TOPIC + NARRATION above to generate")
        print("  a self-contained CustomVideo.tsx (no props, all data hardcoded).")
        print(f"\n  Drop the file here when ready:")
        print(f"\n    {drop_path}\n")
        print("═" * 70)

    try:
        input("  Press Enter when the file is ready → ")
    except (EOFError, KeyboardInterrupt):
        print("\n[compositor] Aborted.")
        sys.exit(0)

    if not os.path.exists(drop_path):
        print(f"\n[ERROR] File not found at {drop_path}", file=sys.stderr)
        print("  Drop the file there and re-run with --stage animator", file=sys.stderr)
        sys.exit(1)

    print(f"\n  ✅ Found CustomVideo.tsx — continuing to render.\n")
    print("═" * 60 + "\n")
    os.environ["COMPOSITOR_FILE"] = drop_path
    return drop_path


def _studio_pause() -> bool:
    """
    Launch Remotion Studio so the user can preview + scrub the rendered video.
    Returns True to send to Telegram, False to skip notifier.
    """
    import subprocess

    remotion_dir = os.path.join(os.path.dirname(__file__), "remotion")
    video_path   = os.path.join(OUTPUT_DIR, "video.mp4")

    print("\n" + "═" * 70)
    print("  STUDIO REVIEW  —  inspect video before sending to Telegram")
    print("═" * 70)

    if os.path.exists(video_path):
        print(f"\n  Rendered video: {video_path}")

    print("\n  Starting Remotion Studio...")
    print("  Browser will open at http://localhost:3000\n")
    print("  • Scrub timeline to check audio sync")
    print("  • Verify beat timing and transitions\n")
    print("═" * 70)

    proc = None
    try:
        proc = subprocess.Popen(
            ["npx", "remotion", "studio"],
            cwd=remotion_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            input("  Press Enter when review is done → ")
        except (EOFError, KeyboardInterrupt):
            print("\n[studio] Interrupted.")

    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("\n[studio] Closed.\n")

    # Explicit send confirmation — bug fix: previously sent regardless of input
    print("═" * 70)
    try:
        ans = input("  Send video to Telegram? [y/n] → ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    print("═" * 70 + "\n")

    if ans != "y":
        print("[notifier] Skipped — video saved at output/video.mp4")
        return False
    return True


def _apply_narration_override(narration_arg: str):
    """
    Write a custom spoken_narration.json from --narration argument.
    Accepts a JSON string or a path to a .json file.
    narrator.py detects this file and skips the LLM rewrite step entirely.
    """
    import json as _json

    # Try as file path first, then as inline JSON string
    if os.path.exists(narration_arg):
        with open(narration_arg) as f:
            narration = _json.load(f)
        print(f"[narration] Loaded custom narration from file → {narration_arg}")
    else:
        # Strip literal newlines/tabs that get embedded when pasting multiline shell commands
        cleaned = narration_arg.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        try:
            narration = _json.loads(cleaned)
            print("[narration] Loaded custom narration from inline JSON")
        except _json.JSONDecodeError as e:
            print(f"[ERROR] --narration value is not valid JSON and not a file path: {e}", file=sys.stderr)
            sys.exit(1)

    required = {"hook", "concept_1", "takeaway_cta"}
    missing  = required - set(narration.keys())
    if missing:
        print(f"[ERROR] --narration JSON missing required keys: {missing}", file=sys.stderr)
        print('  Required: "hook", "concept_1", "concept_2" (optional), "takeaway_cta"', file=sys.stderr)
        sys.exit(1)

    spoken_path = os.path.join(OUTPUT_DIR, "spoken_narration.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(spoken_path, "w") as f:
        _json.dump(narration, f, indent=2)

    segments = list(narration.keys())
    print(f"[narration] Written → {spoken_path}  segments={segments}")
    print("[narration] Narrator LLM rewrite will be skipped — using your narration directly.")


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
    elif name == "brief_generator":
        from pipeline.brief_generator import main
    elif name == "notifier":
        from pipeline.notifier import main
    else:
        raise ValueError(f"Unknown stage: {name}")
    main()


def main():
    parser = argparse.ArgumentParser(description="adamax-content-engine pipeline")
    parser.add_argument("--stage", choices=STAGES + ["content_generator", "brief_generator", "notifier"], help="Run a single stage")
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

    # ── Custom narration + tone ───────────────────────────────────────────────
    parser.add_argument(
        "--narration",
        default="",
        help=(
            "JSON string or path to a .json file with custom spoken narration. "
            "Bypasses LLM narration rewrite. "
            'Expected keys: "hook", "concept_1", "concept_2", "takeaway_cta". '
            "See BRIEF_PROMPT_V2.md for the exact format."
        ),
    )
    parser.add_argument(
        "--tone",
        default="",
        help=(
            "Custom voice delivery instruction for Gemini TTS. "
            "Replaces the default VOICE_DIRECTIVE. "
            'Example: --tone "deadpan and dry, like a skeptical senior engineer who has seen every hype cycle" '
            "See BRIEF_PROMPT_V2.md for tone examples."
        ),
    )

    # ── Compositor ───────────────────────────────────────────────────────────
    parser.add_argument(
        "--compositor", action="store_true",
        help=(
            "Pause after narrator, print context file paths + drop directory, "
            "wait for you to paste a custom CustomVideo.tsx, then continue to render."
        ),
    )

    # ── Intervention checkpoint ───────────────────────────────────────────────
    parser.add_argument(
        "--no-notify", action="store_true", dest="no_notify",
        help="Skip Telegram notification entirely — video saved to output/video.mp4 only.",
    )
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
        os.environ.setdefault("GEMINI_MODEL_RANKER",             "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_SCRIPTER",           "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_VERIFIER",           "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_SCENE_PLANNER",     "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_NARRATOR",           "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_PARAM_EXTRACTOR",   "gemini-2.5-flash-lite")
        os.environ.setdefault("GEMINI_MODEL_ANIMATOR",           "gemini-2.5-flash-lite")
        # content_generator uses flash when generating narration from scratch.
        # With --narration override it only structures data — flash-lite is enough
        # and avoids 403s on keys without gemini-2.5-flash project access.
        # The actual model selection is done in content_generator.py based on NARRATION_OVERRIDE.

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

    # ── Tone override: set env var before narrator stage ─────────────────────
    if args.tone:
        os.environ["NARRATOR_TONE_OVERRIDE"] = args.tone
        print(f"[tone] Custom tone set → \"{args.tone[:80]}\"")

    # ── Narration override: signal content_generator to skip word-count check ─
    if args.narration:
        os.environ["NARRATION_OVERRIDE"] = "1"

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

        # ── Compositor pause: wait for custom CustomVideo.tsx before animator ──
        if getattr(args, "compositor", False) and stage == "animator":
            _compositor_pause()

        # ── Studio review: open Remotion Studio after animator, before notifier ──
        if stage == "notifier":
            if args.no_notify:
                print("[notifier] Skipped — --no-notify flag set.")
                continue
            if not _studio_pause():
                continue

        # ── Narration override: write spoken_narration.json after content stage ─
        if args.narration and stage == "content_generator":
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
            _apply_narration_override(args.narration)
            # ── Narration preview: show final script before TTS ───────────────
            _narration_preview_pause()
            continue

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

        try:
            from pipeline.analytics import create_skeleton
            create_skeleton()
        except Exception as e:
            print(f"[WARN] Analytics skeleton failed: {e}", file=sys.stderr)

    print("\n✅ Pipeline complete.")


if __name__ == "__main__":
    main()
