/**
 * CustomVideo.tsx — Meta Llama 4 Maverick  (v4 — real Meta logo + reel-sized text)
 * 1590 frames · 30fps · 53.0s
 *
 * [hook]      0–218     Meta ∞ SVG draw-in → "LLAMA 4" types → MAVERICK slams → hook line
 * [concept_1] 218–725   MoE expert grid → 2 illuminate → benchmark bars
 * [concept_2] 725–1237  Context bar fills to 1M → LMSYS leaderboard
 * [takeaway]  1237–1590 "Pull it." / "Run it." / "Own it." slam lines + Meta logo bookend
 */

import React, { useRef, useLayoutEffect } from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from "remotion";

// ── Frame budgets ─────────────────────────────────────────────────────────────

const HOOK_F     = 218;
const CONCEPT1_F = 507;
const CONCEPT2_F = 512;
const TAKEAWAY_F = 353;

export const CustomVideoConfig = {
  durationInFrames: HOOK_F + CONCEPT1_F + CONCEPT2_F + TAKEAWAY_F,
  fps: 30, width: 1080, height: 1920,
};

// ── Design tokens ─────────────────────────────────────────────────────────────

const META_BLUE  = "#0081FB";
const META_BLUE2 = "#0668E1";
const META_LIGHT = "#00B2FF";
const WHITE      = "#FFFFFF";
const DIM        = "#888888";
const BG         = "#000000";
const FONT       = "'Inter','system-ui',sans-serif";

const SPRING_HEAVY  = { damping: 12,  stiffness: 150, mass: 1.2, overshootClamping: false };
const SPRING_MEDIUM = { damping: 18,  stiffness: 220, mass: 1.0, overshootClamping: false };
const SPRING_SOFT   = { damping: 28,  stiffness: 200, mass: 1.0, overshootClamping: false };

const BROADCAST: React.CSSProperties = {
  fontFamily:          FONT,
  fontFeatureSettings: '"kern" 1, "liga" 1, "calt" 1',
  textRendering:       "geometricPrecision" as const,
  WebkitFontSmoothing: "antialiased",
  MozOsxFontSmoothing: "grayscale",
};

// ── Beat frame context ────────────────────────────────────────────────────────

const BeatFrameCtx = React.createContext(0);
const useBF = () => React.useContext(BeatFrameCtx);

// ── Telemetry border ──────────────────────────────────────────────────────────

const TelemetryBorder: React.FC<{ frame: number }> = ({ frame }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const W = 1080, H = 1920;
  useLayoutEffect(() => {
    const c = canvasRef.current; if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    const perim = 2 * (W + H);
    const offset = -(frame * 4) % perim;
    ctx.strokeStyle = "rgba(255,255,255,0.10)";
    ctx.lineWidth   = 1;
    ctx.setLineDash([60, perim - 60]);
    ctx.lineDashOffset = offset;
    ctx.strokeRect(1, 1, W - 2, H - 2);
    ctx.setLineDash([]);
  });
  return (
    <canvas ref={canvasRef} width={W} height={H}
      style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 10 }} />
  );
};

// ── Real Meta infinity logo — SVG strokeDashoffset draw-in ───────────────────
//
// Two overlapping ovals forming the Meta ∞ lemniscate.
// Gradient: #0668E1 → #0082FB → #00B2FF  (left→right, official Meta AI palette)
// strokeDashoffset animates total perimeter → 0 as progress goes 0→1.
// Glow pulse via CSS filter drop-shadow after draw completes.

const META_LOGO_PATH =
  "M 100,45 " +
  "C 100,24 84,12 65,12 " +   // right-center → top of left loop
  "C 42,12 22,26 22,45 " +    // top-left → left apex
  "C 22,64 42,78 65,78 " +    // left apex → bottom-left
  "C 84,78 100,66 100,45 " +  // bottom of left loop → center cross
  "C 100,24 116,12 135,12 " + // center cross → top of right loop
  "C 158,12 178,26 178,45 " + // top-right → right apex
  "C 178,64 158,78 135,78 " + // right apex → bottom-right
  "C 116,78 100,66 100,45 Z"; // bottom of right loop → center close

