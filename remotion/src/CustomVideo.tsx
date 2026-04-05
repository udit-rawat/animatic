/**
 * CustomVideo.tsx — Unsloth Studio: "You No Longer Need to Pay for Cloud GPUs to Fine-Tune Models"
 * 1149 frames · 30fps · 38.3s
 *
 * [hook]      frames   0–214   7.1s  Cloud invoice knocked off by Unsloth + FREE slam
 * [concept_1] frames 214–562  11.6s  ComparisonSplit — Cloud vs Unsloth
 * [concept_2] frames 562–889  10.9s  TriStat — Your Data / Your Hardware / Your Speed
 * [takeaway]  frames 889–1149  8.7s  TakeawayScene — word reveal
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
import { ComparisonSplit } from "./layouts/ComparisonSplit";
import { TriStat } from "./layouts/TriStat";
import { TakeawayScene } from "./layouts/TakeawayScene";
import { COLOR, FONT, ParticleBackground, TelemetryFrame } from "./layouts/_shared";
import { SPRING_HEAVY, SPRING_MEDIUM } from "./utils/springIn";

// ── Frame budgets ─────────────────────────────────────────────────────────────

const HOOK_F     = 214;
const CONCEPT1_F = 348;  // 562 - 214
const CONCEPT2_F = 327;  // 889 - 562
const TAKEAWAY_F = 260;  // 1149 - 889

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

const TEAL   = "#1BC8A0";   // Unsloth brand teal
const RED    = "#FF3366";   // Radium Red — cloud cost pain
const YELLOW = COLOR.yellow;
const CYAN   = COLOR.cyan;

// ── Invoice line item ─────────────────────────────────────────────────────────

const InvoiceLine: React.FC<{
  label:   string;
  amount:  string;
  frame:   number;
  fps:     number;
  delay:   number;
}> = ({ label, amount, frame, fps, delay }) => {
  const prog = spring({ frame: Math.max(0, frame - delay), fps, config: SPRING_MEDIUM });
  const opacity  = interpolate(prog, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
  const translateX = interpolate(prog, [0, 1], [-40, 0], { extrapolateRight: "clamp" });

  return (
    <div style={{
      display:       "flex",
      justifyContent:"space-between",
      alignItems:    "center",
      opacity,
      transform:     `translateX(${translateX}px)`,
      padding:       "10px 0",
      borderBottom:  "1px solid rgba(255,100,100,0.15)",
    }}>
      <div style={{ fontSize: 26, color: "rgba(255,255,255,0.55)", fontFamily: FONT }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, color: RED, fontFamily: FONT }}>{amount}</div>
    </div>
  );
};

// ── Unsloth logo (TSX — no white background issue) ────────────────────────────

const UnslothLogo: React.FC<{ size: number; frame: number }> = ({ size, frame }) => {
  const glowPulse = Math.sin((frame / 30) * Math.PI * 2 * 0.4) * 0.5 + 0.5;
  const glow      = 16 + glowPulse * 20;

  return (
    <div style={{
      display:    "flex",
      alignItems: "center",
      gap:        16,
      filter:     `drop-shadow(0 0 ${glow}px ${TEAL}80)`,
    }}>
      {/* Teal circle with sloth face — simplified TSX */}
      <div style={{
        width:        size,
        height:       size,
        borderRadius: "50%",
        background:   `radial-gradient(circle at 40% 35%, ${TEAL}EE, #0D9A77)`,
        display:      "flex",
        alignItems:   "center",
        justifyContent:"center",
        border:       `2px solid ${TEAL}`,
        boxShadow:    `0 0 ${glow}px ${TEAL}60`,
        flexShrink:   0,
        position:     "relative",
        overflow:     "hidden",
      }}>
        {/* Sloth face simplified */}
        <svg width={size * 0.7} height={size * 0.7} viewBox="0 0 60 60">
          {/* Face */}
          <ellipse cx="30" cy="32" rx="22" ry="20" fill="#F5DEB3" />
          {/* Eye patches */}
          <ellipse cx="20" cy="28" rx="8" ry="8" fill="#5C3A1E" opacity="0.85" />
          <ellipse cx="40" cy="28" rx="8" ry="8" fill="#5C3A1E" opacity="0.85" />
          {/* Eyes */}
          <circle cx="20" cy="28" r="4.5" fill="white" />
          <circle cx="40" cy="28" r="4.5" fill="white" />
          <circle cx="21" cy="27" r="2.5" fill="#1a5c3a" />
          <circle cx="41" cy="27" r="2.5" fill="#1a5c3a" />
          <circle cx="22" cy="26" r="1" fill="white" />
          <circle cx="42" cy="26" r="1" fill="white" />
          {/* Nose */}
          <ellipse cx="30" cy="36" rx="4" ry="3" fill="#C68642" opacity="0.7" />
          {/* Smile */}
          <path d="M 22 42 Q 30 48 38 42" stroke="#8B5E3C" strokeWidth="2" fill="none" strokeLinecap="round" />
        </svg>
      </div>
      {/* Wordmark */}
      <div style={{
        fontSize:      size * 0.75,
        fontWeight:    800,
        color:         "#FFFFFF",
        fontFamily:    FONT,
        letterSpacing: "-0.03em",
        lineHeight:    1,
      }}>
        unsloth
      </div>
    </div>
  );
};

