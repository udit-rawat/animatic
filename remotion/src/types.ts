/**
 * types.ts — TypeScript interfaces mirroring the Python param_extractor.py output.
 *
 * Source of truth for the data contract between the Python pipeline and Remotion.
 * Any field added to TEMPLATE_SPECS in param_extractor.py must be reflected here.
 *
 * params.json structure: { "beat_1": {...}, "beat_2": {...}, ... }
 * narration_timing.json keys: "hook", "concept_1", "concept_2", ..., "takeaway_cta"
 */

// ── Beat template discriminated union ────────────────────────────────────────

export type BeatTemplate =
  | "hook"
  | "pipeline"
  | "comparison"
  | "stats_grid"
  | "timeline"
  | "takeaway";

// ── Per-template param interfaces ─────────────────────────────────────────────

/** Beat 1 — hook_stat: ≤8 chars (e.g. "40%", "3B"), hook_text: ≤8 words */
export interface HookParams {
  template: "hook";
  hook_stat: string;
  hook_text: string;
}

/** Beat type: pipeline — concept_text ≤7 words, pipeline_steps 3-5 items ≤6 chars each */
export interface PipelineParams {
  template: "pipeline";
  concept_text: string;
  pipeline_steps: string[];
}

/** Beat type: comparison — before/after labels ≤6 chars, details ≤5 words */
export interface ComparisonParams {
  template: "comparison";
  concept_text: string;
  before_label: string;
  after_label: string;
  before_detail: string;
  after_detail: string;
}

/** Beat type: stats_grid — 2-6 stat cards with label ≤5 chars, value ≤8 chars */
export interface GridItem {
  label: string;
  value: string;
}
export interface StatsGridParams {
  template: "stats_grid";
  concept_text: string;
  grid_items: GridItem[];
}

/** Beat type: timeline — 3-6 dated events with year ≤6 chars, label ≤5 words */
export interface TimelineEvent {
  year: string;
  label: string;
}
export interface TimelineParams {
  template: "timeline";
  concept_text: string;
  timeline_events: TimelineEvent[];
}

/** Last beat — takeaway_text ≤12 words */
export interface TakeawayParams {
  template: "takeaway";
  takeaway_text: string;
}

/** Discriminated union of all beat param types */
export type BeatParams =
  | HookParams
  | PipelineParams
  | ComparisonParams
  | StatsGridParams
  | TimelineParams
  | TakeawayParams;

// ── Timing ────────────────────────────────────────────────────────────────────

/** One entry from narration_timing.json */
export interface TimingEntry {
  start: number;    // seconds from video start
  duration: number; // seconds this beat plays
  end: number;      // start + duration
  text?: string;    // narration text (informational only)
}

// ── Scene plan ────────────────────────────────────────────────────────────────

export interface BeatInfo {
  beat: number;         // 1-indexed
  template: BeatTemplate;
}

// ── Root props passed from animator.py via --props ────────────────────────────

export interface RemotionProps {
  /** Ordered beat list from scene_plan.json */
  beats: BeatInfo[];
  /** Per-beat visual params: key = "beat_1", "beat_2", ... */
  params: Record<string, BeatParams>;
  /** Narration timing: keys = "hook", "concept_1", ..., "takeaway_cta" */
  timing: Record<string, TimingEntry>;
  /** Filename of audio in remotion/public/ (e.g. "narration.wav") */
  audioSrc: string;
  /** Total frames = round(totalDuration * 30) */
  totalFrames: number;
}
