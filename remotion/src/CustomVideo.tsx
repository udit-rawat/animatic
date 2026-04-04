/**
 * CustomVideo.tsx — MolmoWeb: "You Pay for Web Agents. This Open Source One Beats Them Locally"
 * 937 frames · 30fps · 31.2s
 *
 * [hook]      frames   0–216   7.2s  Custom browser + MolmoWeb logo entrance + FREE slam
 * [concept_1] frames 216–512   9.9s  BarComparison — 4 web agent benchmark scores
 * [concept_2] frames 512–731   7.3s  MetricFocus   — $0 hero metric
 * [takeaway]  frames 731–937   6.8s  TakeawayScene — word reveal + CTA
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
import { BarComparison } from "./layouts/BarComparison";
import { MetricFocus } from "./layouts/MetricFocus";
import { TakeawayScene } from "./layouts/TakeawayScene";
import {
  COLOR,
  FONT,
  ParticleBackground,
  TelemetryFrame,
} from "./layouts/_shared";
import { SPRING_HEAVY, SPRING_MEDIUM } from "./utils/springIn";

// ── Frame budgets ─────────────────────────────────────────────────────────────

const HOOK_F     = 216;
const CONCEPT1_F = 296;   // 512 - 216
const CONCEPT2_F = 219;   // 731 - 512
const TAKEAWAY_F = 206;   // 937 - 731

// ── Beat context wrapper ──────────────────────────────────────────────────────

const Beat: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <BeatFrameContext.Provider value={{ beatStartFrame: 0 }}>
    {children}
  </BeatFrameContext.Provider>
);

// ── Design tokens ─────────────────────────────────────────────────────────────

const PINK   = "#F472B6";
const CYAN   = COLOR.cyan;
const YELLOW = COLOR.yellow;

// ── Loading spinner ───────────────────────────────────────────────────────────

const Spinner: React.FC<{ frame: number; size: number; color: string }> = ({ frame, size, color }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" style={{ overflow: "visible" }}>
    {Array.from({ length: 8 }, (_, i) => {
      const angle   = (i / 8) * Math.PI * 2;
      const phase   = ((frame * 0.12) + i / 8) % 1;
      const x1 = 20 + Math.cos(angle) * 11;
      const y1 = 20 + Math.sin(angle) * 11;
      const x2 = 20 + Math.cos(angle) * 17;
      const y2 = 20 + Math.sin(angle) * 17;
      return (
        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={color} strokeWidth={2.5} strokeLinecap="round" opacity={0.15 + phase * 0.85} />
      );
    })}
  </svg>
);

// ── Geometric network node ────────────────────────────────────────────────────

const NetworkNode: React.FC<{ frame: number; size: number }> = ({ frame, size }) => {
  const rot      = frame * 0.6;
  const glowPulse = Math.sin((frame / 30) * Math.PI * 2 * 0.4) * 0.5 + 0.5;
  const glow      = 12 + glowPulse * 16;

  const pts = Array.from({ length: 6 }, (_, i) => {
    const a = (i / 6) * Math.PI * 2 + (rot * Math.PI) / 180;
    return { x: Math.cos(a) * 0.65, y: Math.sin(a) * 0.65 };
  });

  const edges: [number, number][] = [[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[0,3],[1,4],[2,5]];

  return (
    <div style={{ width: size, height: size, filter: `drop-shadow(0 0 ${glow}px ${PINK}80)` }}>
      <svg width={size} height={size} viewBox="-1 -1 2 2">
        <circle cx={0} cy={0} r={0.92} fill={`${PINK}22`} stroke={PINK} strokeWidth={0.04} />
        {edges.map(([a, b], i) => (
          <line key={i} x1={pts[a].x} y1={pts[a].y} x2={pts[b].x} y2={pts[b].y}
            stroke={PINK} strokeWidth={0.03} opacity={0.5} />
        ))}
        {pts.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={0.055} fill={PINK} opacity={0.85} />
        ))}
        <circle cx={0} cy={0} r={0.08} fill={PINK} opacity={0.9} />
      </svg>
    </div>
  );
};

// ── Bidirectional pulse arrow ─────────────────────────────────────────────────

const PulseArrow: React.FC<{ frame: number; width: number }> = ({ frame, width }) => {
  const cycle   = 60;
  const t       = (frame % cycle) / cycle;
  const goRight = Math.floor(frame / cycle) % 2 === 0;
  const pos     = (goRight ? t : 1 - t) * width;

  return (
    <div style={{ position: "relative", width, height: 20, display: "flex", alignItems: "center" }}>
      <div style={{
        position: "absolute", left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, ${PINK}30, ${PINK}70, ${PINK}30)`,
      }} />
      <div style={{
        position: "absolute", left: -4,
        width: 0, height: 0,
        borderTop: "5px solid transparent", borderBottom: "5px solid transparent",
        borderRight: `7px solid ${PINK}70`,
      }} />
      <div style={{
        position: "absolute", right: -4,
        width: 0, height: 0,
        borderTop: "5px solid transparent", borderBottom: "5px solid transparent",
        borderLeft: `7px solid ${PINK}70`,
      }} />
      <div style={{
        position:     "absolute",
        left:         pos - 4,
        width:        8, height: 8,
        borderRadius: "50%",
        background:   PINK,
        boxShadow:    `0 0 10px ${PINK}`,
      }} />
    </div>
  );
};

// ── Browser window ────────────────────────────────────────────────────────────

const BrowserWindow: React.FC<{ frame: number; fps: number; progress: number }> = ({ frame, fps, progress }) => {
  const fullText   = "✦ MolmoWeb";
  const charCount  = Math.floor(
    interpolate(progress, [0.15, 0.65], [0, fullText.length], { extrapolateRight: "clamp" })
  );
  const displayText = fullText.slice(0, charCount);

  const elemProgress = spring({ frame: Math.max(0, frame - 14), fps, config: SPRING_MEDIUM });
  const elemOpacity  = interpolate(elemProgress, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
  const elemScale    = interpolate(elemProgress, [0, 1], [0.7, 1]);

  const urlGlow     = Math.sin((frame / fps) * Math.PI * 2 * 0.4) * 0.3 + 0.5;
  const browserOpacity = interpolate(progress, [0, 0.12], [0, 1], { extrapolateRight: "clamp" });
  const browserY       = interpolate(progress, [0, 1], [-60, 0]);

  return (
    <div style={{ opacity: browserOpacity, transform: `translateY(${browserY}px)`, width: 640 }}>
      {/* Chrome bar */}
      <div style={{
        background:   "rgba(255,255,255,0.04)",
        border:       `1px solid ${CYAN}40`,
        borderBottom: "none",
        borderRadius: "16px 16px 0 0",
        padding:      "14px 18px",
        display:      "flex",
        alignItems:   "center",
        gap:          10,
      }}>
        {["#FF5F57", "#FFBD2E", "#28C840"].map((c, i) => (
          <div key={i} style={{ width: 12, height: 12, borderRadius: "50%", background: c, opacity: 0.7 }} />
        ))}
        <div style={{
          flex:         1,
          marginLeft:   8,
          background:   `rgba(0,229,255,${urlGlow * 0.06})`,
          border:       `1px solid ${CYAN}30`,
          borderRadius: 6,
          padding:      "4px 12px",
          fontSize:     17,
          color:        "rgba(255,255,255,0.35)",
          fontFamily:   FONT,
        }}>
          localhost:7860/molmoweb
        </div>
      </div>

      {/* Body */}
      <div style={{
        background:   "rgba(10,10,10,0.92)",
        border:       `1px solid ${CYAN}35`,
        borderTop:    `1px solid ${CYAN}18`,
        borderRadius: "0 0 16px 16px",
        padding:      "36px 40px 44px",
        position:     "relative",
        overflow:     "hidden",
        boxShadow:    `0 0 60px ${CYAN}08`,
      }}>
        {/* MolmoWeb logo type-in */}
        <div style={{
          fontSize:      52,
          fontWeight:    700,
          color:         PINK,
          fontFamily:    FONT,
          letterSpacing: "-0.02em",
          marginBottom:  36,
          minHeight:     64,
          display:       "flex",
          alignItems:    "center",
        }}>
          {displayText}
          {charCount < fullText.length && (
            <span style={{
              display:      "inline-block",
              width:        3, height: "0.85em",
              background:   PINK,
              marginLeft:   2,
              opacity:      Math.floor(frame / 8) % 2 === 0 ? 1 : 0,
              verticalAlign:"middle",
            }} />
          )}
        </div>

        {/* Cursor + arrow + node */}
        <div style={{
          display:         "flex",
          alignItems:      "center",
          opacity:         elemOpacity,
          transform:       `scale(${elemScale})`,
          transformOrigin: "left center",
        }}>
          <div style={{ position: "relative", width: 80, height: 80, flexShrink: 0 }}>
            <div style={{ position: "absolute", top: 0, left: 0 }}>
              <Spinner frame={frame} size={60} color={CYAN} />
            </div>
            <svg width={38} height={38} viewBox="0 0 24 24"
              style={{ position: "absolute", bottom: 0, right: 0 }}>
              <path d="M4 4 L4 20 L8 16 L11 22 L13 21 L10 15 L16 15 Z"
                fill="none" stroke={CYAN} strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
          </div>

          <PulseArrow frame={frame} width={120} />
          <NetworkNode frame={frame} size={80} />
        </div>
      </div>
    </div>
  );
};

