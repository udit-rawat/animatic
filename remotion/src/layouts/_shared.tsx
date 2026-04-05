/**
 * _shared.tsx — design tokens, shared primitives, motion system.
 *
 * Palette: "Neon Cyber" — high-contrast, single signal accent
 *   cyan   → #00E5FF  Cyber Cyan   (primary anchor: borders, connectors, structure)
 *   yellow → #CCFF00  Acid Volt    (signal accent: ONE hero element per screen only)
 *   green  → #10B981  Emerald      (positive metrics)
 *   red    → #FF3366  Radium Red   (negative metrics, bottlenecks)
 *   white  → #F9FAFB
 *
 * Motion tiers (see springIn.ts for spring configs):
 *   HEAVY  — hook + takeaway hero elements. Visible overshoot.
 *   MEDIUM — concept beat cards and data. Single-frame overshoot.
 *   SOFT   — secondary text, labels. Clean landing, no bounce.
 *
 * Shared components:
 *   <ParticleBackground frame />   — 40-particle digital dust field (all templates)
 *   <TelemetryFrame frame />       — 1px perimeter border (brand signature, all templates)
 *   <SectionLabelRow />            — micro-label with left accent bar
 *   <HRule />                      — subtle horizontal rule
 *
 * Hooks:
 *   useBreath(frame, fps)          — 0.25 Hz ambient scale/opacity pulse
 */

import React from "react";
import { interpolate } from "remotion";
import type { NodeColor } from "../types";

// ── Design tokens ─────────────────────────────────────────────────────────────

export const COLOR: Record<NodeColor, string> = {
  cyan:   "#00E5FF",   // Cyber Cyan  — primary anchor
  yellow: "#CCFF00",   // Acid Volt   — signal accent (use for ONE element per screen)
  green:  "#10B981",   // Emerald     — positive metrics
  red:    "#FF3366",   // Radium Red  — negative metrics / bottlenecks
  white:  "#F9FAFB",
};

export const VIOLET = "#8B5CF6"; // Deep Violet — ambient backgrounds, particle tint

export const FONT = "'Inter', 'system-ui', sans-serif";

// ── Deterministic particle data (computed once, no Math.random) ───────────────

const frac = (v: number) => { const f = v - Math.floor(v); return f; };
const det  = (seed: number) => frac(Math.sin(seed) * 43758.5453);

export const PARTICLE_FIELD = Array.from({ length: 40 }, (_, i) => ({
  x:        det(i * 127.1) * 1080,
  y:        det(i * 311.7 + 99) * 1920,
  size:     1 + Math.round(det(i * 74.3 + 33) * 1.5), // 1–2 px
  xFreq:    0.007 + det(i * 53.1) * 0.005,             // X-axis sine frequency
  xAmp:     18 + det(i * 91.3) * 28,                   // X-axis amplitude (px)
  blurred:  i % 2 === 0,                               // faux depth-of-field
  isCyan:   i % 3 !== 2,                               // 2/3 cyan, 1/3 violet
}));

// ── ParticleBackground ────────────────────────────────────────────────────────

/**
 * Shared particle field. Drop inside any template as the first child.
 * 40 small squares drift upward at 0.3 px/frame on a slow sine X-axis.
 * Half are blurred for faux depth-of-field. Opacity 15% — never distracting.
 */
export const ParticleBackground: React.FC<{ frame: number }> = ({ frame }) => (
  <div style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
    {PARTICLE_FIELD.map((p, i) => {
      const top  = ((p.y - frame * 0.3) % 1920 + 1920) % 1920;
      const left = p.x + Math.sin(frame * p.xFreq) * p.xAmp;
      return (
        <div key={i} style={{
          position:     "absolute",
          left,
          top,
          width:        p.size,
          height:       p.size,
          background:   p.isCyan ? COLOR.cyan : VIOLET,
          opacity:      0.15,
          filter:       p.blurred ? "blur(1px)" : "none",
          pointerEvents:"none",
        }} />
      );
    })}
  </div>
);

// ── TelemetryFrame — brand signature ─────────────────────────────────────────

/**
 * 1px Cyber Cyan border around the video perimeter.
 * - Normal: 20% opacity — subtle HUD frame.
 * - First 15 frames (beat transition): spikes to 100%, Acid Volt streak sweeps top edge.
 * Drop inside every template as the last child (highest z-index).
 */
export const TelemetryFrame: React.FC<{ frame: number }> = ({ frame }) => {
  const isTransition = frame < 16;

  const borderOpacity = isTransition
    ? interpolate(frame, [0, 3, 10, 16], [1, 1, 0.55, 0.2], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0.2;

  // Acid Volt streak travels along the top edge during transition
  const streakLeft = isTransition
    ? interpolate(frame, [0, 15], [-8, 108], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 110;

  const streakOpacity = isTransition
    ? interpolate(frame, [0, 5, 13, 16], [0, 1, 1, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0;

  return (
    <div style={{
      position:     "absolute",
      inset:        0,
      border:       `1px solid rgba(0,229,255,${borderOpacity})`,
      borderRadius: 0,
      pointerEvents:"none",
      zIndex:       1000,
    }}>
      {/* Top-edge Acid Volt streak */}
      <div style={{
        position:   "absolute",
        top:        -1,
        left:       `${streakLeft}%`,
        transform:  "translateX(-50%)",
        width:      120,
        height:     2,
        background: `linear-gradient(90deg, transparent, ${COLOR.yellow}, transparent)`,
        opacity:    streakOpacity,
        filter:     `blur(1px) drop-shadow(0 0 6px ${COLOR.yellow})`,
      }} />
    </div>
  );
};

// ── Shared sub-components ─────────────────────────────────────────────────────

export const SectionLabelRow: React.FC<{
  text:   string;
  color?: NodeColor;
}> = ({ text, color = "cyan" }) => {
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
 * Apply to hero elements after their entrance spring settles (~frame 20+).
 */
export function useBreath(frame: number, fps: number) {
  const phase = (frame / fps) * Math.PI * 2 * 0.25;
  const sin   = Math.sin(phase);
  return {
    scale:        1 + sin * 0.012,
    opacityShift: sin * 0.04,
  };
}

// ── Count-up helper ───────────────────────────────────────────────────────────

/**
 * parseHeroValue — splits a formatted value string into numeric and decorative parts.
 * Examples: "400M" → {prefix:"", num:400, suffix:"M", decimals:0}
 *           "3.8×" → {prefix:"", num:3.8, suffix:"×", decimals:1}
 *           ">3B"  → {prefix:">", num:3,  suffix:"B", decimals:0}
 *           "90ms" → {prefix:"", num:90,  suffix:"ms", decimals:0}
 */
export function parseHeroValue(value: string) {
  const m = value.match(/^([^0-9.]*)([0-9]+(?:\.[0-9]+)?)(.*)$/);
  if (!m) return { prefix: "", num: 0, suffix: value, decimals: 0 };
  const decimals = m[2].includes(".") ? m[2].split(".")[1].length : 0;
  return { prefix: m[1], num: parseFloat(m[2]), suffix: m[3], decimals };
}

/**
 * countUp — returns a formatted display string that counts from 0 to target.
 * progress: 0→1 (use spring progress). Finishes counting at progress=0.88
 * so the number lands before the spring fully settles.
 */
export function countUp(value: string, progress: number): string {
  const { prefix, num, suffix, decimals } = parseHeroValue(value);
  if (num === 0) return value;
  const current = interpolate(progress, [0, 0.88], [0, num], { extrapolateRight: "clamp" });
  return `${prefix}${current.toFixed(decimals)}${suffix}`;
}
