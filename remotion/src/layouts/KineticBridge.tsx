/**
 * KineticBridge — conversational gap filler. Kills the "black hole" problem.
 *
 * Use when the voiceover is a bridge/narrative section with no structured data
 * (e.g. "Imagine running massive models on consumer GPUs…"). The layout pulses
 * 2–5 short keywords sequentially — never a dead black frame.
 *
 * Motion model:
 *   Each keyword owns a fixed HOLD_FRAMES window.
 *   Entry: scale 0.7 → 1.0 + opacity 0 → 1 (spring, crisp).
 *   Hold:  resting scale with gentle ambient breath.
 *   Exit:  opacity 1 → 0 over last 10 frames of window.
 *   Next keyword fires immediately after exit.
 *
 * After all keywords cycle, loops back to the first — perpetual motion for the full beat duration.
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { KineticBridgeData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow } from "./_shared";

const HOLD_FRAMES = 44; // 1.47s per keyword @30fps — tweak if needed
const EXIT_START  = HOLD_FRAMES - 10;

export const KineticBridge: React.FC<{ data: KineticBridgeData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[data.accent_color ?? "cyan"];
  const kws     = data.keywords;

  // Loop keywords for the full beat duration — no dead-air hold after last keyword.
  const totalCycleFrames = kws.length * HOLD_FRAMES;
  const effectiveFrame   = frame % totalCycleFrames;

  // Ambient drift on the active keyword (0.25 Hz breath, ±1.5% scale)
  const breathScale = 1 + Math.sin((frame / fps) * Math.PI * 2 * 0.25) * 0.015;

  return (
    <div style={{
      width:     "100%",
      height:    "100%",
      background:"#0A0A0A",
      position:  "relative",
      overflow:  "hidden",
      display:   "flex",
      flexDirection: "column",
      padding:   60,
      boxSizing: "border-box",
      fontFamily: FONT,
    }}>
      {/* Section micro-label — fades in with first keyword */}
      <SectionLabelRow text={data.section_label} color={data.accent_color ?? "cyan"} />

      {/* Keyword slots — all in absolute centre, only active one is visible */}
      <div style={{
        flex:           1,
        position:       "relative",
        display:        "flex",
        alignItems:     "center",
      }}>
        {kws.map((kw, i) => {
          const windowStart = i * HOLD_FRAMES;
          const kwFrame     = effectiveFrame - windowStart;
          const inWindow    = kwFrame >= 0 && kwFrame < HOLD_FRAMES;

          if (!inWindow) return null;

          const entryProgress = spring({
            frame: Math.max(0, kwFrame),
            fps,
            config: { damping: 28, stiffness: 220, overshootClamping: false },
          });

          const entryOpacity = interpolate(
            entryProgress, [0, 0.2], [0, 1], { extrapolateRight: "clamp" },
          );
          const exitOpacity = interpolate(kwFrame, [EXIT_START, HOLD_FRAMES - 2], [1, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });

          const scale = interpolate(entryProgress, [0, 1], [0.72, 1.0]) * breathScale;

          const opacity = entryOpacity * exitOpacity;

          // Colour cycles per-keyword, loops naturally with frame looping
          const kwColor = i === 0 ? accent
            : i % 3 === 1 ? COLOR.white
            : i % 3 === 2 ? COLOR[data.accent_color === "green" ? "cyan" : "green"]
            : accent;

          return (
            <div
              key={i}
              style={{
                position:        "absolute",
                left:            0,
                right:           0,
                opacity,
                transform:       `scale(${scale})`,
                transformOrigin: "left center",
                willChange:      "transform, opacity",
              }}
            >
              <div style={{
                fontSize:      data.keywords.length <= 2 ? 120 : 96,
                fontWeight:    800,
                color:         kwColor,
                lineHeight:    1.05,
                letterSpacing: "-0.03em",
                fontFamily:    FONT,
                textShadow:    `0 0 80px ${kwColor}20`,
              }}>
                {kw}
              </div>
            </div>
          );
        })}
      </div>

      {/* Subtle bottom accent line */}
      <div style={{
        position:   "absolute",
        bottom:     0, left: 0, right: 0,
        height:     2,
        background: `linear-gradient(90deg, transparent, ${accent}30, transparent)`,
      }} />
    </div>
  );
};
