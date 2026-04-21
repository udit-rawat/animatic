## Phase 2 Asset Classification

This file classifies the current Remotion codebase into:
- `PORT_FIRST`
- `DEFER`
- `ARCHIVE_LATER`

Goal:
- preserve current production flow
- port only the visual pieces that matter first
- avoid rebuilding Remotion concepts that do not belong in HyperFrames

## PORT_FIRST

These should become HyperFrames-native scene modules first.

### Templates

- `remotion/src/layouts/MetricFocus.tsx`
  Why: core hook beat, reused heavily, easy HTML/CSS port.

- `remotion/src/layouts/StatementSlam.tsx`
  Why: core insight beat, also appears in bespoke compositor flow.

- `remotion/src/layouts/TakeawayScene.tsx`
  Why: core outro beat, product-critical.

- `remotion/src/layouts/BarComparison.tsx`
  Why: strong for repo/tool comparisons and current active briefs.

- `remotion/src/layouts/DataGrid.tsx`
  Why: generic multi-metric card pattern, high utility.

- `remotion/src/layouts/ComparisonSplit.tsx`
  Why: high-signal before/after or A-vs-B pattern.

- `remotion/src/layouts/PipelineFlow.tsx`
  Why: mechanism explanations still need a sequential process layout.

### Shared motion ideas to port conceptually

- `remotion/src/layouts/_shared.tsx`
  Why: pulse, slide, highlight, count-up, breath should become HyperFrames helper primitives.

- `remotion/src/utils/springIn.ts`
  Why: timing presets should become motion presets, not literal React hooks.

## DEFER

Useful, but not required for first HyperFrames parity.

- `remotion/src/layouts/TerminalScene.tsx`
- `remotion/src/layouts/TriStat.tsx`
- `remotion/src/layouts/TimelineFlow.tsx`
- `remotion/src/layouts/LeaderboardRank.tsx`
- `remotion/src/layouts/CodeDiff.tsx`

Reason:
- valuable layouts, but lower volume or narrower use.
- should be ported only if active briefs keep selecting them.

## ARCHIVE_LATER

Do not port these as-is.

### Remotion-specific orchestration

- `remotion/src/VideoComposition.tsx`
- `remotion/src/SceneRouter.tsx`
- `remotion/src/Root.tsx`
- `remotion/src/index.ts`
- `remotion/src/types.ts`
- `remotion/src/CameraViewport.tsx`
- `remotion/src/context/SceneContext.ts`
- `remotion/src/hooks/useAudioMetrics.ts`
- `remotion/src/hooks/useBeatFrame.ts`
- `remotion/src/hooks/useCameraY.ts`
- `remotion/src/hooks/useCue.ts`

Reason:
- tied to Remotion timing model, camera model, or React composition model.

### Legacy layout/runtime systems

- `remotion/src/LayoutRenderer.tsx`
- `remotion/src/layouts/KineticBridge.tsx`

Reason:
- old system or transitional abstraction that should not survive into HyperFrames.

### Animation hook split as separate family

- `remotion/src/templates/animation_hook/CaptionZone.tsx`
- `remotion/src/templates/animation_hook/DataGrid.tsx`
- `remotion/src/templates/animation_hook/MetricFocus.tsx`
- `remotion/src/templates/animation_hook/StatementSlam.tsx`
- `remotion/src/templates/animation_hook/TakeawayScene.tsx`
- `remotion/src/templates/animation_hook/TriStat.tsx`
- `remotion/src/templates/animation_hook/index.ts`
- `remotion/src/templates/infographic/index.ts`

Reason:
- HyperFrames should use `layout_mode` (`full_scene`, `caption_overlay`, `transparent_overlay`)
  instead of maintaining duplicate template families.

### Demo and experiment files

- `remotion/src/PhosphorDemo.tsx`
- `remotion/src/QwenPawCPU.tsx`
- `remotion/src/SampleMVP.tsx`
- `remotion/src/TemplateMVP.tsx`
- `remotion/src/ThemeTest.tsx`
- `remotion/src/layouts/HookR3F.tsx`
- `remotion/src/r3f/MetallicHook.tsx`

Reason:
- demos, experiments, or R3F-specific work not needed for first renderer migration.

### Current bespoke compositor artifact

- `remotion/src/CustomVideo.tsx`

Reason:
- keep until HyperFrames custom-scene path exists, then archive as legacy render artifact.

## Mapping Rules

### Template family

Future template scene IDs:
- `MetricFocus`
- `StatementSlam`
- `TakeawayScene`
- `BarComparison`
- `DataGrid`
- `ComparisonSplit`
- `PipelineFlow`

### Layout mode

Use `video_spec.beats[].layout_mode` instead of duplicate template families:
- `full_scene`
- `caption_overlay`
- `transparent_overlay`

### Custom scene path

`scene.kind = "custom"` should become a HyperFrames-native composition path,
not a React file.

### External clip path

`scene.kind = "external_clip"` should be used for Veo3-backed scenes with
optional overlays.