// Approximate total perimeter of the path above
const META_PERIMETER = 560;

const MetaLogo: React.FC<{
  frame:    number;
  progress: number;
  size?:    number;   // height of the SVG in px
  showWord?: boolean; // whether to show "meta" wordmark below
}> = ({ frame, progress, size = 180, showWord = true }) => {
  const vbW = 200, vbH = 90;
  const svgW = (vbW / vbH) * size;
  const dashOffset = META_PERIMETER * (1 - Math.min(progress, 1));

  const glow = progress > 0.92
    ? 10 + (Math.sin((frame / 30) * Math.PI * 2 * 0.45) * 0.5 + 0.5) * 24
    : 0;

  const wordOp = interpolate(progress, [0.75, 1.0], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
      <svg
        width={svgW}
        height={size}
        viewBox={`0 0 ${vbW} ${vbH}`}
        style={{ filter: glow > 0 ? `drop-shadow(0 0 ${glow}px ${META_BLUE})` : "none", overflow: "visible" }}
      >
        <defs>
          <linearGradient id="metaInfGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor={META_BLUE2} />
            <stop offset="50%"  stopColor={META_BLUE}  />
            <stop offset="100%" stopColor={META_LIGHT} />
          </linearGradient>
        </defs>
        <path
          d={META_LOGO_PATH}
          fill="none"
          stroke="url(#metaInfGrad)"
          strokeWidth="9"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={META_PERIMETER}
          strokeDashoffset={dashOffset}
        />
      </svg>
      {showWord && (
        <div style={{
          opacity:       wordOp,
          ...BROADCAST,
          fontSize:      size * 0.26,
          fontWeight:    700,
          color:         WHITE,
          letterSpacing: "0.10em",
          textTransform: "lowercase" as const,
        }}>
          meta
        </div>
      )}
    </div>
  );
};

// ── Underline draw-in ─────────────────────────────────────────────────────────

const UnderlineDraw: React.FC<{ progress: number; width: number; color?: string }> = ({
  progress, width, color = META_BLUE,
}) => (
  <div style={{
    height:          3,
    width:           width,
    background:      `linear-gradient(90deg, ${color}, ${color}60)`,
    transformOrigin: "left center",
    transform:       `scaleX(${progress})`,
    marginTop:       10,
    borderRadius:    2,
    boxShadow:       `0 0 8px ${color}60`,
  }} />
);

// ── Benchmark bar ─────────────────────────────────────────────────────────────

