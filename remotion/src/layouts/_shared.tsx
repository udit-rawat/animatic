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

import React, { useRef, useLayoutEffect } from "react";
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

// ── Broadcast-grade typography styles ─────────────────────────────────────────
// Apply to all text elements for optical precision matching broadcast graphics.

export const BROADCAST_TEXT: React.CSSProperties = {
  fontFamily:             FONT,
  fontFeatureSettings:    '"kern" 1, "liga" 1, "calt" 1, "ss01" 1',
  fontOpticalSizing:      "auto" as const,
  textRendering:          "geometricPrecision" as const,
  WebkitFontSmoothing:    "antialiased",
  MozOsxFontSmoothing:    "grayscale",
};

/** Use on large numerals and hero values (tabular-nums prevents width jitter on count-ups). */
export const HERO_NUMBER: React.CSSProperties = {
  ...BROADCAST_TEXT,
  fontVariantNumeric: "tabular-nums",
  letterSpacing:      "-0.04em",
};

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
 * Shared particle field — canvas implementation.
 * 40 DOM nodes → 1 canvas element. Canvas shadowBlur = GPU-composited gaussian,
 * not software CSS blur. Circular particles instead of 1px square divs.
 * useLayoutEffect fires synchronously pre-paint — Remotion Puppeteer screenshots after.
 */
export const ParticleBackground: React.FC<{ frame: number }> = ({ frame }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, 1080, 1920);

    for (const p of PARTICLE_FIELD) {
      const top  = ((p.y - frame * 0.3) % 1920 + 1920) % 1920;
      const left = p.x + Math.sin(frame * p.xFreq) * p.xAmp;
      const color = p.isCyan ? COLOR.cyan : VIOLET;

      ctx.save();

      if (p.blurred) {
        // Depth-of-field tier: soft glow, lower opacity
        ctx.globalAlpha = 0.08;
        ctx.shadowBlur  = 6;
        ctx.shadowColor = color;
      } else {
        // Sharp tier: crisp dot with tight GPU glow
        ctx.globalAlpha = 0.18;
        ctx.shadowBlur  = 3;
        ctx.shadowColor = color;
      }

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(left, top, p.size * 0.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  });

  return (
    <canvas
      ref={canvasRef}
      width={1080}
      height={1920}
      style={{
        position:      "absolute",
        inset:         0,
        pointerEvents: "none",
        zIndex:        0,
      }}
    />
  );
};

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
        ...BROADCAST_TEXT,
        fontSize: 22, fontWeight: 600, color: c,
        letterSpacing: "0.12em",
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

// ── Specular shimmer utility ──────────────────────────────────────────────────

/**
 * shimmerStyle — angle-aware specular highlight replacing the flat white smear.
 * Narrow bright core (peak 20% opacity) with soft falloff either side.
 * Matches real glass/metal specularity: bright centre, fast falloff.
 *
 * shimmerPos: -20 → 120 (percentage left offset)
 */
export function shimmerStyle(shimmerPos: number): React.CSSProperties {
  return {
    position:      "absolute",
    inset:         0,
    left:          `${shimmerPos}%`,
    width:         "22%",
    background:    [
      "linear-gradient(90deg,",
      "  transparent 0%,",
      "  rgba(255,255,255,0.02) 20%,",
      "  rgba(255,255,255,0.12) 45%,",
      "  rgba(255,255,255,0.20) 50%,",
      "  rgba(255,255,255,0.12) 55%,",
      "  rgba(255,255,255,0.02) 80%,",
      "  transparent 100%",
      ")",
    ].join(""),
    transform:     "skewX(-18deg)",
    pointerEvents: "none",
  };
}

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
