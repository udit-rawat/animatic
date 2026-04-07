/**
 * CustomVideo.tsx — AMD: "The Million Token Barrier Just Fell for Agentic Workflows"
 * 1187 frames · 30fps · 39.6s
 *
 * [hook]      frames   0–207   6.9s  AMD logo draw-in → red barrier → SHATTER + camera shake → 1M slam
 * [concept_1] frames 207–622  13.8s  ComparisonSplit — MI300X vs MI355X, AMD green laser divider
 * [concept_2] frames 622–966  11.5s  Before/After stacked cards — latency bottleneck eliminated
 * [takeaway]  frames 966–1187  7.4s  Blur word-reveal + AMD green radial bg + AdaMax CTA
 */

import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { BeatFrameContext } from "./hooks/useBeatFrame";
import { COLOR, FONT, ParticleBackground, TelemetryFrame } from "./layouts/_shared";
import { SPRING_HEAVY, SPRING_MEDIUM } from "./utils/springIn";

// ── Frame budgets ─────────────────────────────────────────────────────────────

const HOOK_F     = 207;
const CONCEPT1_F = 415;   // 622 - 207
const CONCEPT2_F = 344;   // 966 - 622
const TAKEAWAY_F = 221;   // 1187 - 966

export const CustomVideoConfig = {
  durationInFrames: HOOK_F + CONCEPT1_F + CONCEPT2_F + TAKEAWAY_F,
  fps:    30,
  width:  1080,
  height: 1920,
};

// ── Beat wrapper ──────────────────────────────────────────────────────────────

const Beat: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <BeatFrameContext.Provider value={{ beatStartFrame: 0 }}>
    {children}
  </BeatFrameContext.Provider>
);

// ── Design tokens ─────────────────────────────────────────────────────────────

const AMD_GREEN = "#00B050";   // AMD brand green
const RED       = "#FF3366";   // Barrier / pain / legacy
const YELLOW    = "#CCFF00";   // Acid Volt — number slam
const CYAN      = COLOR.cyan;  // #00E5FF — throughput accent
const BG        = "#030A03";   // Near-black, green-tinted

// ── AMD Logo Mark (TSX SVG with strokeDashoffset draw-in) ─────────────────────

const AMDLogo: React.FC<{ size: number; frame: number; drawProgress: number }> = ({
  size, frame, drawProgress,
}) => {
  const fillOpacity = interpolate(drawProgress, [0.62, 1.0], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const glowPulse  = Math.sin((frame / 30) * Math.PI * 2 * 0.5) * 0.5 + 0.5;
  const glow       = 14 + glowPulse * 32;

  // Logo mark: square frame with arrow notch (top-right corner cut)
  // Path: start bottom-left, go up, right to notch point, diagonal to notch corner, down, left back
  const markPath  = "M 8,72 L 8,8 L 52,8 L 72,28 L 72,72 Z";
  const notchPath = "M 52,8 L 72,8 L 72,28 Z"; // the cut-away triangle
  const arrowDot  = "M 55,20 L 68,20 L 68,40 L 55,40 Z"; // inner detail

  const pathLen   = 260; // approximate perimeter of markPath
  const dashOff   = interpolate(drawProgress, [0, 0.65], [pathLen, 0], { extrapolateRight: "clamp" });

  const wordOp    = interpolate(drawProgress, [0.55, 0.9], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
      filter: `drop-shadow(0 0 ${glow}px ${AMD_GREEN}99)`,
    }}>
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 80 80">
        {/* Fill — fades in once draw nears completion */}
        <path d={markPath} fill={AMD_GREEN} fillOpacity={fillOpacity} />
        {/* Notch cutout — background color */}
        <path d={notchPath} fill={BG} fillOpacity={fillOpacity} />
        {/* Inner arrow detail */}
        <path d={arrowDot} fill={AMD_GREEN} fillOpacity={fillOpacity * 0.45} />
        {/* Stroke draw-in animation */}
        <path
          d={markPath}
          fill="none"
          stroke={AMD_GREEN}
          strokeWidth="3.5"
          strokeDasharray={`${pathLen}`}
          strokeDashoffset={dashOff}
          strokeLinejoin="round"
        />
      </svg>

      {/* Wordmark */}
      <div style={{
        fontSize: size * 0.72, fontWeight: 900, color: AMD_GREEN,
        fontFamily: FONT, letterSpacing: "0.12em", lineHeight: 1,
        opacity: wordOp,
        textShadow: `0 0 ${glow}px ${AMD_GREEN}80`,
      }}>
        AMD
      </div>
    </div>
  );
};

