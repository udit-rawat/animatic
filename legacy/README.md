## Legacy Archive Plan

This directory is archive staging for code and docs that no longer match the
current product direction.

Current direction:
- Gemini-first custom topic flow
- brief-driven end-to-end video generation
- Veo prompt sidecar generation
- upcoming HyperFrames renderer pivot

Archive in phases to avoid breaking the live path.

### Phase 1: Safe To Archive Now

These files belong to the old multi-stage pipeline and are no longer part of
the intended future architecture:

- `pipeline/scraper.py`
- `pipeline/ranker.py`
- `pipeline/scripter.py`
- `pipeline/verifier.py`
- `pipeline/scene_planner.py`
- `pipeline/param_extractor.py`

These can move first because the intended path is now:

`content_generator -> narrator -> word_aligner -> brief_generator -> renderer -> notifier`

### Phase 2: Archive After HyperFrames Parity

Do not archive these yet. They still back the current live render path:

- `pipeline/animator.py`
- `remotion/`
- Remotion-specific docs and prompts

### Files To Rewrite Before Any More Archiving

- `run.py`
- `pipeline/content_generator.py`
- `pipeline/brief_generator.py`
- `pipeline/notifier.py`
- `README.md`
- `.env.example`

### Notes

- Archive should preserve file history and code reference value.
- Move dead code before deleting it.
- Keep runtime stable until HyperFrames render path exists.