// ── Hook Beat ─────────────────────────────────────────────────────────────────

const HookBeat: React.FC = () => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress     = spring({ frame: Math.max(0, frame), fps, config: SPRING_HEAVY });
  const freeProgress = spring({ frame: Math.max(0, frame - 28), fps, config: SPRING_HEAVY });
  const line1Progress = spring({ frame: Math.max(0, frame - 6), fps, config: SPRING_MEDIUM });
  const line2Progress = spring({ frame: Math.max(0, frame - 36), fps, config: SPRING_MEDIUM });

  const freeScale   = interpolate(freeProgress, [0, 1], [0.5, 1]);
  const freeOpacity = interpolate(freeProgress, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });
  const freeGlow    = 30 + (Math.sin((frame / fps) * Math.PI * 2 * 0.4) * 0.5 + 0.5) * 40;

  return (
    <AbsoluteFill style={{
      background:     "radial-gradient(ellipse at 50% 40%, #111 0%, #0A0A0A 70%)",
      display:        "flex",
      flexDirection:  "column",
      alignItems:     "center",
      justifyContent: "center",
      fontFamily:     FONT,
      position:       "relative",
      overflow:       "hidden",
      padding:        60,
      boxSizing:      "border-box",
    }}>
      <ParticleBackground frame={frame} />

      <div style={{
        position:       "relative",
        zIndex:         1,
        display:        "flex",
        flexDirection:  "column",
        alignItems:     "center",
        gap:            36,
        width:          "100%",
      }}>
        {/* Top eyebrow */}
        <div style={{
          fontSize:      28,
          fontWeight:    500,
          color:         "rgba(255,255,255,0.4)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          opacity:       interpolate(line1Progress, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }),
          transform:     `translateY(${interpolate(line1Progress, [0, 1], [20, 0])}px)`,
        }}>
          AllenAI · Open Source
        </div>

        <BrowserWindow frame={frame} fps={fps} progress={progress} />

        {/* FREE slam */}
        <div style={{
          display:         "flex",
          alignItems:      "baseline",
          gap:             20,
          opacity:         freeOpacity,
          transform:       `scale(${freeScale})`,
          transformOrigin: "center bottom",
        }}>
          <div style={{
            fontSize:      44,
            fontWeight:    400,
            color:         "rgba(255,255,255,0.4)",
            fontFamily:    FONT,
            letterSpacing: "0.02em",
          }}>
            Runs locally.
          </div>
          <div style={{
            fontSize:      100,
            fontWeight:    900,
            color:         YELLOW,
            fontFamily:    FONT,
            letterSpacing: "-0.04em",
            lineHeight:    1,
            textShadow:    `0 0 ${freeGlow}px ${YELLOW}60, 0 0 ${freeGlow * 2}px ${YELLOW}20`,
          }}>
            FREE.
          </div>
        </div>

        {/* Hook line */}
        <div style={{
          fontSize:      26,
          fontWeight:    400,
          color:         "rgba(255,255,255,0.28)",
          letterSpacing: "0.02em",
          opacity:       interpolate(line2Progress, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }),
          transform:     `translateY(${interpolate(line2Progress, [0, 1], [16, 0])}px)`,
          textAlign:     "center",
          maxWidth:      680,
        }}>
          You pay monthly for web agents that break.
        </div>
      </div>

      <TelemetryFrame frame={frame} />
    </AbsoluteFill>
  );
};

