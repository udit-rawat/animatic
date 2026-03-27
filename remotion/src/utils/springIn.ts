/**
 * springIn.ts — shared spring animation utility
 *
 * Single source of truth for spring config and the Math.max(0, frame - delay)
 * guard. All animated primitives call springIn() instead of spring() directly.
 *
 * Motion contrast principle:
 *   - Structural chrome (backgrounds, borders, containers) → cut in at frame 0
 *   - Data values, metric numbers, key visuals → springIn()
 *   - Exit animations → never; cut to next beat cleanly
 */

import { spring, interpolate } from "remotion";

// ── Spring presets ─────────────────────────────────────────────────────────────

interface SpringConfig {
  damping: number;
  stiffness: number;
  overshootClamping: boolean;
}

/** Crisp entry for metric cards and data elements (default) */
const SPRING_CRISP: SpringConfig = { damping: 28, stiffness: 220, overshootClamping: true };

/** Slower reveal for hero numbers — more gravitas */
const SPRING_HERO:  SpringConfig = { damping: 28, stiffness: 180, overshootClamping: true };

/** Fast snap for structural elements that do need a hint of motion */
const SPRING_SNAP:  SpringConfig = { damping: 40, stiffness: 300, overshootClamping: true };

export type SpringPreset = "crisp" | "hero" | "snap";

const PRESET_MAP: Record<SpringPreset, SpringConfig> = {
  crisp: SPRING_CRISP,
  hero:  SPRING_HERO,
  snap:  SPRING_SNAP,
};

// ── Core utility ──────────────────────────────────────────────────────────────

/**
 * springIn — compute spring progress with delay guard.
 *
 * @param frame  - current beat-local frame (from useBeatFrame)
 * @param fps    - from useVideoConfig().fps
 * @param delay  - frame offset before spring starts (stagger)
 * @param preset - spring character: "crisp" | "hero" | "snap"
 * @returns      - spring progress 0→1
 */
export function springIn(
  frame: number,
  fps: number,
  delay: number = 0,
  preset: SpringPreset = "crisp",
): number {
  return spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: PRESET_MAP[preset],
  });
}

// ── Derived animation values ──────────────────────────────────────────────────

export interface SlideUpValues {
  opacity:    number;
  translateY: number;
}

/**
 * slideUp — standard card entrance: fade in + translate up 16px → 0.
 * Used by MetricCard, LabelValueCard, and any staggered list item.
 */
export function slideUp(
  frame: number,
  fps: number,
  delay: number = 0,
  preset: SpringPreset = "crisp",
): SlideUpValues {
  const progress = springIn(frame, fps, delay, preset);
  return {
    opacity:    interpolate(progress, [0, 0.15], [0, 1], { extrapolateRight: "clamp" }),
    translateY: interpolate(progress, [0, 1],    [16, 0]),
  };
}

export interface ScaleInValues {
  opacity: number;
  scale:   number;
}

/**
 * scaleIn — hero metric entrance: fade + scale 0.75 → 1.0.
 * Used by NumberCounter.
 */
export function scaleIn(
  frame: number,
  fps: number,
  delay: number = 0,
  preset: SpringPreset = "hero",
): ScaleInValues {
  const progress = springIn(frame, fps, delay, preset);
  return {
    opacity: interpolate(progress, [0, 0.15], [0, 1], { extrapolateRight: "clamp" }),
    scale:   interpolate(progress, [0, 1],    [0.75, 1.0]),
  };
}

export interface PopInValues {
  opacity: number;
  scale:   number;
}

/**
 * popIn — GPU node entrance: scale 0.85 → 1.0 with stagger.
 * Used by GPUNode.
 */
export function popIn(
  frame: number,
  fps: number,
  delay: number = 0,
): PopInValues {
  const progress = springIn(frame, fps, delay, "crisp");
  return {
    opacity: interpolate(progress, [0, 0.2], [0, 1], { extrapolateRight: "clamp" }),
    scale:   interpolate(progress, [0, 1],   [0.85, 1.0]),
  };
}

// ── Stagger utility ───────────────────────────────────────────────────────────

/**
 * staggerDelay — normalize stagger across any array size.
 *
 * Always produces the same total sweep duration regardless of item count.
 * With STAGGER_BUDGET=24: 2 items → delays [0, 12]; 8 items → [0,3,6,9,12,15,18,21]
 *
 * @param index         - 0-based item index
 * @param total         - total number of items
 * @param budgetFrames  - total frames for the whole sweep (default 24 = 0.8s)
 * @param baseDelay     - additional base offset applied to all items
 */
export function staggerDelay(
  index: number,
  total: number,
  budgetFrames: number = 24,
  baseDelay: number = 0,
): number {
  if (total <= 1) return baseDelay;
  return baseDelay + Math.round((index / total) * budgetFrames);
}
