# AdaMax Remotion — Technical Design Document
## Motion Design System v2.0

*Architecture only. No implementation code.*
*Branch target: `feature/motion-design-v2`*
*Based on: `feature/remotion-migration` codebase audit, 2026-03-27*

---

## Executive Summary

The current system has a fundamental architectural ceiling: a fixed enum of 6 templates (`hook`, `stats_grid`, `pipeline`, `comparison`, `timeline`, `takeaway`) that cut sequentially like slides. This TDD proposes four pillars that transform it into a continuous, generative motion design system. The pillars are explicitly sequenced so each one can ship independently without breaking the pipeline.

---

## Current State Constraints

| Constraint | Current Value | Implication |
|---|---|---|
| Beat types | 6 fixed enums | LLM can only choose from a closed list |
| Beat transitions | Hard cut via `<Sequence from>` | No motion between beats |
| Canvas size | Exactly 1080×1920 per beat | No spatial continuity |
| Audio awareness | Zero | UI is deaf to the narration |
| Post-processing | None | Too clean; no hardware feel |
| `types.ts` | Discriminated union on `template` | Adding a 7th template requires touching 5 files |

---

## PILLAR 1: Generative Component Engine

### The Problem

`param_extractor.py`'s `TEMPLATE_SPECS` is a hardcoded string describing field expectations per named template. The LLM is constrained to output scalar values into pre-defined slots. Adding a new visual pattern requires a new Python spec, a new TypeScript interface, a new React component, and a new `BeatRouter` switch case.

### Primitive Component Vocabulary

| Node Type | Role | Key Props |
|---|---|---|
| `column` | Vertical flex container | `gap`, `justify`, `align`, `padding` |
| `row` | Horizontal flex container | `gap`, `justify`, `align` |
| `grid` | CSS grid container | `columns` (2 or 3), `gap` |
| `TerminalPrompt` | `user@adamax:~$ ` prefix line | `text` |
| `TerminalText` | Typewriter-effect text | `text`, `size`, `color`, `typewriter`, `cursor` |
| `StatBox` | Hero metric display | `value`, `label`, `color`, `animate` |
| `LabelValueCard` | Bordered card with label + value | `label`, `value`, `border_color`, `glow` |
| `CodeBlock` | Monospace pre-formatted block | `lines[]`, `highlight_line` |
| `Divider` | Horizontal separator | `color`, `opacity` |
| `Spacer` | Flexible whitespace | `size` (px) |
| `Chip` | Small inline badge | `text`, `color` |

Containers (`column`, `row`, `grid`) accept `children: LayoutNode[]`. Primitives are leaf nodes.

### Proposed JSON Schema Contract

**Python output (`params.json`) — new format:**

```json
{
  "beat_1": {
    "animate_in": "spring_scale",
    "layout": {
      "type": "column",
      "gap": 48,
      "justify": "flex-start",
      "padding": 50,
      "children": [
        { "type": "TerminalPrompt", "text": "user@adamax:~$" },
        {
          "type": "StatBox",
          "value": "3B",
          "label": "parameters",
          "color": "green",
          "animate": "spring_in",
          "delay": 0
        },
        {
          "type": "TerminalText",
          "text": "ElevenLabs beaten.",
          "size": "lg",
          "color": "white",
          "typewriter": true,
          "cursor": true,
          "delay": 36
        }
      ]
    }
  },
  "beat_2": {
    "animate_in": "fade",
    "layout": {
      "type": "column",
      "gap": 32,
      "padding": 50,
      "children": [
        {
          "type": "TerminalText",
          "text": "Voxtral TTS: open-weight model",
          "size": "md",
          "color": "yellow"
        },
        {
          "type": "grid",
          "columns": 2,
          "gap": 24,
          "children": [
            { "type": "LabelValueCard", "label": "Params", "value": "> 3B", "border_color": "cyan", "glow": true },
            { "type": "LabelValueCard", "label": "RAM",    "value": "> 3GB", "border_color": "cyan", "glow": true }
          ]
        }
      ]
    }
  }
}
```