// ── Barrier shatter fragment ──────────────────────────────────────────────────

// 8 deterministic fragments seeded by index — no Math.random()
const FRAGMENT_SEEDS = [
  { dx: -380, dy: -120, rot: -45 },
  { dx: -260, dy: -200, rot: -120 },
  { dx: -80,  dy: -260, rot: 30  },
  { dx: 120,  dy: -180, rot: 90  },
  { dx: 300,  dy: -140, rot: -60 },
  { dx: 420,  dy: -60,  rot: 150 },
  { dx: 180,  dy: -300, rot: -30 },
  { dx: -150, dy: -320, rot: 80  },
];

const BarrierFragment: React.FC<{
  seed: typeof FRAGMENT_SEEDS[0]; progress: number; i: number;
}> = ({ seed, progress, i }) => {
  const x      = interpolate(progress, [0, 1], [0, seed.dx]);
  const y      = interpolate(progress, [0, 1], [0, seed.dy]);
  const rotate = interpolate(progress, [0, 1], [0, seed.rot]);
  const op     = interpolate(progress, [0, 0.15, 0.7, 1], [1, 1, 0.4, 0]);
  const w      = 24 + (i % 3) * 18;
  const h      = 6  + (i % 2) * 4;

  return (
    <div style={{
      position: "absolute",
      width: w, height: h,
      background: RED,
      borderRadius: 2,
      opacity: op,
      transform: `translate(${x}px, ${y}px) rotate(${rotate}deg)`,
      boxShadow: `0 0 8px ${RED}80`,
      transformOrigin: "center center",
    }} />
  );
};

// ── Hook Beat ─────────────────────────────────────────────────────────────────

const SHATTER_FRAME = 108; // local frame when logo hits barrier

