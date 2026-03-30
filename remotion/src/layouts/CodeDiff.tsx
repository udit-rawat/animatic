/**
 * CodeDiff — before/after code block layout.
 *
 * Use for "one weird trick" topics: drop-in replacements, API migrations,
 * single-line fixes that have outsized impact.
 *
 * Layout:
 *   [BEFORE]   ← dim red block, enters first, slightly muted
 *   [AFTER]    ← bright green/accent block, springs in after, glow
 *
 * Motion model:
 *   Before block fades in at frame 0 (opacity target 0.5 — intentionally dim).
 *   After block springs in at frame 22 with scale + fade.
 *   Each line of the after block staggers in with a 10-frame delay between lines.
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { CodeDiffData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow } from "./_shared";

const CODE_FONT   = "'JetBrains Mono', 'Fira Code', 'Courier New', monospace";
const AFTER_START = 22; // frame when after block begins entering
const LINE_STAGGER = 10; // frames between after-block lines

const RED    = "#EF4444";
const GREEN  = "#10B981";

export const CodeDiff: React.FC<{ data: CodeDiffData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = data.accent_color ? COLOR[data.accent_color] : GREEN;

  // Before block: fades in quickly, stays dim
  const beforeProgress = spring({
    frame:  Math.max(0, frame),
    fps,
    config: { damping: 30, stiffness: 300 },
  });
  const beforeOpacity = interpolate(beforeProgress, [0, 0.3], [0, 0.52], { extrapolateRight: "clamp" });

  // After block container
  const afterFrame    = frame - AFTER_START;
  const afterProgress = afterFrame >= 0 ? spring({
    frame:  afterFrame,
    fps,
    config: { damping: 26, stiffness: 200 },
  }) : 0;
  const afterOpacity   = interpolate(afterProgress, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
  const afterScale     = interpolate(afterProgress, [0, 1], [0.96, 1.0], { extrapolateRight: "clamp" });
  const afterTranslate = interpolate(afterProgress, [0, 1], [20, 0], { extrapolateRight: "clamp" });

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
      paddingTop:     52,
      boxSizing:      "border-box",
      fontFamily:     FONT,
      gap:            32,
    }}>
      <SectionLabelRow text={data.section_label} color={data.accent_color ?? "green"} />

      <div style={{
        flex:           1,
        display:        "flex",
        flexDirection:  "column",
        justifyContent: "center",
        gap:            24,
      }}>
        {/* BEFORE block */}
        <div style={{ opacity: beforeOpacity, willChange: "opacity" }}>
          {/* Label */}
          <div style={{
            fontSize:      18,
            fontWeight:    600,
            color:         RED,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            fontFamily:    FONT,
            marginBottom:  10,
            opacity:       0.8,
          }}>
            ✕  {data.before.label}
          </div>

          {/* Code block */}
          <div style={{
            background:   "rgba(239, 68, 68, 0.06)",
            border:       `1px solid rgba(239, 68, 68, 0.22)`,
            borderRadius: 12,
            padding:      "22px 28px",
          }}>
            {data.before.lines.map((line, i) => (
              <div
                key={i}
                style={{
                  fontSize:      44,
                  fontWeight:    500,
                  color:         "rgba(255,255,255,0.55)",
                  lineHeight:    1.55,
                  letterSpacing: "-0.01em",
                  fontFamily:    CODE_FONT,
                  textDecoration: "line-through",
                  textDecorationColor: "rgba(239,68,68,0.4)",
                }}
              >
                {line}
              </div>
            ))}
          </div>
        </div>

        {/* AFTER block */}
        <div style={{
          opacity:         afterOpacity,
          transform:       `translateY(${afterTranslate}px) scale(${afterScale})`,
          transformOrigin: "left center",
          willChange:      "transform, opacity",
        }}>
          {/* Label */}
          <div style={{
            fontSize:      18,
            fontWeight:    600,
            color:         accent,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            fontFamily:    FONT,
            marginBottom:  10,
          }}>
            ✓  {data.after.label}
          </div>

          {/* Code block */}
          <div style={{
            background:   `${accent}0D`,
            border:       `1px solid ${accent}35`,
            borderRadius: 12,
            padding:      "22px 28px",
            boxShadow:    `0 0 48px ${accent}15`,
          }}>
            {data.after.lines.map((line, i) => {
              const lineFrame    = afterFrame - i * LINE_STAGGER;
              const lineProgress = lineFrame >= 0 ? spring({
                frame:  lineFrame,
                fps,
                config: { damping: 28, stiffness: 220 },
              }) : 0;
              const lineOpacity = interpolate(lineProgress, [0, 0.25], [0, 1], { extrapolateRight: "clamp" });

              return (
                <div
                  key={i}
                  style={{
                    fontSize:      44,
                    fontWeight:    600,
                    color:         COLOR.white,
                    lineHeight:    1.55,
                    letterSpacing: "-0.01em",
                    fontFamily:    CODE_FONT,
                    opacity:       lineOpacity,
                    textShadow:    `0 0 20px ${accent}30`,
                  }}
                >
                  {line}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom accent line */}
      <div style={{
        position:   "absolute",
        bottom:     0, left: 0, right: 0,
        height:     2,
        background: `linear-gradient(90deg, transparent, ${accent}40, transparent)`,
      }} />
    </div>
  );
};