### TypeScript Type Definitions (`types.ts` — replacement)

```typescript
type NodeType =
  | "column" | "row" | "grid"
  | "TerminalPrompt" | "TerminalText"
  | "StatBox" | "LabelValueCard"
  | "CodeBlock" | "Chip"
  | "Divider" | "Spacer";

type NodeColor = "green" | "cyan" | "yellow" | "red" | "white";
type NodeSize  = "xs" | "sm" | "md" | "lg" | "xl";
type AnimateIn = "spring_in" | "spring_scale" | "typewriter" | "fade" | "slide_up" | "none";

interface LayoutNode {
  type: NodeType;

  // Container props (column / row / grid only)
  gap?: number;
  justify?: "flex-start" | "center" | "flex-end" | "space-between";
  align?: "flex-start" | "center" | "flex-end";
  padding?: number;
  columns?: 2 | 3;
  children?: LayoutNode[];

  // Primitive content props
  text?: string;
  value?: string;
  label?: string;
  lines?: string[];
  highlight_line?: number;

  // Style props
  color?: NodeColor;
  border_color?: NodeColor;
  size?: NodeSize;
  glow?: boolean;
  opacity?: number;

  // Animation props
  animate?: AnimateIn;
  delay?: number;       // frame offset for stagger
  typewriter?: boolean;
  cursor?: boolean;
}

interface BeatLayout {
  animate_in: AnimateIn;
  layout: LayoutNode;
}

interface RemotionProps {
  beats: Array<{ beat: number }>;   // template field removed — layout is self-describing
  params: Record<string, BeatLayout>;
  timing: Record<string, TimingEntry>;
  audioSrc: string;
  totalFrames: number;
}
```

### React Component Hierarchy — Pillar 1

```
<VideoComposition>
  └── <CameraViewport>
      └── <VirtualCanvas>
          ├── <BeatZone beat=1>
          │   └── <LayoutRenderer node={beat_1.layout} />
          │       └── <NodeFactory type="column">
          │           ├── <NodeFactory type="TerminalPrompt" />
          │           ├── <NodeFactory type="StatBox" />
          │           └── <NodeFactory type="TerminalText" />
          ├── <BeatZone beat=2>
          │   └── <LayoutRenderer node={beat_2.layout} />
          │       └── <NodeFactory type="column">
          │           ├── <NodeFactory type="TerminalText" />
          │           └── <NodeFactory type="grid">
          │               ├── <NodeFactory type="LabelValueCard" />
          │               └── <NodeFactory type="LabelValueCard" />
          └── ...
```

`<LayoutRenderer>` is a single recursive component that reads `node.type`, dispatches to the correct primitive, or recurses into children. This replaces the entire `BeatRouter` switch and all individual beat files.

### Python Validation Strategy

Replace `_validate()` with a recursive tree walker:

```
def _validate_layout_node(node: dict, depth: int = 0) -> list[str]:
    errors = []
    # Max recursion depth = 4 (column > row > grid > leaf)
    if depth > 4: return ["Layout tree too deep (max 4 levels)"]
    # type must be in ALLOWED_NODE_TYPES
    # containers must have children []
    # leaf nodes must NOT have children
    # text fields must be under character limits
    # color must be in ALLOWED_COLORS
    # delay must be non-negative integer
    for child in node.get("children", []):
        errors += _validate_layout_node(child, depth + 1)
    return errors
```

---

## PILLAR 2: The Infinite Canvas & Camera

### The Problem

`<Sequence from={n} durationInFrames={d}>` produces hard cuts. There is no spatial relationship between beats. The viewer has no sense of "moving through" information.

### Canvas Layout

```
Virtual Canvas (1080 × n_beats × 1920 px):
  ┌─────────────────────┐  y = 0
  │     Beat 1: Hook    │  (1920px tall)
  ├─────────────────────┤  y = 1920
  │  Beat 2: StatsGrid  │  (1920px tall)
  ├─────────────────────┤  y = 3840
  │  Beat 3: Comparison │  (1920px tall)
  ├─────────────────────┤  y = 5760
  │  Beat 4: Takeaway   │  (1920px tall)
  └─────────────────────┘  y = 7680
```

