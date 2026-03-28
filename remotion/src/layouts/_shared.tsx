/**
 * _shared.tsx — shared primitives and design tokens for Scene layouts.
 *
 * Layouts (ComparisonSplit, MetricFocus, etc.) import from here rather than
 * from LayoutRenderer so they are fully self-contained and don't depend on
 * the LayoutNode dispatcher. LayoutRenderer primitives remain unchanged.
 */

import React from "react";
import type { NodeColor } from "../types";

// ── Design tokens ─────────────────────────────────────────────────────────────

export const COLOR: Record<NodeColor, string> = {
  green:  "#10B981",
  cyan:   "#6366F1",
  yellow: "#8B5CF6",
  red:    "#EF4444",
  white:  "#F9FAFB",
};

export const FONT = "'Inter', 'system-ui', sans-serif";

// ── Shared sub-components ─────────────────────────────────────────────────────

export const SectionLabelRow: React.FC<{
  text:   string;
  color?: NodeColor;
}> = ({ text, color = "yellow" }) => {
  const c = COLOR[color];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, flexShrink: 0 }}>
      <div style={{ width: 3, height: 22, background: c, borderRadius: 2, opacity: 0.9 }} />
      <div style={{
        fontSize: 22, fontWeight: 600, color: c,
        fontFamily: FONT, letterSpacing: "0.12em",
        textTransform: "uppercase", opacity: 0.85,
      }}>
        {text}
      </div>
    </div>
  );
};

export const HRule: React.FC = () => (
  <div style={{ width: "100%", height: 1, background: "rgba(255,255,255,0.08)", flexShrink: 0 }} />
);

// ── Ambient breathing hook ────────────────────────────────────────────────────

/**
 * useBreath — continuous 0.25 Hz sinusoidal pulse.
 * Returns scale (1 ± 0.012) and opacityShift (± 0.04).
 * Apply to a container after its entrance animation completes so the element
 * "stays alive" rather than going static.
 */
export function useBreath(frame: number, fps: number) {
  const phase = (frame / fps) * Math.PI * 2 * 0.25; // 0.25 Hz
  const sin   = Math.sin(phase);
  return {
    scale:        1 + sin * 0.012,
    opacityShift: sin * 0.04,
  };
}