const BenchBar: React.FC<{
  label:     string;
  value:     number;
  maxValue?: number;
  color:     string;
  frame:     number;
  delay:     number;
  fps:       number;
  highlight?: boolean;
}> = ({ label, value, maxValue = 100, color, frame, delay, fps, highlight }) => {
  const prog = spring({ frame: Math.max(0, frame - delay), fps, config: SPRING_MEDIUM });
  const barW = interpolate(prog, [0, 1], [0, value / maxValue], { extrapolateRight: "clamp" });
  const op   = interpolate(prog, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{ opacity: op, marginBottom: 28 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ ...BROADCAST, fontSize: 28, color: highlight ? WHITE : DIM, fontWeight: highlight ? 600 : 400 }}>
          {label}
        </span>
        <span style={{ ...BROADCAST, fontSize: 28, color, fontWeight: 700, fontVariantNumeric: "tabular-nums" as const }}>
          {value}
        </span>
      </div>
      <div style={{ height: 8, background: "#1a1a1a", borderRadius: 4 }}>
        <div style={{
          height:       "100%",
          width:        `${barW * 100}%`,
          background:   highlight ? `linear-gradient(90deg, ${META_BLUE2}, ${META_BLUE})` : "#2a2a2a",
          borderRadius: 4,
          boxShadow:    highlight ? `0 0 14px ${META_BLUE}60` : "none",
        }} />
      </div>
    </div>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// BEAT 1 — HOOK
// ══════════════════════════════════════════════════════════════════════════════

const HookBeat: React.FC = () => {
  const frame = useBF();
  const fps   = 30;

  // Meta logo draw-in: frames 0→70
  const logoProgress = interpolate(frame, [0, 70], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // "LLAMA 4" typewriter: starts frame 55
  const LLAMA_STR    = "LLAMA 4";
  const charsVisible = Math.min(LLAMA_STR.length, Math.max(0, Math.floor((frame - 55) * 0.38)));
  const cursorOn     = frame > 55 && charsVisible < LLAMA_STR.length && Math.floor(frame / 12) % 2 === 0;

  // MAVERICK slam: SPRING_HEAVY from frame 95
  const mavProg   = spring({ frame: Math.max(0, frame - 95), fps, config: SPRING_HEAVY });
  const mavScale  = interpolate(mavProg, [0, 1], [0.3, 1], { extrapolateRight: "clamp" });
  const mavOp     = interpolate(mavProg, [0, 0.12], [0, 1], { extrapolateRight: "clamp" });

  // Blue underline draws from frame 138
  const ulProg     = spring({ frame: Math.max(0, frame - 138), fps, config: SPRING_SOFT });
  const ulProgress = interpolate(ulProg, [0, 1], [0, 1], { extrapolateRight: "clamp" });

  // Hook line fades in frame 162
  const hookOp = interpolate(frame, [162, 192], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{
      background:     BG,
      display:        "flex",
      flexDirection:  "column",
      alignItems:     "center",
      justifyContent: "center",
      fontFamily:     FONT,
      gap:            0,
    }}>
      <TelemetryBorder frame={frame} />

      {/* Real Meta infinity logo */}
      <div style={{ marginBottom: 52 }}>
        <MetaLogo frame={frame} progress={logoProgress} size={180} showWord />
      </div>

      {/* "LLAMA 4" typewriter */}
      <div style={{ marginBottom: 24, minHeight: 72 }}>
        <span style={{
          ...BROADCAST, fontSize: 58, fontWeight: 300,
          color: DIM, letterSpacing: "0.20em",
        }}>
          {LLAMA_STR.slice(0, charsVisible)}
          {cursorOn && <span style={{ color: META_BLUE }}>|</span>}
        </span>
      </div>

      {/* MAVERICK hero slam */}
      <div style={{
        opacity:         mavOp,
        transform:       `scale(${mavScale})`,
        transformOrigin: "center center",
        display:         "flex",
        flexDirection:   "column",
        alignItems:      "center",
        marginBottom:    56,
      }}>
        <div style={{
          ...BROADCAST,
          fontSize:      168,
          fontWeight:    900,
          color:         WHITE,
          letterSpacing: "-0.04em",
          lineHeight:    1,
        }}>
          MAVERICK
        </div>
        <UnderlineDraw progress={ulProgress} width={840} />
      </div>

      {/* Hook line */}
      <div style={{ opacity: hookOp, maxWidth: 840, textAlign: "center" as const, padding: "0 60px" }}>
        <div style={{ ...BROADCAST, fontSize: 34, color: DIM, lineHeight: 1.55, fontWeight: 400 }}>
          Most capable open model yet.
          <br />Runs on hardware you actually own.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// BEAT 2 — CONCEPT 1: MoE diagram + benchmark bars
// ══════════════════════════════════════════════════════════════════════════════

const Concept1Beat: React.FC = () => {
  const frame = useBF();
  const fps   = 30;

  const labelOp = interpolate(frame, [0, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const EXPERTS     = 8;
  const ACTIVE_IDXS = [2, 5];
  const BOX_SIZE    = 100;
  const BOX_GAP     = 14;
  const ILLUM_F     = 100;
  const BENCH_F     = 210;

  const line1Op = interpolate(frame, [32,  58],  [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const line2Op = interpolate(frame, [105, 130], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const divOp   = interpolate(frame, [BENCH_F - 20, BENCH_F], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const benchmarks = [
    { label: "Maverick",     value: 88, color: META_BLUE, highlight: true  },
    { label: "GPT-4o",       value: 82, color: DIM,       highlight: false },
    { label: "Gemini Flash", value: 76, color: DIM,       highlight: false },
  ];

  return (
    <AbsoluteFill style={{
      background: BG, display: "flex", flexDirection: "column",
      padding: "80px 72px", boxSizing: "border-box", fontFamily: FONT,
    }}>
      <TelemetryBorder frame={frame} />

      {/* Section label */}
      <div style={{ opacity: labelOp, marginBottom: 44 }}>
        <div style={{ ...BROADCAST, fontSize: 18, color: META_BLUE, letterSpacing: "0.22em", textTransform: "uppercase" as const, marginBottom: 10 }}>
          Architecture
        </div>
        <div style={{ ...BROADCAST, fontSize: 52, fontWeight: 700, color: WHITE, lineHeight: 1.15 }}>
          Mixture of Experts
        </div>
      </div>

      {/* Expert grid */}
      <div style={{
        display:             "grid",
        gridTemplateColumns: `repeat(${EXPERTS}, ${BOX_SIZE}px)`,
        gap:                 BOX_GAP,
        marginBottom:        36,
        justifyContent:      "center",
      }}>
        {Array.from({ length: EXPERTS }, (_, i) => {
          const boxProg    = spring({ frame: Math.max(0, frame - i * 8), fps, config: SPRING_MEDIUM });
          const boxOp      = interpolate(boxProg, [0, 0.25], [0, 1], { extrapolateRight: "clamp" });
          const boxScale   = interpolate(boxProg, [0, 1], [0.5, 1], { extrapolateRight: "clamp" });
          const isActive   = ACTIVE_IDXS.includes(i);
          const illumProg  = isActive
            ? spring({ frame: Math.max(0, frame - ILLUM_F - i * 8), fps, config: SPRING_SOFT })
            : 0;
          const illumAlpha = interpolate(illumProg, [0, 1], [0, 1], { extrapolateRight: "clamp" });
          const illumBg    = interpolate(illumProg, [0, 1], [0, 0.16], { extrapolateRight: "clamp" });

          return (
            <div key={i} style={{
              opacity:       boxOp,
              transform:     `scale(${boxScale})`,
              width:         BOX_SIZE,
              height:        BOX_SIZE,
              borderRadius:  12,
              border:        `1.5px solid ${isActive ? `rgba(0,129,251,${illumAlpha})` : "rgba(255,255,255,0.12)"}`,
              background:    isActive ? `rgba(0,129,251,${illumBg})` : "rgba(255,255,255,0.03)",
              display:       "flex",
              alignItems:    "center",
              justifyContent:"center",
              boxShadow:     isActive && illumProg > 0.5 ? `0 0 24px ${META_BLUE}40` : "none",
              transition:    "none",
            }}>
              <div style={{
                ...BROADCAST, fontSize: 18,
                color:      isActive ? META_BLUE : "rgba(255,255,255,0.22)",
                fontWeight: isActive ? 700 : 400,
              }}>
                E{i + 1}
              </div>
            </div>
          );
        })}
      </div>

      {/* Annotation lines */}
      <div style={{ opacity: line1Op, marginBottom: 12 }}>
        <div style={{ ...BROADCAST, fontSize: 30, color: DIM, lineHeight: 1.5 }}>
          128 experts total —{" "}
          <span style={{ color: WHITE, fontWeight: 600 }}>only 2 activate per token</span>
        </div>
      </div>
      <div style={{ opacity: line2Op, marginBottom: 36 }}>
        <div style={{ ...BROADCAST, fontSize: 30, color: DIM, lineHeight: 1.5 }}>
          Fast and efficient. Beats models 10× its size.
        </div>
      </div>

      {/* Divider */}
      <div style={{ opacity: divOp, height: 1, background: "rgba(255,255,255,0.08)", marginBottom: 36 }} />

      {/* Benchmark bars */}
      <div style={{ opacity: divOp }}>
        <div style={{ ...BROADCAST, fontSize: 18, color: DIM, letterSpacing: "0.18em", textTransform: "uppercase" as const, marginBottom: 28 }}>
          Coding · Reasoning · Vision — Overall Score
        </div>
        {benchmarks.map((b, i) => (
          <BenchBar key={b.label} {...b} frame={frame} delay={BENCH_F + i * 20} fps={fps} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// BEAT 3 — CONCEPT 2: Context window + LMSYS leaderboard
// ══════════════════════════════════════════════════════════════════════════════

const ContextFillCanvas: React.FC<{ frame: number; progress: number }> = ({ frame, progress }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const W = 936, H = 88;

  useLayoutEffect(() => {
    const c = canvasRef.current; if (!c) return;
    const ctx = c.getContext("2d"); if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    const r = 10;
    ctx.save();
    ctx.fillStyle = "#111";
    ctx.beginPath(); ctx.roundRect(0, 0, W, H, r); ctx.fill();
    ctx.restore();

    const fillW = W * progress;
    if (fillW > 0) {
      const grad = ctx.createLinearGradient(0, 0, fillW, 0);
      grad.addColorStop(0,   META_BLUE2 + "80");
      grad.addColorStop(0.7, META_BLUE);
      grad.addColorStop(1,   META_LIGHT);
      ctx.save();
      ctx.shadowBlur  = 24;
      ctx.shadowColor = META_BLUE + "60";
      ctx.fillStyle   = grad;
      ctx.beginPath(); ctx.roundRect(0, 0, W, H, r); ctx.clip();
      ctx.beginPath(); ctx.roundRect(0, 0, fillW, H, r); ctx.fill();
      ctx.restore();
    }
  });

  return (
    <canvas ref={canvasRef} width={W} height={H}
      style={{ display: "block", width: "100%", borderRadius: 10 }} />
  );
};

const LMSYS_ENTRIES = [
  { name: "Maverick (chat)",   score: 1417, color: META_BLUE, highlight: true  },
  { name: "GPT-4.1",           score: 1399, color: DIM,       highlight: false },
  { name: "DeepSeek V3",       score: 1381, color: DIM,       highlight: false },
  { name: "Gemini 2.0 Flash",  score: 1354, color: DIM,       highlight: false },
  { name: "Claude 3.5 Sonnet", score: 1328, color: DIM,       highlight: false },
];
const MAX_SCORE = 1450;

const Concept2Beat: React.FC = () => {
  const frame = useBF();
  const fps   = 30;

  const ctxProg    = spring({ frame: Math.max(0, frame - 20), fps, config: { damping: 32, stiffness: 80, mass: 1, overshootClamping: true } });
  const ctxFill    = interpolate(ctxProg, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const tokenCount = Math.round(ctxFill * 1_000_000);
  const labelOp    = interpolate(frame, [0, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const LB_START = 210;
  const lbOp  = interpolate(frame, [LB_START, LB_START + 25], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const mmOp  = interpolate(frame, [260, 285], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: BG, display: "flex", flexDirection: "column",
      padding: "80px 72px", boxSizing: "border-box", fontFamily: FONT,
    }}>
      <TelemetryBorder frame={frame} />

      {/* Context window */}
      <div style={{ opacity: labelOp, marginBottom: 36 }}>
        <div style={{ ...BROADCAST, fontSize: 18, color: META_BLUE, letterSpacing: "0.22em", textTransform: "uppercase" as const, marginBottom: 10 }}>
          Context Window
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 18, marginBottom: 22 }}>
          <div style={{ ...BROADCAST, fontSize: 100, fontWeight: 900, color: WHITE, letterSpacing: "-0.04em", fontVariantNumeric: "tabular-nums" as const }}>
            {tokenCount >= 1_000_000 ? "1M" : (tokenCount / 1000).toFixed(0) + "K"}
          </div>
          <div style={{ ...BROADCAST, fontSize: 30, color: DIM, fontWeight: 400 }}>tokens</div>
        </div>
        <ContextFillCanvas frame={frame} progress={ctxFill} />
        <div style={{ ...BROADCAST, fontSize: 26, color: "rgba(255,255,255,0.35)", marginTop: 14 }}>
          Entire codebases, long documents, multi-image inputs.
        </div>
      </div>

      {/* Capability badges */}
      <div style={{ opacity: mmOp, display: "flex", gap: 14, marginBottom: 44, flexWrap: "wrap" as const }}>
        {["Native Vision", "Multi-Image", "Docs + Code"].map(tag => (
          <div key={tag} style={{
            ...BROADCAST, fontSize: 20, color: META_BLUE, fontWeight: 600,
            border: `1px solid ${META_BLUE}40`, borderRadius: 8,
            padding: "8px 18px", background: `${META_BLUE}0A`,
          }}>
            {tag}
          </div>
        ))}
      </div>

      {/* Divider */}
      <div style={{ opacity: lbOp, height: 1, background: "rgba(255,255,255,0.08)", marginBottom: 36 }} />

      {/* LMSYS leaderboard */}
      <div style={{ opacity: lbOp }}>
        <div style={{ ...BROADCAST, fontSize: 18, color: DIM, letterSpacing: "0.18em", textTransform: "uppercase" as const, marginBottom: 28 }}>
          LMSYS Chatbot Arena — Elo Score
        </div>
        {LMSYS_ENTRIES.map((e, i) => {
          const prog  = spring({ frame: Math.max(0, frame - LB_START - i * 24), fps, config: SPRING_MEDIUM });
          const barW  = interpolate(prog, [0, 1], [0, e.score / MAX_SCORE], { extrapolateRight: "clamp" });
          const rowOp = interpolate(prog, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });

          return (
            <div key={e.name} style={{ opacity: rowOp, marginBottom: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ ...BROADCAST, fontSize: 26, color: e.highlight ? WHITE : DIM, fontWeight: e.highlight ? 600 : 400 }}>
                  {e.name}
                </span>
                <span style={{ ...BROADCAST, fontSize: 26, color: e.color, fontWeight: 700, fontVariantNumeric: "tabular-nums" as const }}>
                  {e.score}
                </span>
              </div>
              <div style={{ height: 7, background: "#1a1a1a", borderRadius: 4 }}>
                <div style={{
                  height:       "100%",
                  width:        `${barW * 100}%`,
                  background:   e.highlight ? `linear-gradient(90deg, ${META_BLUE2}, ${META_BLUE})` : "#2a2a2a",
                  borderRadius: 4,
                  boxShadow:    e.highlight ? `0 0 12px ${META_BLUE}50` : "none",
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// BEAT 4 — TAKEAWAY
// ══════════════════════════════════════════════════════════════════════════════

const TAKEAWAY_LINES = [
  { text: "Pull it.",  delay: 0   },
  { text: "Run it.",   delay: 60  },
  { text: "Own it.",   delay: 120 },
];

const SUBLINES = [
  { text: "Open weights. No API key.",         delay: 30  },
  { text: "Your hardware. Your inference.",    delay: 90  },
  { text: "No subscription. No lock-in.",      delay: 150 },
];

const TakeawayBeat: React.FC = () => {
  const frame = useBF();
  const fps   = 30;

  const secLabelOp = interpolate(frame, [0, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const mBookOp    = interpolate(frame, [210, 240], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const mDrawProg  = interpolate(frame, [210, 272], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ctaOp      = interpolate(frame, [265, 295], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background:    BG,
      display:       "flex",
      flexDirection: "column",
      padding:       "80px 72px",
      boxSizing:     "border-box",
      fontFamily:    FONT,
      justifyContent:"center",
    }}>
      <TelemetryBorder frame={frame} />

      {/* Section label */}
      <div style={{ opacity: secLabelOp, marginBottom: 52 }}>
        <div style={{ ...BROADCAST, fontSize: 18, color: META_BLUE, letterSpacing: "0.22em", textTransform: "uppercase" as const }}>
          Takeaway
        </div>
      </div>

      {/* Three slam lines */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {TAKEAWAY_LINES.map((line, i) => {
          const prog   = spring({ frame: Math.max(0, frame - line.delay), fps, config: SPRING_HEAVY });
          const lineY  = interpolate(prog, [0, 1], [70, 0], { extrapolateRight: "clamp" });
          const lineOp = interpolate(prog, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });
          const ulProg = spring({ frame: Math.max(0, frame - line.delay - 20), fps, config: SPRING_SOFT });
          const ulW    = interpolate(ulProg, [0, 1], [0, 1], { extrapolateRight: "clamp" });

          const sub    = SUBLINES[i];
          const subP   = spring({ frame: Math.max(0, frame - sub.delay), fps, config: SPRING_SOFT });
          const subOp  = interpolate(subP, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });

          // Underline pixel width based on text (each char ~60px at 130px fontSize)
          const ulPx = line.text.length * 60;

          return (
            <div key={i} style={{ marginBottom: 44 }}>
              <div style={{ opacity: lineOp, transform: `translateY(${lineY}px)` }}>
                <div style={{
                  ...BROADCAST,
                  fontSize:      130,
                  fontWeight:    900,
                  color:         WHITE,
                  letterSpacing: "-0.03em",
                  lineHeight:    1,
                }}>
                  {line.text}
                </div>
                <UnderlineDraw progress={ulW} width={ulPx} />
              </div>
              <div style={{ opacity: subOp, marginTop: 12, paddingLeft: 3 }}>
                <div style={{ ...BROADCAST, fontSize: 30, color: DIM, fontWeight: 400 }}>
                  {sub.text}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Meta logo bookend */}
      <div style={{ opacity: mBookOp, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
        <MetaLogo frame={frame} progress={mDrawProg} size={120} showWord={false} />
        <div style={{ opacity: ctaOp, ...BROADCAST, fontSize: 26, color: DIM, letterSpacing: "0.10em" }}>
          Follow for daily AI breakdowns
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
// ROOT COMPOSITION
// ══════════════════════════════════════════════════════════════════════════════

export const CustomVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const bf    = (start: number) => frame - start;

  return (
    <AbsoluteFill style={{ background: BG }}>
      <Audio src={staticFile("narration.wav")} />

      <Sequence from={0} durationInFrames={HOOK_F}>
        <BeatFrameCtx.Provider value={bf(0)}>
          <HookBeat />
        </BeatFrameCtx.Provider>
      </Sequence>

      <Sequence from={HOOK_F} durationInFrames={CONCEPT1_F}>
        <BeatFrameCtx.Provider value={bf(HOOK_F)}>
          <Concept1Beat />
        </BeatFrameCtx.Provider>
      </Sequence>

      <Sequence from={HOOK_F + CONCEPT1_F} durationInFrames={CONCEPT2_F}>
        <BeatFrameCtx.Provider value={bf(HOOK_F + CONCEPT1_F)}>
          <Concept2Beat />
        </BeatFrameCtx.Provider>
      </Sequence>

      <Sequence from={HOOK_F + CONCEPT1_F + CONCEPT2_F} durationInFrames={TAKEAWAY_F}>
        <BeatFrameCtx.Provider value={bf(HOOK_F + CONCEPT1_F + CONCEPT2_F)}>
          <TakeawayBeat />
        </BeatFrameCtx.Provider>
      </Sequence>
    </AbsoluteFill>
  );
};
