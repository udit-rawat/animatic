# adamax-content-engine — Claude Project Context

## Git Rules (no exceptions)
- Never add co-author lines to commits. All commits are authored solely by the repo owner.
- Never run `git commit` without showing the proposed one-line message first and receiving explicit approval.
- Never run `git push` without approval in the same message exchange.
- "push it" or "go ahead" approves that single operation only — not future ones.
- Before any git operation (commit, push, tag), state what you are about to do and wait.

## Project Summary
Automated daily AI short-form video pipeline. Runs once per day, end-to-end:

1. **scraper** — Fetches top posts from configured subreddits + arXiv papers (no API keys, public endpoints only)
2. **ranker** — Claude picks the single best topic for a 60-second Manim explainer
3. **scripter** — Claude writes a structured script: hook / concept bullets / takeaway / CTA + caption + hashtags
4. **animator** — Claude generates a Manim scene, renders it, auto-retries on error (max 3×)
5. **notifier** — Sends final video + caption to Telegram

## Model & Quality
- Always use `claude-sonnet-4-6` (latest Sonnet series)
- All Claude calls must use `max_tokens=8096` minimum
- Never downgrade model or reduce token budget to save cost

## Architecture Decisions
- Anthropic Python SDK (not subprocess CLI) for all LLM calls — enables token auditing
- Subreddits are env-configurable via `SUBREDDITS` in `.env`
- Output paths are hardcoded: `output/` for data, `manim_scripts/` for generated scenes
- Manim `media/` folder is cleaned up after video is copied to `output/video.mp4`
- Only `output/script.json` and `output/video.mp4` are the "final" deliverables; intermediate JSONs are kept for debugging

## Token Auditing
- Every Claude API call is routed through `pipeline/claude_client.py`
- Usage is accumulated in-process and printed at end of full pipeline run
- Audit saved to `output/audit.json` after each run

## Environment Variables
See `.env.example`. Required:
- `ANTHROPIC_API_KEY` — for all Claude API calls
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — for delivery
- `SUBREDDITS` — comma-separated list, e.g. `r/MachineLearning,r/LocalLLaMA`
