/**
 * LeaderboardRank — ordered ranking table with animated entrance.
 *
 * Use for benchmark comparisons, model rankings, pricing leaderboards.
 * Items are provided rank-order (rank 1 at top) but animate in REVERSE —
 * lower ranks appear first, rank 1 arrives last for maximum impact.
 *
 * Layout per row:
 *   [#N]  Item Name                Score
 *
 * Highlighted row: accent background tint + left glow bar.
 * Non-highlighted rows: progressively muted.
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { LeaderboardRankData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow } from "./_shared";

const ROW_STAGGER = 14; // frames between row entrances (reversed order)

export const LeaderboardRank: React.FC<{ data: LeaderboardRankData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[data.accent_color ?? "cyan"];
  const n       = data.items.length;

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
      <SectionLabelRow text={data.section_label} color={data.accent_color ?? "cyan"} />

      {/* Metric label */}
      <div style={{
        fontSize:      20,
        fontWeight:    500,
        color:         "rgba(255,255,255,0.35)",
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        fontFamily:    FONT,
        marginTop:     -16,
      }}>
        {data.metric_label}
      </div>

      {/* Rows */}
      <div style={{
        flex:           1,
        display:        "flex",
        flexDirection:  "column",
        justifyContent: "center",
        gap:            12,
      }}>
        {data.items.map((item, i) => {
          // Reverse stagger: last item enters first, rank 1 enters last
          const startFrame = (n - 1 - i) * ROW_STAGGER;
          const rowFrame   = frame - startFrame;
          const progress   = rowFrame >= 0 ? spring({
            frame:  rowFrame,
            fps,
            config: { damping: 26, stiffness: 200, overshootClamping: false },
          }) : 0;

          const opacity    = interpolate(progress, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
          const translateX = interpolate(progress, [0, 1], [-56, 0], { extrapolateRight: "clamp" });

          const isHighlight  = item.highlight;
          const rankColor    = isHighlight ? accent : "rgba(255,255,255,0.25)";
          const nameOpacity  = isHighlight ? 1.0 : Math.max(0.45, 1 - i * 0.12);
          const scoreColor   = isHighlight ? accent : "rgba(255,255,255,0.4)";

          return (
            <div
              key={i}
              style={{
                display:         "flex",
                alignItems:      "center",
                gap:             20,
                padding:         isHighlight ? "18px 20px" : "14px 20px",
                borderRadius:    12,
                background:      isHighlight ? `${accent}0D` : "transparent",
                border:          isHighlight ? `1px solid ${accent}30` : "1px solid transparent",
                opacity,
                transform:       `translateX(${translateX}px)`,
                willChange:      "transform, opacity",
              }}
            >
              {/* Rank badge */}
              <div style={{
                width:         52,
                flexShrink:    0,
                fontSize:      isHighlight ? 42 : 34,
                fontWeight:    800,
                color:         rankColor,
                letterSpacing: "-0.03em",
                fontFamily:    FONT,
                textAlign:     "right",
                textShadow:    isHighlight ? `0 0 30px ${accent}50` : "none",
              }}>
                #{item.rank}
              </div>

              {/* Divider */}
              <div style={{
                width:        2,
                height:       isHighlight ? 44 : 36,
                background:   rankColor,
                borderRadius: 1,
                flexShrink:   0,
                opacity:      0.6,
              }} />

              {/* Name */}
              <div style={{
                flex:          1,
                fontSize:      isHighlight ? 44 : 36,
                fontWeight:    isHighlight ? 700 : 500,
                color:         COLOR.white,
                opacity:       nameOpacity,
                letterSpacing: "-0.02em",
                fontFamily:    FONT,
                minWidth:      0,
                overflow:      "hidden",
                textOverflow:  "ellipsis",
                whiteSpace:    "nowrap",
              }}>
                {item.name}
              </div>

              {/* Score */}
              <div style={{
                flexShrink:    0,
                fontSize:      isHighlight ? 44 : 36,
                fontWeight:    700,
                color:         scoreColor,
                letterSpacing: "-0.02em",
                fontFamily:    FONT,
                textShadow:    isHighlight ? `0 0 24px ${accent}40` : "none",
              }}>
                {item.score}
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
