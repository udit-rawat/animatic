/**
 * TriStat — three-metric card stack.
 *
 * Use when a topic has 2-3 key numbers that don't fit ComparisonSplit
 * (e.g. compute cost / user revenue / daily burn — three distinct metrics,
 * not a clean left-vs-right comparison).
 *
 * Layout:
 *   Cards stacked vertically, each occupying roughly equal height.
 *   Card 0: primary stat — largest value, accent colour, glow.
 *   Cards 1-2: supporting stats — slightly muted, their own colours.
 *   Each card: left accent bar + large value + label + optional sublabel.
 *
 * Motion model:
 *   Cards spring scale-in (0.92 → 1.0) + fade with an 18-frame stagger.
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { TriStatData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow } from "./_shared";

const CARD_STAGGER = 18; // frames between card entrances

export const TriStat: React.FC<{ data: TriStatData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[data.accent_color ?? "cyan"];

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
      gap:            28,
    }}>
      <SectionLabelRow text={data.section_label} color={data.accent_color ?? "cyan"} />

      {/* Card stack — vertically centred */}
      <div style={{
        flex:           1,
        display:        "flex",
        flexDirection:  "column",
        justifyContent: "center",
        gap:            18,
      }}>
        {data.stats.map((stat, i) => {
          const cardFrame = frame - i * CARD_STAGGER;
          const progress  = cardFrame >= 0 ? spring({
            frame:  cardFrame,
            fps,
            config: { damping: 28, stiffness: 220, overshootClamping: false },
          }) : 0;

          const opacity      = interpolate(progress, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
          const scale        = interpolate(progress, [0, 1],   [0.92, 1.0], { extrapolateRight: "clamp" });
          const cardColor    = stat.color ? COLOR[stat.color as keyof typeof COLOR] ?? accent : accent;
          const borderAlpha  = i === 0 ? "55" : "28";
          const bgAlpha      = i === 0 ? "12" : "08";
          const glowShadow   = stat.glow ? `0 0 48px ${cardColor}22` : "none";

          return (
            <div
              key={i}
              style={{
                opacity,
                transform:       `scale(${scale})`,
                transformOrigin: "left center",
                willChange:      "transform, opacity",
                background:      `${cardColor}${bgAlpha}`,
                border:          `1px solid ${cardColor}${borderAlpha}`,
                borderRadius:    16,
                padding:         "26px 28px",
                display:         "flex",
                alignItems:      "center",
                gap:             24,
                boxShadow:       glowShadow,
              }}
            >
              {/* Left accent bar */}
              <div style={{
                width:        4,
                alignSelf:    "stretch",
                background:   cardColor,
                borderRadius: 2,
                opacity:      i === 0 ? 1.0 : 0.55,
                flexShrink:   0,
              }} />

              {/* Value + labels */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize:      88,
                  fontWeight:    800,
                  color:         cardColor,
                  lineHeight:    1.0,
                  letterSpacing: "-0.04em",
                  fontFamily:    FONT,
                  textShadow:    stat.glow ? `0 0 60px ${cardColor}50` : "none",
                }}>
                  {stat.value}
                </div>
                <div style={{
                  fontSize:      24,
                  fontWeight:    600,
                  color:         COLOR.white,
                  opacity:       0.82,
                  marginTop:     6,
                  fontFamily:    FONT,
                  letterSpacing: "0.01em",
                }}>
                  {stat.label}
                </div>
                {stat.sublabel && (
                  <div style={{
                    fontSize:   18,
                    fontWeight: 400,
                    color:      "rgba(255,255,255,0.38)",
                    marginTop:  4,
                    fontFamily: FONT,
                  }}>
                    {stat.sublabel}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom accent line */}
      <div style={{
        position:   "absolute",
        bottom:     0, left: 0, right: 0,
        height:     2,
        background: `linear-gradient(90deg, transparent, ${accent}30, transparent)`,
      }} />
    </div>
  );
};