Camera = `translateY(-cameraY)` on the canvas container. Viewport `overflow: hidden` clips to 1080×1920.

### `useCameraY` Hook Design

```
Input:  frame, timing entries (frame-converted), beats.length
Output: { cameraY, cameraVelocity }

Algorithm:
  1. targetY[beat_i] = (beat_i - 1) * 1920

  2. At each timing boundary, spring from targetY[i] to targetY[i+1]:
       panStartFrame = timingEntry[i].endFrame - 18  (0.6s before end)
       panEndFrame   = timingEntry[i].endFrame + 8   (settle 0.27s after)

  3. Spring config:
       damping: 180, stiffness: 320, overshootClamping: true
       (~0.8s total travel)

  4. Between pans: Ken Burns drift +/- 8px over the full beat duration
       interpolate(frame, [beatStart, beatEnd], [0, 8], sine easing)

  5. cameraVelocity = cameraY[frame] - cameraY[frame-1]
     (exported for CRT aberration gating in Pillar 4)
```

### Camera Movement Types

| Type | Trigger | Duration | Config |
|---|---|---|---|
| Smooth pan | Default beat transition | ~0.8s / 24 frames | Spring overdamped |
| Warp cut | Beat duration < 3s | Instant + flash frame | `opacity: 0` for 1 frame |
| Ken Burns | During hold period | Full beat duration | `interpolate` sine 8px |

### `<CameraViewport>` Component Contract

```typescript
interface CameraViewportProps {
  totalBeats: number;
  timing: Record<string, TimingEntry>;
  children: React.ReactNode;
}
// Returns: JSX with overflow:hidden viewport + translated canvas
// Exposes cameraVelocity via React context for CRTWrapper
```

---

## PILLAR 3: Audio-Reactive Environments

### Package Requirement

```
npm install @remotion/media-utils
```

### Frequency Bin Mapping

At 24kHz sample rate with 256 frequency bins from `visualizeAudio`:

| Bin Range | Frequency | Derived Metric | Visual Effect |
|---|---|---|---|
| 0–8 | 0–375 Hz (sub-bass) | `bassEnergy` | Background matrix stream speed |
| 9–32 | 375–1.5kHz (bass) | `bassEnergy` | Border glow pulse on cards |
| 33–128 | 1.5–6kHz (mid/voice) | `midEnergy` / `rmsVoice` | Text glow intensity |
| 129–255 | 6–12kHz (presence) | `highEnergy` | Screen grain/noise overlay |

### `useAudioMetrics` Hook Design

```
Input:  audioSrc (string), frame, fps
Output: { rms, bassEnergy, midEnergy, highEnergy }  — all 0.0–1.0

Algorithm:
  1. useAudioData(staticFile(audioSrc)) → audioData (null until loaded)
  2. If null → return { rms: 0, bassEnergy: 0, midEnergy: 0, highEnergy: 0 }
  3. bins = visualizeAudio({ audioData, frame, fps, numberOfSamples: 256 })
  4. Smooth over 5-frame window (call visualizeAudio 5× per frame):
       smoothBins = average of bins[frame-2..frame+2]
  5. Derive:
       bassEnergy = mean(smoothBins[0..32]) / maxAmplitude
       midEnergy  = mean(smoothBins[33..128]) / maxAmplitude
       highEnergy = mean(smoothBins[129..255]) / maxAmplitude
       rms        = sqrt(mean(smoothBins² across all 256))
  6. Clamp all values to [0, 1]
```

### CSS Variable Injection Contract

`useAudioMetrics` called once at `<VideoComposition>` root. Injected as CSS custom properties:

```
--audio-rms:    0.0–1.0  → text-shadow spread (neon glow)
--audio-bass:   0.0–1.0  → border-color opacity and matrix speed
--audio-mid:    0.0–1.0  → card inner glow brightness
--audio-high:   0.0–1.0  → screen grain intensity
```