const HookBeat: React.FC = () => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── AMD logo draw-in (frames 0–70)
  const logoProg    = spring({ frame: Math.max(0, frame), fps, config: SPRING_MEDIUM });
  const logoScale   = interpolate(logoProg, [0, 1], [0.5, 1]);
  const logoOp      = interpolate(logoProg, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });
  const drawProgress = interpolate(Math.max(0, frame), [0, 55], [0, 1], { extrapolateRight: "clamp" });

  // ── Red barrier slides in from right at frame 50
  const barrierProg = spring({ frame: Math.max(0, frame - 50), fps, config: SPRING_MEDIUM });
  const barrierX    = interpolate(barrierProg, [0, 1], [600, 0]);
  const barrierOp   = interpolate(barrierProg, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });
  // Barrier hides on shatter
  const barrierHide = interpolate(
    Math.max(0, frame - SHATTER_FRAME),
    [0, 3], [1, 0], { extrapolateRight: "clamp" }
  );

  // ── Logo scales into barrier — stiffness 200, physical impact
  const impactProg  = spring({ frame: Math.max(0, frame - 78), fps, config: { stiffness: 200, damping: 15, mass: 1 } });
  const impactScale = interpolate(impactProg, [0, 1], [1, 2.4]);
  const logoFinalOp = interpolate(Math.max(0, frame - SHATTER_FRAME + 2), [0, 5], [1, 0], { extrapolateRight: "clamp" });

  // ── Shatter fragments — activate at SHATTER_FRAME
  const shatterProg = spring({ frame: Math.max(0, frame - SHATTER_FRAME), fps, config: SPRING_HEAVY });

  // ── Camera shake — 5 frames at SHATTER_FRAME
  const shakeActive = frame >= SHATTER_FRAME && frame < SHATTER_FRAME + 5;
  const shakeX      = shakeActive ? Math.sin(frame * 173.7) * 12 : 0;
  const shakeY      = shakeActive ? Math.cos(frame * 241.3) * 9  : 0;

  // ── Shockwave ring at shatter
  const ringProg    = spring({ frame: Math.max(0, frame - SHATTER_FRAME), fps, config: SPRING_HEAVY });
  const ringScale   = interpolate(ringProg, [0, 1], [0.2, 3.5]);
  const ringOp      = interpolate(ringProg, [0, 0.2, 0.6, 1], [0, 0.8, 0.3, 0]);

  // ── "1,000,000" slam at frame 115
  const slamProg    = spring({ frame: Math.max(0, frame - 115), fps, config: SPRING_HEAVY });
  const slamScale   = interpolate(slamProg, [0, 1], [0.4, 1]);
  const slamOp      = interpolate(slamProg, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });
  const numGlow     = 22 + (Math.sin((frame / fps) * Math.PI * 2 * 0.55) * 0.5 + 0.5) * 42;

  // ── "TOKENS / SEC" fades in at frame 145
  const unitProg    = spring({ frame: Math.max(0, frame - 145), fps, config: SPRING_MEDIUM });
  const unitOp      = interpolate(unitProg, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
  const unitY       = interpolate(unitProg, [0, 1], [16, 0]);

  // ── "NEW BASELINE" at frame 160
  const baselineProg = spring({ frame: Math.max(0, frame - 160), fps, config: SPRING_MEDIUM });
  const baselineOp   = interpolate(baselineProg, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });

  // ── Hook text at frame 172
  const hookOp = interpolate(
    spring({ frame: Math.max(0, frame - 172), fps, config: SPRING_MEDIUM }),
    [0, 0.3], [0, 1], { extrapolateRight: "clamp" }
  );

  const showLogoPhase = frame < SHATTER_FRAME + 2;

  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at 50% 45%, #051005 0%, ${BG} 70%)`,
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", fontFamily: FONT, overflow: "hidden",
      padding: 60, boxSizing: "border-box",
      transform: `translate(${shakeX}px, ${shakeY}px)`,
    }}>
      <ParticleBackground frame={frame} />

      {/* Shockwave ring at shatter point */}
      <div style={{
        position: "absolute",
        width: 200, height: 200,
        borderRadius: "50%",
        border: `3px solid ${AMD_GREEN}`,
        boxShadow: `0 0 20px ${AMD_GREEN}60, 0 0 60px ${AMD_GREEN}20`,
        opacity: ringOp,
        transform: `scale(${ringScale})`,
        pointerEvents: "none",
      }} />

      {/* AMD logo — draw-in phase, then scales into barrier */}
      {showLogoPhase && (
        <div style={{
          opacity: logoOp * logoFinalOp,
          transform: `scale(${showLogoPhase ? logoScale * (frame >= 78 ? impactScale : 1) : 1})`,
          transformOrigin: "center center",
          position: "relative", zIndex: 2,
        }}>
          <AMDLogo size={140} frame={frame} drawProgress={drawProgress} />
        </div>
      )}

      {/* Red barrier — slides in, shatters on impact */}
      <div style={{
        position: "absolute",
        width: "110%", height: 6,
        background: `linear-gradient(90deg, transparent, ${RED}, ${RED}, transparent)`,
        boxShadow: `0 0 20px ${RED}90, 0 0 40px ${RED}30`,
        opacity: barrierOp * barrierHide,
        transform: `translateX(${barrierX}px)`,
        zIndex: 3,
      }}>
        <div style={{
          position: "absolute", right: 16, top: -22,
          fontSize: 17, fontWeight: 700, color: RED,
          letterSpacing: "0.08em", fontFamily: FONT,
          opacity: 0.85,
        }}>
          1M TOKENS/SEC CEILING
        </div>
      </div>

      {/* Shatter fragments */}
      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 4 }}>
        {FRAGMENT_SEEDS.map((seed, i) => (
          <BarrierFragment key={i} seed={seed} progress={shatterProg} i={i} />
        ))}
      </div>

      {/* Post-shatter content */}
      <div style={{
        position: "relative", zIndex: 5,
        display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
        opacity: frame < SHATTER_FRAME ? 0 : 1,
      }}>

        {/* 1,000,000 slam */}
        <div style={{
          opacity: slamOp,
          transform: `scale(${slamScale})`,
          transformOrigin: "center center",
          fontSize: 96, fontWeight: 900, color: YELLOW,
          fontFamily: FONT, letterSpacing: "-0.04em", lineHeight: 1,
          textShadow: `0 0 ${numGlow}px ${YELLOW}70, 0 0 ${numGlow * 2}px ${YELLOW}25`,
        }}>
          1,000,000
        </div>

        {/* TOKENS / SEC */}
        <div style={{
          opacity: unitOp,
          transform: `translateY(${unitY}px)`,
          fontSize: 36, fontWeight: 700, color: AMD_GREEN,
          fontFamily: FONT, letterSpacing: "0.15em",
          textShadow: `0 0 16px ${AMD_GREEN}70`,
        }}>
          TOKENS / SEC
        </div>

        {/* NEW BASELINE badge */}
        <div style={{
          opacity: baselineOp,
          marginTop: 8,
          background: `${AMD_GREEN}18`,
          border: `1px solid ${AMD_GREEN}50`,
          borderRadius: 40,
          padding: "6px 20px",
          fontSize: 20, fontWeight: 600, color: AMD_GREEN,
          letterSpacing: "0.1em", fontFamily: FONT,
        }}>
          NEW BASELINE
        </div>

        {/* Hook text — small, forces focus */}
        <div style={{
          opacity: hookOp,
          marginTop: 20,
          fontSize: 26, color: "rgba(255,255,255,0.30)",
          fontFamily: FONT, textAlign: "center", maxWidth: 680, lineHeight: 1.55,
        }}>
          AMD just made this the new floor.
        </div>

      </div>

      <TelemetryFrame frame={frame} />
    </AbsoluteFill>
  );
};