// ── Beat data ─────────────────────────────────────────────────────────────────

const barData = {
  section_label: "Web Agent Benchmarks",
  accent_color:  "cyan" as const,
  items: [
    { label: "MolmoWeb 8B",    value: "67.8", highlight: true  },
    { label: "GPT-4V",         value: "59.1", highlight: false },
    { label: "Claude 3.5",     value: "57.3", highlight: false },
    { label: "Gemini 1.5 Pro", value: "52.4", highlight: false },
  ],
};

const metricData = {
  section_label: "Monthly API Cost",
  hero: {
    value: "$0",
    label: "After switching to MolmoWeb",
    color: "cyan" as const,
  },
  context: "No API costs. No data leaving your machine. Your automation runs fully local.",
  chips: ["Open Source", "Private", "Zero Cost"],
};

const takeawayData = {
  section_label: "Takeaway",
  accent_color:  "cyan" as const,
  headline:      "When a top lab open sources an agent this capable — ship with it the same day.",
  cta:           "MolmoWeb is live. Go build.",
};

// ── Composition config (consumed by Root.tsx) ─────────────────────────────────

export const CustomVideoConfig = {
  durationInFrames: HOOK_F + CONCEPT1_F + CONCEPT2_F + TAKEAWAY_F,
  fps:    30,
  width:  1080,
  height: 1920,
};

// ── Root composition ──────────────────────────────────────────────────────────

export const CustomVideo: React.FC = () => {
  const start2 = HOOK_F;
  const start3 = start2 + CONCEPT1_F;
  const start4 = start3 + CONCEPT2_F;

  return (
    <AbsoluteFill style={{ background: "#0A0A0A" }}>

      <Audio src={staticFile("narration.wav")} />

      <Sequence from={0} durationInFrames={HOOK_F}>
        <Beat><HookBeat /></Beat>
      </Sequence>

      <Sequence from={start2} durationInFrames={CONCEPT1_F}>
        <Beat>
          <AbsoluteFill><BarComparison data={barData} /></AbsoluteFill>
        </Beat>
      </Sequence>

      <Sequence from={start3} durationInFrames={CONCEPT2_F}>
        <Beat>
          <AbsoluteFill><MetricFocus data={metricData} /></AbsoluteFill>
        </Beat>
      </Sequence>

      <Sequence from={start4} durationInFrames={TAKEAWAY_F}>
        <Beat>
          <AbsoluteFill>
            <TakeawayScene data={takeawayData} durationFrames={TAKEAWAY_F} />
          </AbsoluteFill>
        </Beat>
      </Sequence>

    </AbsoluteFill>
  );
};
