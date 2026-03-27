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
}

// ── Motion Design v2 — LayoutNode types ──────────────────────────────────────

export type NodeType =
  | "column" | "row" | "grid"
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
}

export interface BeatLayout {
  animate_in: AnimateIn;
  layout: LayoutNode;
}
