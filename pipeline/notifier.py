import asyncio
import json
import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

SCRIPT_PATH      = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
TOPIC_PATH       = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")
AUDIT_PATH       = os.path.join(os.path.dirname(__file__), "..", "output", "audit.json")
VIDEO_FINAL_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "video_final.mp4")
VIDEO_PATH       = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")


def get_video_path() -> str:
    """Use the narrated final video if available, else the raw Manim video."""
    if os.path.exists(VIDEO_FINAL_PATH):
        return VIDEO_FINAL_PATH
    return VIDEO_PATH


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


def build_message(topic: dict, script: dict) -> str:
    hashtags    = " ".join(script["hashtags"])
    audit_block = build_audit_block()
    msg = (
        f"\u2705 Today's video is ready\n\n"
        f"\U0001f4cc Topic: {topic['title']}\n\n"
        f"\U0001f4dd Caption:\n{script['caption']}\n\n"
        f"#\ufe0f\u20e3 Hashtags: {hashtags}"
    )
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

    video_path = get_video_path()
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