// ── Hook Beat ─────────────────────────────────────────────────────────────────

const HookBeat: React.FC = () => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Invoice slides in from top
  const invoiceProgress = spring({ frame: Math.max(0, frame), fps, config: SPRING_HEAVY });
  const invoiceY  = interpolate(invoiceProgress, [0, 1], [-120, 0]);
  const invoiceOp = interpolate(invoiceProgress, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });

  // Invoice exits — slides left and fades at frame 90
  const exitProgress = spring({ frame: Math.max(0, frame - 90), fps, config: SPRING_HEAVY });
  const invoiceExitX = interpolate(exitProgress, [0, 1], [0, -800]);
  const invoiceExitOp = interpolate(exitProgress, [0, 0.4], [1, 0], { extrapolateRight: "clamp" });

  // Unsloth logo crashes in from below at frame 80
  const logoProgress = spring({ frame: Math.max(0, frame - 80), fps, config: SPRING_HEAVY });
  const logoY  = interpolate(logoProgress, [0, 1], [200, 0]);
  const logoOp = interpolate(logoProgress, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });

  // FREE slams in at frame 110
  const freeProgress = spring({ frame: Math.max(0, frame - 110), fps, config: SPRING_HEAVY });
  const freeScale = interpolate(freeProgress, [0, 1], [0.4, 1]);
  const freeOp    = interpolate(freeProgress, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });
  const freeGlow  = 30 + (Math.sin((frame / fps) * Math.PI * 2 * 0.4) * 0.5 + 0.5) * 50;

  // Hook text fades in at frame 130
  const textProgress = spring({ frame: Math.max(0, frame - 130), fps, config: SPRING_MEDIUM });
  const textOp = interpolate(textProgress, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
  const textY  = interpolate(textProgress, [0, 1], [20, 0]);

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
      gap:            40,
    }}>
      <ParticleBackground frame={frame} />

      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 40, width: "100%" }}>

        {/* Cloud invoice card */}
        <div style={{
          opacity:   invoiceOp * invoiceExitOp,
          transform: `translateY(${invoiceY}px) translateX(${invoiceExitX}px)`,
          width:     "100%",
          background:"rgba(255,50,80,0.06)",
          border:    `1px solid ${RED}30`,
          borderRadius: 16,
          padding:   "28px 32px",
        }}>
          <div style={{
            fontSize: 22, fontWeight: 600, color: "rgba(255,255,255,0.4)",
            letterSpacing: "0.1em", textTransform: "uppercase",
            fontFamily: FONT, marginBottom: 16,
          }}>
            Cloud GPU Invoice — April 2026
          </div>
          <InvoiceLine label="GPU compute (A100 · 40h)" amount="$47.20" frame={frame} fps={fps} delay={4} />
          <InvoiceLine label="Training runs"            amount="$23.80" frame={frame} fps={fps} delay={10} />
          <InvoiceLine label="Storage + egress"         amount="$8.40"  frame={frame} fps={fps} delay={16} />
          <div style={{
            display: "flex", justifyContent: "space-between",
            marginTop: 16, paddingTop: 16,
            borderTop: `1px solid ${RED}40`,
          }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: "rgba(255,255,255,0.7)", fontFamily: FONT }}>Total this month</div>
            <div style={{ fontSize: 36, fontWeight: 900, color: RED, fontFamily: FONT, letterSpacing: "-0.02em",
              textShadow: `0 0 20px ${RED}50` }}>$79.40</div>
          </div>
        </div>

        {/* Unsloth logo crashes in */}
        <div style={{
          opacity:   logoOp,
          transform: `translateY(${logoY}px)`,
        }}>
          <UnslothLogo size={72} frame={frame} />
        </div>

        {/* FREE */}
        <div style={{
          opacity:         freeOp,
          transform:       `scale(${freeScale})`,
          transformOrigin: "center center",
          fontSize:        140,
          fontWeight:      900,
          color:           YELLOW,
          fontFamily:      FONT,
          letterSpacing:   "-0.05em",
          lineHeight:      1,
          textShadow:      `0 0 ${freeGlow}px ${YELLOW}60, 0 0 ${freeGlow * 2}px ${YELLOW}20`,
        }}>
          FREE.
        </div>

        {/* Hook line */}
        <div style={{
          opacity:   textOp,
          transform: `translateY(${textY}px)`,
          fontSize:  28,
          color:     "rgba(255,255,255,0.35)",
          fontFamily: FONT,
          textAlign: "center",
          maxWidth:  700,
          lineHeight: 1.5,
        }}>
          You are still paying for cloud GPUs every month to fine-tune your own models.
        </div>
      </div>

      <TelemetryFrame frame={frame} />
    </AbsoluteFill>
  );
};

