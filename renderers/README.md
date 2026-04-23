## Renderers

This directory holds renderer backends that consume the renderer-neutral
`video_spec.json` contract.

Current state:
- active production renderer: Remotion via `pipeline/animator.py`
- next target renderer: HyperFrames

Rule:
- pipeline code should emit `output/video_spec.json`
- renderer code should consume it
- renderer code should not become the source of truth

During migration, Remotion remains live and HyperFrames is built in parallel.
