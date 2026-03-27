import asyncio
import json
import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

SCRIPT_PATH      = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TOPIC_PATH       = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
AUDIT_PATH       = os.path.join(os.path.dirname(__file__), "..", "output", "audit.json")
RETRIES_PATH     = os.path.join(os.path.dirname(__file__), "..", "output", "animator_retries.json")
VIDEO_PATH       = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")


def build_audit_block() -> str:
    if not os.path.exists(AUDIT_PATH):
        return ""
    with open(AUDIT_PATH) as f:
        report = json.load(f)

    stages = report.get("stages", {})
    total  = report.get("total", {})
    has_tokens = report.get("has_token_counts", False)

    lines = ["📊 Token Usage"]
    if has_tokens:
        lines.append("```")
        lines.append(f"{'Stage':<12} {'In':>7} {'Out':>7} {'Total':>8}")
        lines.append("-" * 38)
        for stage, d in stages.items():
            tok = d["input_tokens"] + d["output_tokens"]
            lines.append(f"{stage:<12} {d['input_tokens']:>7,} {d['output_tokens']:>7,} {tok:>8,}")
        lines.append("-" * 38)
        grand = total["input_tokens"] + total["output_tokens"]
        lines.append(f"{'TOTAL':<12} {total['input_tokens']:>7,} {total['output_tokens']:>7,} {grand:>8,}")
        lines.append("```")
        lines.append(f"Cost: ${total['cost_usd']:.4f}")
    else:
        lines.append(f"Calls: {total.get('calls', 0)}  |  Cost: ${total['cost_usd']:.4f}")

    return "\n".join(lines)


def build_run_stats() -> str:
    lines = []

    # Animator retry info
    if os.path.exists(RETRIES_PATH):
        with open(RETRIES_PATH) as f:
            r = json.load(f)
        attempts = r.get("attempts", 1)
        max_r    = r.get("max_retries", 3)
        icon     = "✅" if attempts == 1 else ("⚠️" if attempts < max_r else "🔴")
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
    hashtags    = " ".join(script["hashtags"])
    audit_block = build_audit_block()
    run_stats   = build_run_stats()
    msg = (
        f"\u2705 Today's video is ready\n\n"
        f"\U0001f4cc Topic: {topic['title']}\n\n"
        f"\U0001f4dd Caption:\n{script['caption']}\n\n"
        f"#\ufe0f\u20e3 Hashtags: {hashtags}"
    )
    if run_stats:
        msg += f"\n\n{run_stats}"
    if audit_block:
        msg += f"\n\n{audit_block}"
    return msg


async def send_notification():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")

    with open(TOPIC_PATH) as f:
        topic = json.load(f)
    with open(SCRIPT_PATH) as f:
        script = json.load(f)

    bot = Bot(token=token)
    message = build_message(topic, script)

    print("Sending Telegram message...")
    await bot.send_message(chat_id=chat_id, text=message)

    video_path = VIDEO_PATH
    print(f"Sending video ({os.path.basename(video_path)})...")
    with open(video_path, "rb") as video_file:
        await bot.send_video(chat_id=chat_id, video=video_file)

    print("Notification sent successfully.")

    # Commit topic to history only after a video is successfully delivered.
    try:
        from pipeline.ranker import load_history, save_history
        history = load_history()
        save_history(history, topic["title"])
        print(f"Topic saved to history: {topic['title']}")
    except Exception as exc:
        print(f"[WARN] Failed to save topic to history: {exc}")


def main():
    asyncio.run(send_notification())


if __name__ == "__main__":
    main()
