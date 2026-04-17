/**
 * CustomVideo.tsx — QwenPaw. Local AI assistant. No API key.
 * 545f / 18.2s / 30fps
 *
 * ── EDIT THESE PROPS ─────────────────────────────────────────────────────────
 */
const PROPS = {
  beat1: {
    section_label: "qwenpaw",
    hero_value:    "Zero API",
    hero_label:    "100% local inference",
    hero_color:    "cyan" as const,
    context:       "Runs Qwen models entirely on CPU. No cloud. No key.",
    chips:         ["CPU-only", "llama.cpp", "free forever"],
  },
  beat2: {
    section_label: "under the hood",
    accent_color:  "green" as const,
    stats: [
      { value: "100%", label: "CPU inference via llama.cpp",   color: "cyan"  as const, glow: true },
      { value: "LOCAL", label: "All memory stored on device",  color: "green" as const },
      { value: "$0",    label: "Zero API cost, zero key",       color: "yellow" as const },
    ],
  },
  beat3: {
    section_label: "install",
    accent_color:  "cyan" as const,
    lines: [
      "git clone + build.",
      "Multi chat. Tool plugins.",
      "Ships tonight.",
    ],
  },
  beat4: {
    section_label: "takeaway",
    headline:      "Local AI that costs nothing and leaks nothing.",
    cta:           "Pull it. Run it.",
    accent_color:  "cyan" as const,
  },
};
// ─────────────────────────────────────────────────────────────────────────────

import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, spring, interpolate, useVideoConfig } from "remotion";
import { MetricFocus }    from "./layouts/MetricFocus";
import { StatementSlam }  from "./layouts/StatementSlam";
import { TakeawayScene }  from "./layouts/TakeawayScene";
import { BeatFrameContext } from "./hooks/useBeatFrame";

// Beat boundaries from pipeline brief
const BEAT1_START = 0;
const BEAT2_START = 98;
const BEAT3_START = 296;
const BEAT4_START = 493;
const TOTAL_FRAMES = 545;

const BEAT1_DUR = BEAT2_START - BEAT1_START;   // 98
const BEAT2_DUR = BEAT3_START - BEAT2_START;   // 198
const BEAT3_DUR = BEAT4_START - BEAT3_START;   // 197
const BEAT4_DUR = TOTAL_FRAMES - BEAT4_START;  // 52

export const CustomVideoConfig = {
  durationInFrames: TOTAL_FRAMES,
  fps:   30,
  width:  1080,
  height: 1920,
};

const STAT_COLORS: Record<string, string> = { cyan: "#00E5FF", green: "#10B981", yellow: "#CCFF00" };

const Beat2Stats: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{
      position: "absolute", top: 1480, left: 72, right: 72, zIndex: 20,
      display: "flex", flexDirection: "column", gap: 18,
      fontFamily: "'Space Grotesk', 'Inter', sans-serif",
    }}>
      {PROPS.beat2.stats.map((stat, i) => {
        const delay = 8 + i * 14;
        const prog  = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 16, mass: 0.7, stiffness: 220 } });
        const op    = interpolate(prog, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
        const ty    = interpolate(prog, [0, 1], [28, 0], { extrapolateRight: "clamp" });
        const c     = STAT_COLORS[stat.color] ?? "#00E5FF";
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 16, opacity: op, transform: `translateY(${ty}px)` }}>
            <div style={{ width: 4, height: 36, background: c, borderRadius: 2, flexShrink: 0 }} />
            <span style={{ fontSize: 52, fontWeight: 800, color: c, lineHeight: 1 }}>{stat.value}</span>
            <span style={{ fontSize: 28, fontWeight: 400, color: "rgba(249,250,251,0.7)", lineHeight: 1.2 }}>{stat.label}</span>
          </div>
        );
      })}
    </div>
  );
};

export const CustomVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: "#0A0A0A" }}>

      {/* Narration audio */}
      <Audio src={staticFile("narration.wav")} />

      {/* ── beat_1 — MetricFocus ── */}
      <Sequence from={BEAT1_START} durationInFrames={BEAT1_DUR}>
        <BeatFrameContext.Provider value={{ beatStartFrame: 0 }}>
          <AbsoluteFill>
            <MetricFocus data={{
              layout:        "MetricFocus",
              section_label: PROPS.beat1.section_label,
              hero:          { value: PROPS.beat1.hero_value, label: PROPS.beat1.hero_label, color: PROPS.beat1.hero_color },
              context:       PROPS.beat1.context,
              chips:         PROPS.beat1.chips,
            }} />
          </AbsoluteFill>
        </BeatFrameContext.Provider>
      </Sequence>

      {/* ── beat_2 — TriStat (caption zone — composite QwenPawCPU.mp4 over center in iMovie) ── */}
      <Sequence from={BEAT2_START} durationInFrames={BEAT2_DUR}>
        <BeatFrameContext.Provider value={{ beatStartFrame: 0 }}>
          <AbsoluteFill style={{ background: "#000000" }}>
            {/* Center region y:400–1400 intentionally empty — bg_loop composited here */}
            <div style={{
              position: "absolute", top: 400, left: 80, right: 80, height: 900,
              display: "flex", alignItems: "center", justifyContent: "center",
              border: "1px dashed rgba(0,229,255,0.06)", borderRadius: 12,
              pointerEvents: "none", zIndex: 0,
            }} />

            {/* Scrim above caption zone */}
            <div style={{
              position: "absolute", top: 1200, left: 0, right: 0, height: 280,
              background: "linear-gradient(to bottom, transparent, rgba(0,0,0,0.92))",
              zIndex: 5, pointerEvents: "none",
            }} />
            <div style={{
              position: "absolute", top: 1480, left: 0, right: 0, bottom: 0,
              background: "#000000", zIndex: 6, pointerEvents: "none",
            }} />

            {/* Caption zone — y:1480, stat lines with staggered spring entrance */}
            <Beat2Stats />
          </AbsoluteFill>
        </BeatFrameContext.Provider>
      </Sequence>

      {/* ── beat_3 — StatementSlam ── */}
      <Sequence from={BEAT3_START} durationInFrames={BEAT3_DUR}>
        <BeatFrameContext.Provider value={{ beatStartFrame: 0 }}>
          <AbsoluteFill>
            <StatementSlam data={{
              layout:        "StatementSlam",
              section_label: PROPS.beat3.section_label,
              lines:         PROPS.beat3.lines,
              accent_color:  PROPS.beat3.accent_color,
            }} />
          </AbsoluteFill>
        </BeatFrameContext.Provider>
      </Sequence>

      {/* ── beat_4 — TakeawayScene ── */}
      <Sequence from={BEAT4_START} durationInFrames={BEAT4_DUR}>
        <BeatFrameContext.Provider value={{ beatStartFrame: 0 }}>
          <AbsoluteFill>
            <TakeawayScene
              data={{
                layout:        "TakeawayScene",
                section_label: PROPS.beat4.section_label,
                headline:      PROPS.beat4.headline,
                cta:           PROPS.beat4.cta,
                accent_color:  PROPS.beat4.accent_color,
              }}
              durationFrames={BEAT4_DUR}
            />
          </AbsoluteFill>
        </BeatFrameContext.Provider>
      </Sequence>

    </AbsoluteFill>
  );
};
