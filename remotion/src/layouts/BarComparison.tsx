/**
 * BarComparison — horizontal bar chart for N items against one metric.
 *
 * Use when magnitude IS the story — the visual gap between bars conveys the
 * insight faster than numbers alone. Best for throughput, latency, cost
 * comparisons where you have 2-5 items sharing a single unit.
 *
 * Layout per row:
 *   Label           [████████████████░░░]  382 tok/s
 *
 * Highlighted bar: accent colour + glow + full label opacity.
 * Other bars: progressively muted colour.
 *
 * Motion model:
 *   Rows fade + slide in from left with a 15-frame stagger.
 *   Bar fills grow from 0 → target width via spring scaleX.
 *   Bar growth starts 8 frames after the row is visible.
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { BarComparisonData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow } from "./_shared";

const ROW_STAGGER  = 15;
const BAR_DELAY    = 8;  // frames after row visible before bar starts growing
const BAR_HEIGHT   = 28;
const LABEL_WIDTH  = 260; // px reserved for item label on the left
const VALUE_WIDTH  = 120; // px reserved for value text on the right

const parseNum = (v: string): number => parseFloat(v.replace(/[^0-9.]/g, "")) || 1;

export const BarComparison: React.FC<{ data: BarComparisonData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[data.accent_color ?? "cyan"];

  // Compute max value once for relative bar widths
  const rawValues  = data.items.map(item => parseNum(item.value));
  const maxVal     = Math.max(...rawValues, 1);

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

      {/* Bar rows — vertically centred */}
      <div style={{
        flex:           1,
        display:        "flex",
        flexDirection:  "column",
        justifyContent: "center",
        gap:            28,
      }}>
        {data.items.map((item, i) => {
          const rowFrame  = frame - i * ROW_STAGGER;
          const barFrame  = rowFrame - BAR_DELAY;

          const rowProgress = rowFrame >= 0 ? spring({
            frame:  rowFrame,
            fps,
            config: { damping: 24, stiffness: 180 },
          }) : 0;

          const barProgress = barFrame >= 0 ? spring({
            frame:  barFrame,
            fps,
            config: { damping: 22, stiffness: 140 },
          }) : 0;

          const rowOpacity   = interpolate(rowProgress, [0, 0.22], [0, 1], { extrapolateRight: "clamp" });
          const translateX   = interpolate(rowProgress, [0, 1], [-40, 0], { extrapolateRight: "clamp" });
          const barScaleX    = interpolate(barProgress, [0, 1], [0, 1], { extrapolateRight: "clamp" });

          const widthFraction = rawValues[i] / maxVal;
          const isHighlight   = item.highlight;
          const barColor      = isHighlight ? accent : "rgba(255,255,255,0.18)";
          const labelOpacity  = isHighlight ? 1.0 : 0.55;
          const valueColor    = isHighlight ? accent : "rgba(255,255,255,0.4)";

          return (
            <div
              key={i}
              style={{
                opacity:   rowOpacity,
                transform: `translateX(${translateX}px)`,
                willChange: "transform, opacity",
              }}
            >
              {/* Label */}
              <div style={{
                fontSize:      isHighlight ? 28 : 24,
                fontWeight:    isHighlight ? 600 : 400,
                color:         COLOR.white,
                opacity:       labelOpacity,
                letterSpacing: "-0.01em",
                fontFamily:    FONT,
                marginBottom:  10,
              }}>
                {item.label}
              </div>

              {/* Bar track + value */}
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                {/* Track */}
                <div style={{
                  flex:         1,
                  height:       isHighlight ? BAR_HEIGHT + 4 : BAR_HEIGHT,
                  background:   "rgba(255,255,255,0.06)",
                  borderRadius: 6,
                  overflow:     "hidden",
                  position:     "relative",
                }}>
                  {/* Filled bar */}
                  <div style={{
                    position:        "absolute",
                    left:            0,
                    top:             0,
                    bottom:          0,
                    width:           `${widthFraction * 100}%`,
                    background:      isHighlight
                      ? `linear-gradient(90deg, ${accent}cc, ${accent})`
                      : barColor,
                    borderRadius:    6,
                    transform:       `scaleX(${barScaleX})`,
                    transformOrigin: "left center",
                    boxShadow:       isHighlight ? `0 0 20px ${accent}40` : "none",
                  }} />
                </div>

                {/* Value + unit */}
                <div style={{
                  flexShrink:    0,
                  width:         VALUE_WIDTH,
                  fontSize:      isHighlight ? 34 : 28,
                  fontWeight:    700,
                  color:         valueColor,
                  letterSpacing: "-0.02em",
                  fontFamily:    FONT,
                  textShadow:    isHighlight ? `0 0 20px ${accent}40` : "none",
                }}>
                  {item.value}{item.unit ? ` ${item.unit}` : ""}
                </div>
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