Components react via `calc()`:
```css
/* TerminalText */
text-shadow: 0 0 calc(var(--audio-rms) * 40px + 8px) #00FF41,
             0 0 calc(var(--audio-rms) * 80px + 16px) #00FF4160;

/* LabelValueCard */
box-shadow: 0 0 calc(var(--audio-bass) * 30px + 12px) #00E5FF40;
```

### Matrix Data Stream Background

- Falling katakana/ASCII characters in a column grid
- Fall speed = `bassEnergy × 8 + 2` pixels per frame
- Character opacity = `midEnergy × 0.15 + 0.03`
- **All randomness must be deterministic**: use `Math.sin(column * frame * 0.01)` — never `Math.random()`
- Determinism is critical: Remotion parallel workers render frames independently; non-deterministic code produces visual artifacts in the final encode

---

## PILLAR 4: CRT Post-Processing Wrapper

### Effect Stack (Z-order)

```
z=0   : Content (VideoComposition children)
z=100 : Scanlines (CSS repeating-linear-gradient, always on)
z=101 : Vignette (CSS radial-gradient, always on)
z=102 : Chromatic aberration (gated: |cameraVelocity| > 15px/frame AND CRT_ABERRATION=1)
z=103 : Screen grain (gated: highEnergy > 0.1)
```

### Effect 1: Scanlines

```css
background: repeating-linear-gradient(
  0deg,
  transparent 0px, transparent 3px,
  rgba(0, 0, 0, 0.12) 3px, rgba(0, 0, 0, 0.12) 4px
);
```
4px pitch. 480 scanlines at 1920px height. Zero compute cost.

### Effect 2: Vignette

```css
background: radial-gradient(
  ellipse 85% 85% at 50% 50%,
  transparent 55%,
  rgba(0, 0, 0, 0.55) 100%
);
```

### Effect 3: Chromatic Aberration

- Only activates when `|cameraVelocity| > 15px/frame` AND `CRT_ABERRATION=1` env var
- `aberrationPx = clamp(|cameraVelocity| / 20, 0, 4)` — max 4px split
- Approximated via `backdrop-filter` at very low radius (0.3px) with CSS color matrix
- **WARNING**: `backdrop-filter` is slow in Puppeteer headless. Hard-gate behind env var. Profile before enabling in production.

### Effect 4: Screen Grain

- Small-scale noise overlay, deterministic via `sin/cos` hash seeded on `frame`
- `opacity = highEnergy × 0.08 + 0.02`
- 64×64 repeating pattern (not per-pixel) for performance

---

## Risk Assessment

### Critical Risks

| Risk | Severity | Probability | Mitigation |
|---|---|---|---|
| LLM outputs invalid LayoutNode tree | **High** | **Medium-High** | Recursive `_validate_layout_node()` + 3-attempt retry + static fallback trees |
| `backdrop-filter` tanks render time in Puppeteer | **High** | **Medium** | Hard-gate behind `CRT_ABERRATION=1` env var; profile first |
| `Math.random()` in Matrix stream causes frame desync | **High** | **High** | All visual randomness must use deterministic hash functions seeded on frame/column |
| `useAudioData()` returns null for early frames | **Medium** | **High** | Default all audio metrics to 0 when `audioData === null` |

### Performance Impact Table

| Change | RAM Delta | Render Time Delta | Notes |
|---|---|---|---|
| Virtual canvas (Pillar 2) | +~4MB | ~0% | DOM is cheap; only visible portion is painted |
| `useAudioMetrics` (Pillar 3) | +~2.3MB/worker | +15–25% | `visualizeAudio()` ×5 per frame. Acceptable. |
| Matrix stream (Pillar 3) | negligible | +3–5% | Deterministic CSS, no canvas API |
| CRTWrapper gradients (Pillar 4) | negligible | +2–4% | CSS gradients are GPU-composited |
| `backdrop-filter` (Pillar 4) | negligible | +**30–60%** if enabled | Known Puppeteer bottleneck. Hard gate. |

