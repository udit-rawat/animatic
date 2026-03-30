/**
 * StatementSlam — kinetic insight beat.
 *
 * Replaces KineticBridge for beat_3. Instead of cycling unrelated keywords,
 * displays 2-3 short punchy lines derived directly from the narration insight.
 * Each line springs in from below with a staggered delay so the screen reads
 * progressively while the voiceover plays.
 *
 * Motion model:
 *   Line 0 enters at frame 0   — accent colour, biggest visual weight.
 *   Line 1 enters at frame 20  — white, slightly muted.
 *   Line 2 enters at frame 40  — white, most muted.
 *   After entry, line 0 breathes with a 0.25 Hz ambient scale pulse.
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { StatementSlamData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow, useBreath } from "./_shared";

const LINE_STAGGER = 20; // frames between each line entrance
const LINE_OPACITY = [1.0, 0.88, 0.68]; // per-line opacity multiplier

export const StatementSlam: React.FC<{ data: StatementSlamData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[data.accent_color ?? "cyan"];
  const { scale: breathScale } = useBreath(frame, fps);

  return (
    <div style={{
      width:          "100%",
      height:         "100%",
      background:     "#0A0A0A",
      position:       "relative",
      overflow:       "hidden",
      display:        "flex",
      flexDirection:  "column",
      padding:        60,
      boxSizing:      "border-box",
      fontFamily:     FONT,
      gap:            40,
    }}>
      <SectionLabelRow text={data.section_label} color={data.accent_color ?? "cyan"} />

      {/* Lines container — vertically centred in remaining space */}
      <div style={{
        flex:           1,
        display:        "flex",
        flexDirection:  "column",
        justifyContent: "center",
        gap:            28,
      }}>
        {data.lines.map((line, i) => {
          const lineFrame = frame - i * LINE_STAGGER;

          const progress = lineFrame >= 0 ? spring({
            frame:  lineFrame,
            fps,
            config: { damping: 26, stiffness: 200, overshootClamping: false },
          }) : 0;

          const opacity     = interpolate(progress, [0, 0.18], [0, 1], { extrapolateRight: "clamp" });
          const translateY  = interpolate(progress, [0, 1],    [44, 0], { extrapolateRight: "clamp" });
          const lineColor   = i === 0 ? accent : COLOR.white;
          const lineOpacity = opacity * (LINE_OPACITY[i] ?? 0.6);

          // Breathe only on the first line once it's fully entered
          const applyBreath = i === 0 && lineFrame > 28;

          return (
            <div
              key={i}
              style={{
                opacity:         lineOpacity,
                transform:       `translateY(${translateY}px)${applyBreath ? ` scale(${breathScale})` : ""}`,
                transformOrigin: "left center",
                willChange:      "transform, opacity",
              }}
            >
              <div style={{
                fontSize:      80,
                fontWeight:    800,
                color:         lineColor,
                lineHeight:    1.05,
                letterSpacing: "-0.03em",
                fontFamily:    FONT,
                textShadow:    i === 0 ? `0 0 60px ${accent}30` : "none",
              }}>
                {line}
              </div>
            </div>
          );
        })}
      </div>

      {/* Accent line at bottom */}
      <div style={{
        position:   "absolute",
        bottom:     0, left: 0, right: 0,
        height:     2,
        background: `linear-gradient(90deg, transparent, ${accent}40, transparent)`,
      }} />
    </div>
  );
};