// ── Concept 1 — MI300X vs MI355X ComparisonSplit ──────────────────────────────

const LEFT_METRICS = [
  { label: "Architecture",   value: "MI300X",   color: RED               },
  { label: "Throughput",     value: "~333K t/s", color: RED               },
  { label: "Generation",     value: "Previous",  color: "rgba(255,80,80,0.7)" },
  { label: "Agentic loops",  value: "Slow",      color: RED               },
];

const RIGHT_METRICS = [
  { label: "Architecture",   value: "MI355X",   color: AMD_GREEN, glow: true  },
  { label: "Throughput",     value: "1M+ t/s",  color: YELLOW,    glow: true  },
  { label: "Generation",     value: "3× faster", color: AMD_GREEN             },
  { label: "Agentic loops",  value: "Real-time", color: CYAN                  },
];

const Concept1Beat: React.FC = () => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();

  const leftProg  = spring({ frame: Math.max(0, frame - 10), fps, config: SPRING_MEDIUM });
  const leftX     = interpolate(leftProg, [0, 1], [-90, 0]);
  const leftOp    = interpolate(leftProg, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });

  const rightProg = spring({ frame: Math.max(0, frame - 15), fps, config: SPRING_MEDIUM });
  const rightX    = interpolate(rightProg, [0, 1], [90, 0]);
  const rightOp   = interpolate(rightProg, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });

  const dividerProg = spring({ frame: Math.max(0, frame - 8), fps, config: SPRING_MEDIUM });
  const dividerOp   = interpolate(dividerProg, [0, 0.4], [0, 1], { extrapolateRight: "clamp" });
  const dividerH    = interpolate(dividerProg, [0, 1], [0, 100]);

  const labelOp = interpolate(
    spring({ frame: Math.max(0, frame - 4), fps, config: SPRING_MEDIUM }),
    [0, 0.3], [0, 1], { extrapolateRight: "clamp" }
  );

  const glowPulse = Math.sin((frame / 30) * Math.PI * 2 * 0.5) * 0.5 + 0.5;

  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at 50% 25%, #071207 0%, ${BG} 65%)`,
      display: "flex", flexDirection: "column",
      fontFamily: FONT, padding: "72px 44px", boxSizing: "border-box",
      gap: 28, overflow: "hidden",
    }}>
      <ParticleBackground frame={frame} />

      <div style={{
        fontSize: 21, fontWeight: 600, letterSpacing: "0.12em",
        textTransform: "uppercase", color: "rgba(255,255,255,0.32)",
        opacity: labelOp, textAlign: "center",
      }}>
        Generation Comparison
      </div>

      <div style={{ flex: 1, display: "flex", alignItems: "stretch", gap: 0, position: "relative" }}>

        {/* LEFT — MI300X (scanline = legacy) */}
        <div style={{
          flex: 1, opacity: leftOp, transform: `translateX(${leftX}px)`,
          display: "flex", flexDirection: "column", paddingRight: 22, position: "relative",
        }}>
          {/* Scanline overlay marks legacy side */}
          <div style={{
            position: "absolute", inset: 0,
            backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.2) 3px, rgba(0,0,0,0.2) 4px)",
            pointerEvents: "none", zIndex: 5, borderRadius: 8,
          }} />
          <div style={{ fontSize: 30, fontWeight: 800, color: RED, marginBottom: 24,
            textShadow: `0 0 14px ${RED}50` }}>
            Previous Gen
          </div>
          {LEFT_METRICS.map((m, i) => {
            const mp  = spring({ frame: Math.max(0, frame - (18 + i * 9)), fps, config: SPRING_MEDIUM });
            const mOp = interpolate(mp, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                opacity: mOp, display: "flex", flexDirection: "column",
                padding: "14px 0", borderBottom: "1px solid rgba(255,255,255,0.05)",
              }}>
                <div style={{ fontSize: 18, color: "rgba(255,255,255,0.38)" }}>{m.label}</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: m.color, marginTop: 4 }}>{m.value}</div>
              </div>
            );
          })}
        </div>

        {/* LASER DIVIDER — AMD green */}
        <div style={{
          width: 2, flexShrink: 0,
          background: `linear-gradient(to bottom, transparent, ${AMD_GREEN}, ${CYAN}, ${AMD_GREEN}, transparent)`,
          boxShadow: `0 0 10px ${AMD_GREEN}AA, 0 0 24px ${AMD_GREEN}40`,
          opacity: dividerOp,
          alignSelf: "stretch",
          clipPath: `inset(${100 - dividerH}% 0 0 0)`,
        }} />

        {/* RIGHT — MI355X (no scanline) */}
        <div style={{
          flex: 1, opacity: rightOp, transform: `translateX(${rightX}px)`,
          display: "flex", flexDirection: "column", paddingLeft: 22,
        }}>
          <div style={{ fontSize: 30, fontWeight: 800, color: AMD_GREEN, marginBottom: 24,
            textShadow: `0 0 16px ${AMD_GREEN}60` }}>
            MI355X
          </div>
          {RIGHT_METRICS.map((m, i) => {
            const mp   = spring({ frame: Math.max(0, frame - (23 + i * 9)), fps, config: SPRING_MEDIUM });
            const mOp  = interpolate(mp, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
            const gr   = m.glow ? 8 + glowPulse * 18 : 0;
            return (
              <div key={i} style={{
                opacity: mOp, display: "flex", flexDirection: "column",
                padding: "14px 0", borderBottom: "1px solid rgba(255,255,255,0.05)",
              }}>
                <div style={{ fontSize: 18, color: "rgba(255,255,255,0.38)" }}>{m.label}</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: m.color, marginTop: 4,
                  textShadow: m.glow ? `0 0 ${gr}px ${m.color}80` : "none" }}>
                  {m.value}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <TelemetryFrame frame={frame} />
    </AbsoluteFill>
  );
};

// ── Concept 2 — Before/After Latency Cards ────────────────────────────────────

const Concept2Beat: React.FC = () => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();

  const labelOp = interpolate(
    spring({ frame: Math.max(0, frame - 4), fps, config: SPRING_MEDIUM }),
    [0, 0.3], [0, 1], { extrapolateRight: "clamp" }
  );

  // Before card
  const beforeProg = spring({ frame: Math.max(0, frame - 12), fps, config: SPRING_MEDIUM });
  const beforeY    = interpolate(beforeProg, [0, 1], [60, 0]);
  const beforeOp   = interpolate(beforeProg, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });

  // After card — enters 12 frames later (pop-pop rhythm)
  const afterProg  = spring({ frame: Math.max(0, frame - 24), fps, config: SPRING_HEAVY });
  const afterY     = interpolate(afterProg, [0, 1], [80, 0]);
  const afterOp    = interpolate(afterProg, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
  const afterGlow  = 10 + (Math.sin((frame / 30) * Math.PI * 2 * 0.45) * 0.5 + 0.5) * 22;

  const BEFORE_ROWS = [
    { label: "Orchestration loop latency",  value: "8–12s per cycle",  color: RED    },
    { label: "Bottleneck",                  value: "Inference queue",   color: RED    },
    { label: "Viable parallel agents",      value: "4–8",               color: RED    },
    { label: "Real-time orchestration",     value: "Impossible",        color: RED    },
  ];

  const AFTER_ROWS = [
    { label: "Orchestration loop latency",  value: "~2s per cycle",     color: AMD_GREEN },
    { label: "Bottleneck",                  value: "Eliminated",         color: YELLOW    },
    { label: "Viable parallel agents",      value: "50+",                color: AMD_GREEN },
    { label: "Real-time orchestration",     value: "Now possible",       color: CYAN      },
  ];

  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at 50% 30%, #071207 0%, ${BG} 65%)`,
      display: "flex", flexDirection: "column",
      fontFamily: FONT, padding: "72px 48px", boxSizing: "border-box",
      gap: 32, overflow: "hidden",
    }}>
      <ParticleBackground frame={frame} />

      <div style={{
        fontSize: 21, fontWeight: 600, letterSpacing: "0.12em",
        textTransform: "uppercase", color: "rgba(255,255,255,0.32)",
        opacity: labelOp, textAlign: "center",
      }}>
        Multi-Agent Swarm Performance
      </div>

      {/* BEFORE card */}
      <div style={{
        opacity: beforeOp, transform: `translateY(${beforeY}px)`,
        background: `${RED}08`,
        border: `1px solid ${RED}30`,
        borderRadius: 16, padding: "24px 28px",
        position: "relative", overflow: "hidden",
      }}>
        {/* Scanline on BEFORE (legacy) */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.16) 3px, rgba(0,0,0,0.16) 4px)",
          pointerEvents: "none", borderRadius: 16,
        }} />
        <div style={{ fontSize: 24, fontWeight: 700, color: RED, marginBottom: 16,
          letterSpacing: "0.06em" }}>
          BEFORE MI355X
        </div>
        {BEFORE_ROWS.map((r, i) => {
          const rp  = spring({ frame: Math.max(0, frame - (16 + i * 6)), fps, config: SPRING_MEDIUM });
          const rOp = interpolate(rp, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              opacity: rOp, padding: "9px 0",
              borderBottom: i < BEFORE_ROWS.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none",
            }}>
              <div style={{ fontSize: 20, color: "rgba(255,255,255,0.42)" }}>{r.label}</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: r.color }}>{r.value}</div>
            </div>
          );
        })}
      </div>

      {/* AFTER card — AMD green glow, no scanline */}
      <div style={{
        opacity: afterOp, transform: `translateY(${afterY}px)`,
        background: `${AMD_GREEN}0A`,
        border: `1px solid ${AMD_GREEN}40`,
        borderRadius: 16, padding: "24px 28px",
        boxShadow: `0 0 ${afterGlow}px ${AMD_GREEN}30`,
      }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: AMD_GREEN, marginBottom: 16,
          letterSpacing: "0.06em",
          textShadow: `0 0 ${afterGlow}px ${AMD_GREEN}70` }}>
          WITH MI355X
        </div>
        {AFTER_ROWS.map((r, i) => {
          const rp  = spring({ frame: Math.max(0, frame - (28 + i * 6)), fps, config: SPRING_MEDIUM });
          const rOp = interpolate(rp, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
          return (
            <div key={i} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              opacity: rOp, padding: "9px 0",
              borderBottom: i < AFTER_ROWS.length - 1 ? "1px solid rgba(255,255,255,0.06)" : "none",
            }}>
              <div style={{ fontSize: 20, color: "rgba(255,255,255,0.42)" }}>{r.label}</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: r.color,
                textShadow: `0 0 10px ${r.color}50` }}>
                {r.value}
              </div>
            </div>
          );
        })}
      </div>

      <TelemetryFrame frame={frame} />
    </AbsoluteFill>
  );
};

