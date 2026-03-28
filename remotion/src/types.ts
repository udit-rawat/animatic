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
  /** Ordered beat list */
  beats: Array<{ beat: number }>;
  /**
   * v3 — ScenePayload per beat (new pipeline path, preferred).
   * Keyed "beat_1", "beat_2", …  Written by animator.py as `scenes`.
   */
  scenes?: Record<string, ScenePayload>;
  /**
   * v2 — BeatLayout / LayoutNode trees (legacy fallback).
   * VideoComposition prefers `scenes` when present.
   */
  params?: Record<string, BeatLayout>;
  /** Narration timing: keys = "hook", "concept_1", ..., "takeaway_cta" */
  timing: Record<string, TimingEntry>;
  /** Filename of audio in remotion/public/ (e.g. "narration.wav") */
  audioSrc: string;
  /** Total frames = round(totalDuration * 30) */
  totalFrames: number;
  /**
   * Semantic cue map from word-level audio alignment (T5).
   * Optional — absent before word_aligner runs.
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
  delay?: number;       // frame offset for stagger (ignored when cue is set)
  cue?: string;         // T5: named cue label from cue_definitions.json; when set, animation
                        // starts when the cue fires (useCue(cue).elapsed), overriding delay
  typewriter?: boolean;
  cursor?: boolean;

  // GPUNode state (drives border/glow/opacity variant)
  state?: "idle" | "active" | "bottleneck";
}

export interface BeatLayout {
  animate_in: AnimateIn;
  layout: LayoutNode;
}

// ── Motion Design v3 — ScenePayload (replaces BeatLayout in new pipeline) ────
//
// The LLM outputs a ScenePayload per beat. SceneData is a discriminated union
// on the `layout` field — TypeScript narrows automatically in switch/if checks.
//
// Python contract (param_extractor.py v3 output):
//   params.json: { "beat_1": ScenePayload, "beat_2": ScenePayload, ... }
//   animator.py assembles_props() writes this as the `scenes` key.

export type LayoutKind =
  | "ComparisonSplit"
  | "MetricFocus"
  | "PipelineFlow"
  | "DataGrid"
  | "TakeawayScene"
  | "KineticBridge";

export interface MetricItem {
  label:  string;         // ≤ 8 chars — renders at 60px on phone
  value:  string;         // ≤ 8 chars
  color?: NodeColor;
  glow?:  boolean;
}

export interface PipelineStep {
  label:    string;                             // node name ≤ 12 chars
  sublabel?: string;                            // e.g. "12ms" — shown below label
  state:    "idle" | "active" | "bottleneck";
}

export interface ComparisonSplitData {
  layout:        "ComparisonSplit";
  section_label: string;
  left:          { heading: string; color: NodeColor; metrics: MetricItem[] };
  right:         { heading: string; color: NodeColor; metrics: MetricItem[] };
  divider_label?: string;                       // e.g. "vs" (default)
}

export interface MetricFocusData {
  layout:        "MetricFocus";
  section_label: string;
  hero:          { value: string; label: string; color: NodeColor };
  context:       string;                        // 1–2 sentence supporting claim
  chips?:        string[];                      // 2–3 short tags
}

export interface PipelineFlowData {
  layout:           "PipelineFlow";
  section_label:    string;
  steps:            PipelineStep[];             // 3–5 nodes
  flow_direction:   "horizontal" | "vertical";
  bottleneck_label?: string;                    // annotation below bottleneck step
}

export interface DataGridData {
  layout:           "DataGrid";
  section_label:    string;
  metrics:          MetricItem[];               // 2–4 items
  highlight_index?: number;                     // card index that gets glow
  caption?:         string;
}

export interface TakeawaySceneData {
  layout:        "TakeawayScene";
  section_label: string;
  headline:      string;                        // key insight ≤ 14 words
  cta?:          string;                        // e.g. "Follow for daily ML breakdowns"
  accent_color?: "cyan" | "green" | "yellow";
}

/**
 * KineticBridgeData — for conversational / narrative beats with no structured data.
 * 2–5 keywords pulse sequentially so the screen is never a black hole.
 */
export interface KineticBridgeData {
  layout:        "KineticBridge";
  section_label: string;
  keywords:      string[];                      // 2–5 short phrases, ≤ 20 chars each
  accent_color?: "cyan" | "green" | "yellow";
}

export type SceneData =
  | ComparisonSplitData
  | MetricFocusData
  | PipelineFlowData
  | DataGridData
  | TakeawaySceneData
  | KineticBridgeData;

export interface ScenePayload {
  animate_in: AnimateIn;
  cue?:       string;       // optional cue label from cue_definitions.json
  data:       SceneData;
}
