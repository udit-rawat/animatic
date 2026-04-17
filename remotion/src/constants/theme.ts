// Single source of truth. All templates import from here.
// Neon Cyber palette — Devs + Technical Founders audience.

export const THEME = {
  // Background
  bg:      "radial-gradient(ellipse at 50% 50%, #111 0%, #0A0A0A 70%)",
  bgSolid: "#0A0A0A",

  // Colors — Neon Cyber
  cyan:    "#00E5FF",   // primary anchor — borders, connectors, structure
  yellow:  "#CCFF00",   // signal accent — ONE hero element per screen only
  green:   "#10B981",   // positive metrics
  red:     "#FF3366",   // negative metrics / bottlenecks
  white:   "#F9FAFB",
  muted:   "rgba(255,255,255,0.38)",
  violet:  "#8B5CF6",   // ambient backgrounds, particle tint

  // Typography
  font:     "'Space Grotesk', 'Inter', sans-serif",
  mono:     "'JetBrains Mono', 'Fira Code', monospace",
  heroSize: 280,    // px — primary stat. Never go below.
  bodySize: 56,     // px — subtext
  labelSize: 22,    // px — section labels

  // Layout
  safeX:    72,     // left/right padding
  safeYMin: 120,    // infographic top padding
  safeYMax: 180,    // infographic bottom padding

  // Caption zone — for Three.js template variants
  captionTop:    1240,   // y start for threejs text
  captionBottom: 1680,   // y end for threejs text

  // Effects
  noise:       0.035,
  gridOpacity: 0.04,
  gridSize:    "80px 80px",

  // Motion
  spring:       { damping: 14, mass: 0.7, stiffness: 200 },
  springMedium: { damping: 18, mass: 0.8, stiffness: 220 },
  springHeavy:  { damping: 22, mass: 1.0, stiffness: 180 },
  springFast:   { damping: 12, mass: 0.5, stiffness: 300 },
  springBounce: { damping: 8,  mass: 1.2, stiffness: 220 },
} as const;

export type Theme = typeof THEME;