// ── Takeaway Beat (blur word-reveal, AMD green radial, AdaMax CTA) ────────────

const HEADLINE = "The compute moat is shifting from capacity to throughput and speed is now the only moat that matters.".split(" ");
const CTA_LINE = "Test your knowledge on AdaMax.";

const TakeawayBeat: React.FC<{ durationFrames: number }> = ({ durationFrames }) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();

  const radialScale = interpolate(frame, [0, durationFrames], [0.4, 2.0], { extrapolateRight: "clamp" });

  const labelOp = interpolate(
    spring({ frame: Math.max(0, frame - 4), fps, config: SPRING_MEDIUM }),
    [0, 0.3], [0, 1], { extrapolateRight: "clamp" }
  );

  const ctaProg = spring({ frame: Math.max(0, frame - 145), fps, config: SPRING_MEDIUM });
  const ctaOp   = interpolate(ctaProg, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
  const ctaY    = interpolate(ctaProg, [0, 1], [18, 0]);

  // AMD logo reappears at frame 155 as identity bookend
  const logoReturnProg = spring({ frame: Math.max(0, frame - 155), fps, config: SPRING_MEDIUM });
  const logoReturnOp   = interpolate(logoReturnProg, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: BG,
      display: "flex", flexDirection: "column", fontFamily: FONT,
      padding: "72px 52px", boxSizing: "border-box",
      justifyContent: "center", gap: 36, overflow: "hidden",
    }}>
      {/* AMD green radial expansion */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: `radial-gradient(circle at 50% 50%, ${AMD_GREEN}18 ${radialScale * 28}%, transparent ${radialScale * 52}%)`,
      }} />

      <ParticleBackground frame={frame} />

      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 32 }}>

        <div style={{
          fontSize: 21, fontWeight: 600, letterSpacing: "0.12em",
          textTransform: "uppercase", color: "rgba(255,255,255,0.32)",
          opacity: labelOp,
        }}>
          Takeaway
        </div>

        {/* Blur word-reveal with letterSpacing tension */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0 10px", lineHeight: 1.5 }}>
          {HEADLINE.map((word, i) => {
            const wp   = spring({ frame: Math.max(0, frame - (8 + i * 4)), fps, config: SPRING_MEDIUM });
            const blur = interpolate(wp, [0, 1], [10, 0]);
            const op   = interpolate(wp, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
            const ls   = interpolate(wp, [0, 1], [5, -0.5]);
            return (
              <span key={i} style={{
                fontSize: 36, fontWeight: 700, color: "#FFFFFF",
                fontFamily: FONT,
                opacity: op,
                filter: `blur(${blur}px)`,
                letterSpacing: `${ls}px`,
                display: "inline-block",
              }}>
                {word}
              </span>
            );
          })}
        </div>

        {/* CTA */}
        <div style={{
          opacity: ctaOp, transform: `translateY(${ctaY}px)`,
          fontSize: 28, fontWeight: 600, color: AMD_GREEN,
          fontFamily: FONT, letterSpacing: "0.02em",
          textShadow: `0 0 18px ${AMD_GREEN}60`,
        }}>
          {CTA_LINE}
        </div>

        {/* AMD logo bookend — returns at end */}
        <div style={{ opacity: logoReturnOp, transform: "scale(0.75)", transformOrigin: "left center" }}>
          <AMDLogo size={80} frame={frame} drawProgress={1} />
        </div>

      </div>

      <TelemetryFrame frame={frame} />
    </AbsoluteFill>
  );
};

// ── Root composition ──────────────────────────────────────────────────────────

export const CustomVideo: React.FC = () => {
  const start2 = HOOK_F;
  const start3 = start2 + CONCEPT1_F;
  const start4 = start3 + CONCEPT2_F;

  return (
    <AbsoluteFill style={{ background: BG }}>

      <Audio src={staticFile("narration.wav")} />

      <Sequence from={0} durationInFrames={HOOK_F}>
        <Beat><HookBeat /></Beat>
      </Sequence>

      <Sequence from={start2} durationInFrames={CONCEPT1_F}>
        <Beat><AbsoluteFill><Concept1Beat /></AbsoluteFill></Beat>
      </Sequence>

      <Sequence from={start3} durationInFrames={CONCEPT2_F}>
        <Beat><AbsoluteFill><Concept2Beat /></AbsoluteFill></Beat>
      </Sequence>

      <Sequence from={start4} durationInFrames={TAKEAWAY_F}>
        <Beat><AbsoluteFill><TakeawayBeat durationFrames={TAKEAWAY_F} /></AbsoluteFill></Beat>
      </Sequence>

    </AbsoluteFill>
  );
};
