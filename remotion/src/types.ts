/**
 * types.ts — TypeScript interfaces for Motion Design v2.
 *
 * The old per-template discriminated union (HookParams, StatsGridParams, …)
 * and BeatRouter are removed in Phase 2. Layout is now fully self-describing
 * via LayoutNode trees — see MOTION_DESIGN_V2_TDD.md §PILLAR 1.
 *
 * Python contract (param_extractor.py output):
 *   params.json: { "beat_1": BeatLayout, "beat_2": BeatLayout, ... }
 */

// ── Timing ────────────────────────────────────────────────────────────────────

/** One entry from narration_timing.json */
export interface TimingEntry {
  start: number;    // seconds from video start
  duration: number; // seconds this beat plays
  end: number;      // start + duration
  text?: string;    // narration text (informational only)
}

// ── Cue map — semantic animation triggers from audio word-alignment ───────────

/**
 * Maps intent label → global frame number.
 * Built by build_cue_map() in animator.py from word_timings.json (T5).
 * Optional: components degrade gracefully when cues are absent.
 *
 * Example: { "gpu_split": 312, "metric_reveal": 489, "tp_dim": 213 }
 */
export type CueMap = Record<string, number>;

// ── Root props passed from animator.py via --props ────────────────────────────

export interface RemotionProps {
  /** Ordered beat list — template field stripped; layout is self-describing */
  beats: Array<{ beat: number }>;
  /** Per-beat visual params: key = "beat_1", "beat_2", ... */
  params: Record<string, BeatLayout>;
  /** Narration timing: keys = "hook", "concept_1", ..., "takeaway_cta" */
  timing: Record<string, TimingEntry>;
  /** Filename of audio in remotion/public/ (e.g. "narration.wav") */
  audioSrc: string;
  /** Total frames = round(totalDuration * 30) */
  totalFrames: number;
  /**
   * Semantic cue map from word-level audio alignment (T5 pipeline stage).
   * Optional — absent until word_aligner.py is wired. Components degrade
   * gracefully: useCue() returns active=false when label is not found.
   */
  cues?: CueMap;
}

// ── Motion Design v2 — LayoutNode types ──────────────────────────────────────

export type NodeType =
  | "column" | "row" | "grid"
  // Tier 2 primitives — devtool design system
  | "MetricCard"      // glassmorphism card: label + value + spring-in
  | "GPUNode"         // GPU tile: idle / active / bottleneck states
  | "NumberCounter"   // hero metric: huge number + scale spring
  | "SectionLabel"    // section header: accent bar + uppercase label
  // Legacy primitives — kept for fallback compatibility
  | "TerminalPrompt" | "TerminalText"
  | "StatBox" | "LabelValueCard"
  | "CodeBlock" | "Chip"
  | "Divider" | "Spacer";

export type NodeColor = "green" | "cyan" | "yellow" | "red" | "white";
export type NodeSize  = "xs" | "sm" | "md" | "lg" | "xl";
export type AnimateIn = "spring_in" | "spring_scale" | "typewriter" | "fade" | "slide_up" | "none";

export interface LayoutNode {
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
  size?: NodeSize | number;  // NodeSize for TerminalText font-size; number (px) for Spacer height
  glow?: boolean;
  opacity?: number;

  // Animation props
  animate?: AnimateIn;
  delay?: number;       // frame offset for stagger
  typewriter?: boolean;
  cursor?: boolean;

  // GPUNode state (drives border/glow/opacity variant)
  state?: "idle" | "active" | "bottleneck";
}

export interface BeatLayout {
  animate_in: AnimateIn;
  layout: LayoutNode;
}
