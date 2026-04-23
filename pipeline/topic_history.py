import json
import os

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "picked_history.json")
MAX_HISTORY = 30


def load_history() -> list[str]:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH) as f:
        return json.load(f)


def save_history(history: list[str], new_title: str):
    history = [new_title] + [t for t in history if t != new_title]
    history = history[:MAX_HISTORY]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)
