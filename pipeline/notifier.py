import asyncio
import json
import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "script.json")
VIDEO_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
TOPIC_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "topic.json")


def build_message(topic: dict, script: dict) -> str:
    hashtags = " ".join(script["hashtags"])
    return (
        f"\u2705 Today's video is ready\n\n"
        f"\U0001f4cc Topic: {topic['title']}\n\n"
        f"\U0001f4dd Caption:\n{script['caption']}\n\n"
        f"#\ufe0f\u20e3 Hashtags: {hashtags}"
    )


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

    print("Sending video...")
    with open(VIDEO_PATH, "rb") as video_file:
        await bot.send_video(chat_id=chat_id, video=video_file)

    print("Notification sent successfully.")


def main():
    asyncio.run(send_notification())


if __name__ == "__main__":
    main()
