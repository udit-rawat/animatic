#!/usr/bin/env python3
"""
Check health of all configured Gemini API keys.
Usage: python check_gemini_quota.py
"""

import json
import os
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

KEYS = [
    k.strip()
    for k in os.environ.get(
        "GEMINI_API_KEYS", os.environ.get("GEMINI_API_KEY", "")
    ).split(",")
    if k.strip()
]
MODEL = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

PAYLOAD = json.dumps(
    {
        "contents": [{"parts": [{"text": "Reply with just: OK"}]}],
        "generationConfig": {"maxOutputTokens": 5},
    }
).encode()


def check_key(key: str) -> tuple[str, str, str]:
    suffix = f"...{key[-8:]}"
    req = urllib.request.Request(
        f"{URL}?key={key}",
        data=PAYLOAD,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return suffix, "✅  HEALTHY", text
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body).get("error", {})
            msg = err.get("message", body)[:100]
        except Exception:
            msg = body[:100]

        if e.code == 429:
            if "quota" in msg.lower() or "limit" in msg.lower():
                return suffix, "🔴 DAILY EXHAUSTED", msg
            return suffix, "⚠️  RPM LIMITED", msg
        elif e.code == 400:
            return suffix, "❌ BAD REQUEST", msg
        elif e.code == 403:
            return suffix, "🔒 FORBIDDEN", msg
        else:
            return suffix, f"❌ HTTP {e.code}", msg
    except Exception as ex:
        return suffix, "❌ ERROR", str(ex)


def load_quota_state() -> dict:
    path = os.path.join(os.path.dirname(__file__), "output", "gemini_quota.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


if __name__ == "__main__":
    quota = load_quota_state()
    exhausted_keys = quota.get("exhausted_keys", [])

    print(f"\nGemini key health check — model: {MODEL}")
    print(
        f"Quota date: {quota.get('date', 'unknown')}  |  Calls today: {quota.get('calls', 0)}"
    )
    print(f"Locally exhausted keys (suffix): {exhausted_keys or 'none'}")
    print("-" * 60)

    if not KEYS:
        print("No keys found. Set GEMINI_API_KEYS in .env")
        exit(1)

    results = []
    for key in KEYS:
        suffix, status, detail = check_key(key)
        local_flag = (
            " [locally marked exhausted]"
            if any(key.endswith(s) for s in exhausted_keys)
            else ""
        )
        print(f"  {suffix}  {status}{local_flag}")
        if (
            "ERROR" in status
            or "EXHAUST" in status
            or "FORBIDDEN" in status
            or "BAD" in status
        ):
            print(f"             └─ {detail}")
        results.append((suffix, status))

    print("-" * 60)
    healthy = sum(1 for _, s in results if "HEALTHY" in s)
    rpm_limited = sum(1 for _, s in results if "RPM" in s)
    print(
        f"  {healthy} healthy  |  {rpm_limited} rpm-limited  |  {len(results) - healthy - rpm_limited} exhausted/broken\n"
    )
