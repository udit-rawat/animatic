## Phase 1 Archive Set

These files are prepared for archive because they represent the old
scraper/ranker/multi-stage content pipeline:

- `pipeline/scraper.py`
- `pipeline/ranker.py`
- `pipeline/scripter.py`
- `pipeline/verifier.py`
- `pipeline/scene_planner.py`
- `pipeline/param_extractor.py`

Why these first:
- current strategy no longer starts from Reddit/arXiv scraping
- ranking is no longer the primary entrypoint
- the old multi-stage LLM chain was replaced by `content_generator.py`
- these files create mental overhead and make the repo look more active than it is

Do not move renderer code yet. Remotion is still the active render backend.
