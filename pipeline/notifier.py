import asyncio
import json
import os

from dotenv import load_dotenv
from telegram import Bot
from telegram.request import HTTPXRequest

load_dotenv()

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TOPIC_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
AUDIT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "audit.json")
RETRIES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "output", "animator_retries.json"
)
VIDEO_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
VEO2_PROMPTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "output", "veo2_prompts.txt"
)


def build_audit_block() -> str:
    if not os.path.exists(AUDIT_PATH):
        return ""
    with open(AUDIT_PATH) as f:
        report = json.load(f)

    stages = report.get("stages", {})
    total = report.get("total", {})
    has_tokens = report.get("has_token_counts", False)

    gemini_stages = report.get("gemini_stages", {})
    gemini_total_calls = report.get("gemini_total_calls", 0)

    lines = ["📊 Usage"]
    if has_tokens:
        lines.append("```")
        lines.append(f"{'Stage':<12} {'In':>7} {'Out':>7} {'Total':>8}")
        lines.append("-" * 38)
        for stage, d in stages.items():
            tok = d["input_tokens"] + d["output_tokens"]
            lines.append(
                f"{stage:<12} {d['input_tokens']:>7,} {d['output_tokens']:>7,} {tok:>8,}"
            )
        lines.append("-" * 38)
        grand = total["input_tokens"] + total["output_tokens"]
        lines.append(
            f"{'TOTAL':<12} {total['input_tokens']:>7,} {total['output_tokens']:>7,} {grand:>8,}"
        )
        lines.append("```")
        lines.append(f"Cost: ${total['cost_usd']:.4f}")
        if gemini_total_calls:
            lines.append(f"Gemini: {gemini_total_calls} API calls")
    elif gemini_stages:
        # Gemini-native run — show per-stage call counts
        lines.append("```")
        lines.append(f"{'Stage':<14} {'Calls':>5}")
        lines.append("-" * 22)
        for stage, cnt in sorted(gemini_stages.items()):
            lines.append(f"{stage:<14} {cnt:>5}")
        lines.append("-" * 22)
        lines.append(f"{'TOTAL':<14} {gemini_total_calls:>5}")
        lines.append("```")
        lines.append("(Gemini free tier — no token counts)")
    else:
        lines.append(
            f"Calls: {total.get('calls', 0)}  |  Cost: ${total['cost_usd']:.4f}"
        )

    return "\n".join(lines)


def build_run_stats() -> str:
    lines = []

    # Animator retry info
    if os.path.exists(RETRIES_PATH):
        with open(RETRIES_PATH) as f:
            r = json.load(f)
        attempts = r.get("attempts", 1)
        max_r = r.get("max_retries", 3)
        icon = "✅" if attempts == 1 else ("⚠️" if attempts < max_r else "🔴")
        lines.append(f"{icon} Animator: {attempts}/{max_r} attempts")

    # Runs remaining today
    try:
        from pipeline.quota import get_status

        s = get_status()
        remaining_calls = s.get("remaining", 0)
        # estimate calls per run from today's usage ÷ completed runs
        runs = s.get("runs", [])
        successful = [r for r in runs if r.get("outcome") == "success"]
        if successful and s.get("calls", 0) > 0:
            calls_per_run = s["calls"] / len(successful)
            runs_left = int(remaining_calls / calls_per_run) if calls_per_run else 0
        else:
            calls_per_run = 4  # default estimate: 4 calls per run
            runs_left = int(remaining_calls / calls_per_run)
        lines.append(f"📊 Quota: ~{runs_left} runs remaining today")
    except Exception:
        pass

    return "\n".join(lines)


def build_message(topic: dict, script: dict) -> str:
    audit_block = build_audit_block()
    run_stats = build_run_stats()
    msg = f"\u2705 Today's video is ready\n\n" f"\U0001f4cc Topic: {topic['title']}"
    if run_stats:
        msg += f"\n\n{run_stats}"
    if audit_block:
        msg += f"\n\n{audit_block}"
    return msg


def build_caption_message(script: dict) -> str:
    """Standalone copy-paste message with just caption for Instagram. No hashtags — they train
    you to reuse the same tags and can get indexed externally. Caption only."""
    return script["caption"]


async def send_notification():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")

    with open(TOPIC_PATH) as f:
        topic = json.load(f)
    with open(SCRIPT_PATH) as f:
        script = json.load(f)

    bot = Bot(
        token=token,
        request=HTTPXRequest(read_timeout=300, write_timeout=300, connect_timeout=60),
    )

    print("Sending Telegram message...")
    await bot.send_message(chat_id=chat_id, text=build_message(topic, script))

    video_path = VIDEO_PATH
    print(f"Sending video ({os.path.basename(video_path)})...")
    with open(video_path, "rb") as video_file:
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            read_timeout=300,
            write_timeout=300,
            connect_timeout=60,
        )

    print("Sending caption (no hashtags)...")
    await bot.send_message(chat_id=chat_id, text=build_caption_message(script))

    # Send Veo2 prompts if any animation_hook beats were generated
    if os.path.exists(VEO2_PROMPTS_PATH):
        with open(VEO2_PROMPTS_PATH) as f:
            veo2_text = f.read().strip()
        if veo2_text:
            print("Sending Veo2 prompts...")
            # Telegram message limit is 4096 chars — chunk if needed
            for i in range(0, len(veo2_text), 4000):
                await bot.send_message(chat_id=chat_id, text=veo2_text[i : i + 4000])

    print("Notification sent successfully.")

    # Commit topic to history only after a video is successfully delivered.
    try:
        from pipeline.topic_history import load_history, save_history

        history = load_history()
        save_history(history, topic["title"])
        print(f"Topic saved to history: {topic['title']}")
    except Exception as exc:
        print(f"[WARN] Failed to save topic to history: {exc}")


def main():
    asyncio.run(send_notification())


if __name__ == "__main__":
    main()
