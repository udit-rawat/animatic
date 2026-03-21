import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
USER_AGENT = "adamax-content-engine/1.0 (daily AI video pipeline)"


def get_subreddits() -> list[str]:
    raw = os.environ.get("SUBREDDITS", "r/MachineLearning,r/LocalLLaMA")
    return [s.strip() for s in raw.split(",") if s.strip()]


def fetch_reddit_posts(subreddit: str, limit: int = 5) -> list[dict]:
    url = f"https://www.reddit.com/{subreddit}/top.json?t=day&limit={limit * 2}"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()
    data = response.json()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    results = []
    for post in data["data"]["children"]:
        p = post["data"]
        created = datetime.fromtimestamp(p["created_utc"], tz=timezone.utc)
        if created < cutoff:
            continue
        results.append({
            "source": subreddit,
            "title": p["title"],
            "summary": (p.get("selftext") or "")[:300] or p.get("url", ""),
            "url": f"https://reddit.com{p['permalink']}",
        })
        if len(results) == limit:
            break
    return results


def fetch_arxiv_papers(query: str, max_results: int = 3) -> list[dict]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": 10,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = requests.get(
        "https://export.arxiv.org/api/query", params=params, timeout=15
    )
    response.raise_for_status()

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(response.text)
    results = []
    for entry in root.findall("atom:entry", ns)[:max_results]:
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:300]
        link = entry.find("atom:id", ns).text.strip()
        results.append({"source": "arxiv", "title": title, "summary": summary, "url": link})
    return results


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    candidates = []

    for sub in get_subreddits():
        print(f"Fetching {sub}...")
        candidates += fetch_reddit_posts(sub, limit=5)

    print("Fetching arXiv...")
    candidates += fetch_arxiv_papers(
        "large language model OR diffusion model OR reinforcement learning",
        max_results=3,
    )

    output_path = os.path.join(OUTPUT_DIR, "candidates.json")
    with open(output_path, "w") as f:
        json.dump(candidates, f, indent=2)

    print(f"Saved {len(candidates)} candidates → {output_path}")
    return candidates


if __name__ == "__main__":
    main()