// ── Beat data ─────────────────────────────────────────────────────────────────

const comparisonData = {
  section_label: "Cloud vs Local",
  left: {
    heading: "Cloud GPU",
    color:   "red" as const,
    metrics: [
      { label: "Monthly cost",  value: "$47–80",  color: "red"  as const },
      { label: "Memory needed", value: "Full",    color: "red"  as const },
      { label: "Data control",  value: "None",    color: "red"  as const },
    ],
  },
  right: {
    heading: "Unsloth",
    color:   "green" as const,
    metrics: [
      { label: "Monthly cost",  value: "$0",   color: "green" as const, glow: true },
      { label: "Memory saved",  value: "70%",  color: "green" as const, glow: true },
      { label: "Data control",  value: "Full", color: "green" as const },
    ],
  },
};

const triStatData = {
  section_label: "What you keep",
  accent_color:  "cyan" as const,
  stats: [
    { value: "100%",  label: "Data Privacy",   sublabel: "Nothing leaves your machine", color: "cyan",  glow: true },
    { value: "$0",    label: "Monthly Bill",    sublabel: "Fine-tune on your own GPU",   color: "green", glow: false },
    { value: "500+",  label: "Models",          sublabel: "All open source, no waitlist",color: "cyan",  glow: false },
  ],
};

const takeawayData = {
  section_label: "Takeaway",
  accent_color:  "cyan" as const,
  headline:      "Free local fine-tuning at seventy percent less memory means the cloud GPU bill is now optional.",
  cta:           "Unsloth Studio. Download and run locally.",
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
          <AbsoluteFill><ComparisonSplit data={comparisonData} /></AbsoluteFill>
        </Beat>
      </Sequence>

      <Sequence from={start3} durationInFrames={CONCEPT2_F}>
        <Beat>
          <AbsoluteFill><TriStat data={triStatData} /></AbsoluteFill>
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