**Total projected render time (Pillars 1–4, no `backdrop-filter`):**
- Current baseline: ~60–90s
- After migration: ~80–120s
- `$0/day` operating cost unchanged. Well under 300s timeout.

---

## Ordered Execution Plan

### Phase 0 — Schema Foundation *(prerequisite for everything)*
1. Define final `LayoutNode` TypeScript types in `types.ts`
2. Implement `_validate_layout_node()` in Python with full recursive validation
3. Build static fallback trees for each of the 6 old templates
4. Build `<LayoutRenderer>` skeleton that renders a hardcoded `LayoutNode` tree
5. **Gate**: confirm `LayoutRenderer` renders Beat1Hook equivalent correctly

### Phase 1 — Generative Component Engine (Pillar 1)
6. Implement all 10 primitive `<NodeFactory>` components
7. Update `param_extractor.py` TEMPLATE_SPECS prompt to request `LayoutNode` JSON
8. Port default props in `Root.tsx` to new schema
9. Remove `BeatRouter`, `Beat1Hook.tsx`, `Beat2Pipeline.tsx`, etc.
10. **Gate**: run `--stage animator` with params converted to new format

### Phase 2 — Infinite Canvas & Camera (Pillar 2)
11. Build `<VirtualCanvas>` and `<BeatZone>` components
12. Implement `useCameraY()` with spring pan logic
13. Build `<CameraViewport>` with overflow clipping
14. Replace `<Sequence>` timing model in `VideoComposition.tsx`
15. **Gate**: render 4-beat test video, inspect transitions

### Phase 3 — Audio Reactivity (Pillar 3)
16. `npm install @remotion/media-utils`
17. Implement `useAudioMetrics()` hook with 5-frame smoothing window
18. Inject CSS variables at `<VideoComposition>` root
19. Add `calc(var(--audio-rms) * ...)` to `TerminalText` and `LabelValueCard`
20. Implement deterministic Matrix data stream background
21. **Gate**: render at `--concurrency=1`, profile frame render time. Accept if <3ms/frame overhead.

### Phase 4 — CRT Post-Processing (Pillar 4)
22. Build `<CRTWrapper>` with scanlines and vignette (always-on)
23. Add screen grain layer gated on `highEnergy`
24. Add chromatic aberration gated on `CRT_ABERRATION=1` env var
25. Profile render time with and without aberration
26. **Gate**: render full pipeline, compare file sizes and visual quality

### Phase 5 — Integration Hardening
27. Run `python3 run.py --gemini` end-to-end on 3 different topics
28. Verify: audio reactivity, camera pans, CRT overlay all present
29. Stress test: topic that generates 6 beats (maximum canvas height)
30. Update `CLAUDE.md` architecture section

---

## Final Component Hierarchy

```
<RemotionRoot>
  └── <VideoComposition props={RemotionProps}>
      ├── <Audio src={staticFile(audioSrc)} />
      ├── useAudioMetrics()  ← CSS vars injected here
      └── <CRTWrapper cameraVelocity={velocity}>
          └── <CameraViewport timing={timing} totalBeats={n}>
              └── <VirtualCanvas height={n * 1920}>
                  ├── <BeatZone index={0} y={0}>
                  │   └── <LayoutRenderer node={params.beat_1.layout} />
                  ├── <BeatZone index={1} y={1920}>
                  │   └── <LayoutRenderer node={params.beat_2.layout} />
                  └── ...
```

---

## Decision Required Before Implementation Begins

**Fallback behavior when LLM outputs a bad LayoutNode tree:**

- **Option A (Safe — recommended):** If validation fails 3 times, `param_extractor` falls back to the old flat-key format and `LayoutRenderer` uses a hardcoded static tree for that template type. Video always renders. Never wastes a Gemini run.
- **Option B (Strict):** If validation fails 3 times, the stage raises `RuntimeError` and the pipeline stops. Forces correct output but fails more runs during early tuning.

Option A is recommended to protect the `$0/day` operating cost constraint.

---

*End of TDD. Begin implementation by reading this file at session start.*
