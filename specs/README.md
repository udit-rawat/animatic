## Video Spec Contract

Phase 0 freezes the renderer-neutral source of truth for one video.

Goal:
- content pipeline decides what the video is
- renderer decides how to render it

This prevents another renderer migration from becoming a repo-wide rewrite.

### Source Of Truth

New canonical contract:

- `specs/video_spec.schema.json`

Target runtime artifact:

- `output/video_spec.json`

### Scene Kinds

Every beat must use one of three scene kinds:

- `template`
  Reusable scene module with structured config.
- `custom`
  Bespoke agent-written scene for cases where template constraints are too tight.
- `external_clip`
  Slot backed by Veo3 or another generated clip, optionally with overlays.

### Layout Modes

`layout_mode` replaces old renderer-specific variant naming.

- `full_scene`
  Scene owns the full frame.
- `caption_overlay`
  Scene occupies lower caption band while center stays available for clip/composite.
- `transparent_overlay`
  Overlay-only composition with transparent-safe layout assumptions.

### Current -> Future Mapping

Current files are legacy or derived:

- `output/topic.json` -> folded into `video_spec.topic`
- `output/spoken_narration.json` -> folded into `video_spec.narration.segments`
- `output/narration_timing.json` -> folded into `video_spec.timing`
- `output/params.json` -> becomes derived renderer input, not source of truth
- `output/scene_plan.json` -> becomes derived renderer input, not source of truth
- `cue_definitions.json` -> folded into `video_spec.cues`
- `output/animation_brief.json` -> derived planning artifact
- `output/compositor_prompt.md` -> derived planning artifact
- `CustomVideo.tsx` / future HyperFrames composition -> derived render artifact

### Template Port Strategy

Not every Remotion template should be ported.

Port first:
- `MetricFocus`
- `StatementSlam`
- `TakeawayScene`
- `BarComparison`
- `DataGrid`
- `ComparisonSplit`
- `PipelineFlow`

Defer:
- `TerminalScene`
- `TriStat`
- `TimelineFlow`
- `LeaderboardRank`
- `CodeDiff`

Archive after parity:
- camera system
- layout tree renderer
- test/demo compositions
- R3F-specific experiments

### Phase 0 Deliverables

- schema exists and is reviewable
- scene kinds are locked
- layout modes are locked
- later pipeline rewrites must target this schema first
