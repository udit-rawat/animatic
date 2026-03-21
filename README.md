# adamax-content-engine

Automated daily AI video pipeline: scrapes trending AI topics, ranks them with Claude, writes a 60-second script, renders a Manim animation, and delivers the final video to Telegram.

---

## Setup

```bash
git clone https://github.com/your-username/adamax-content-engine.git
cd adamax-content-engine
pip install -r requirements.txt
cp .env.example .env
# Fill in your credentials in .env
```

### `.env` variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat/user ID |
| `SUBREDDITS` | No | Comma-separated list (default: `r/MachineLearning,r/LocalLLaMA`) |

---

## Run the full pipeline

```bash
python run.py
```

Runs all five stages in sequence and prints a token cost audit at the end:

| Stage | What it does |
|---|---|
| scraper | Fetches top posts from configured subreddits + arXiv papers |
| ranker | Claude picks the single best topic for a 60-second visual explainer |
| scripter | Claude writes hook / concept bullets / takeaway / caption / hashtags |
| animator | Claude generates a Manim scene, renders it, auto-retries on error (max 3×) |
| notifier | Sends video + caption to Telegram |

---

## Run a single stage

```bash
python run.py --stage scraper
python run.py --stage ranker
python run.py --stage scripter
python run.py --stage animator
python run.py --stage notifier
```

---

## Output files

| File | Description |
|---|---|
| `output/candidates.json` | All scraped topic candidates |
| `output/topic.json` | The single topic Claude selected |
| `output/script.json` | Hook, bullets, takeaway, caption, hashtags |
| `output/video.mp4` | Final rendered Manim video |
| `output/audit.json` | Token usage and cost breakdown per stage |
| `manim_scripts/scene.py` | Generated Manim Python scene |

---

## Telegram bot setup

1. **Create a bot**: Search `@BotFather` on Telegram → `/newbot` → follow prompts → copy the token → set as `TELEGRAM_BOT_TOKEN`.

2. **Get your chat ID**: Start a chat with your bot (send any message). Then open:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   Find `"chat": {"id": 123456789}` → that number is your `TELEGRAM_CHAT_ID`.

3. **Fill `.env`** and run `python run.py`.

---

## Token cost audit

After every full run, the pipeline prints a table like:

```
=======================================================
  TOKEN AUDIT
=======================================================
  Stage           Calls    In tok   Out tok     Cost $
  ---------------------------------------------------
  ranker              1     2,841       312    $0.0131
  scripter            1     1,203       598    $0.0126
  animator            2     4,102     6,890    $0.1159
  ---------------------------------------------------
  TOTAL               4     8,146     7,800    $0.1416
=======================================================
```

Audit is also saved to `output/audit.json` for programmatic use.
