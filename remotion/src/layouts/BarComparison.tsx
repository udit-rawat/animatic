/**
 * BarComparison — horizontal bar chart for N items against one metric.
 *
 * Motion upgrades (design pass):
 *   • Highlighted bar: continuous shimmer glare sweeps left→right every 90 frames
 *   • Highlighted label: slow 8px rightward drift over beat duration
 *   • MEDIUM spring tier (single-frame overshoot) for bar fills
 *   • ParticleBackground + TelemetryFrame
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { BarComparisonData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow, ParticleBackground, TelemetryFrame } from "./_shared";
import { SPRING_MEDIUM } from "../utils/springIn";

const ROW_STAGGER  = 15;
const BAR_DELAY    = 8;
const BAR_HEIGHT   = 28;
const VALUE_WIDTH  = 120;

const parseNum = (v: string): number => parseFloat(v.replace(/[^0-9.]/g, "")) || 1;

export const BarComparison: React.FC<{ data: BarComparisonData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[data.accent_color ?? "cyan"];

  const rawValues = data.items.map(item => parseNum(item.value));
  const maxVal    = Math.max(...rawValues, 1);

  // Shimmer: sweeps left→right over 90 frames, repeating
  const shimmerCycle = 90;
  const shimmerPos   = ((frame % shimmerCycle) / shimmerCycle) * 140 - 20; // -20% → 120%

  return (
    <div style={{
      width:         "100%",
      height:        "100%",
      background:    "radial-gradient(ellipse at 50% 40%, #111 0%, #0A0A0A 70%)",
      position:      "relative",
      overflow:      "hidden",
      display:       "flex",
      flexDirection: "column",
      padding:       60,
      paddingTop:    52,
      boxSizing:     "border-box",
      fontFamily:    FONT,
      gap:           32,
    }}>

      <ParticleBackground frame={frame} />

      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 32, flex: 1 }}>
        <SectionLabelRow text={data.section_label} color={data.accent_color ?? "cyan"} />

        <div style={{
          flex:          1,
          display:       "flex",
          flexDirection: "column",
          justifyContent:"center",
          gap:           28,
        }}>
          {data.items.map((item, i) => {
            const rowFrame = frame - i * ROW_STAGGER;
            const barFrame = rowFrame - BAR_DELAY;

            const rowProgress = rowFrame >= 0 ? spring({
              frame: rowFrame, fps, config: SPRING_MEDIUM,
            }) : 0;

            const barProgress = barFrame >= 0 ? spring({
              frame: barFrame, fps, config: SPRING_MEDIUM,
            }) : 0;

            const rowOpacity = interpolate(rowProgress, [0, 0.22], [0, 1], { extrapolateRight: "clamp" });
            const translateX = interpolate(rowProgress, [0, 1], [-40, 0], { extrapolateRight: "clamp" });
            const barScaleX  = interpolate(barProgress, [0, 1], [0, 1], { extrapolateRight: "clamp" });

            const widthFraction = rawValues[i] / maxVal;
            const isHighlight   = item.highlight;
            const barColor      = isHighlight ? accent : "rgba(255,255,255,0.18)";
            const valueColor    = isHighlight ? accent : "rgba(255,255,255,0.4)";

            // Highlight label: slow rightward drift — 8px over the whole beat
            const labelDrift = isHighlight ? interpolate(frame, [0, 300], [0, 8], { extrapolateRight: "clamp" }) : 0;

            return (
              <div key={i} style={{
                opacity:    rowOpacity,
                transform:  `translateX(${translateX}px)`,
                willChange: "transform, opacity",
              }}>
                {/* Label */}
                <div style={{
                  fontSize:      isHighlight ? 28 : 24,
                  fontWeight:    isHighlight ? 600 : 400,
                  color:         COLOR.white,
                  opacity:       isHighlight ? 1.0 : 0.55,
                  letterSpacing: "-0.01em",
                  fontFamily:    FONT,
                  marginBottom:  10,
                  transform:     `translateX(${labelDrift}px)`,
                  transition:    "none",
                }}>
                  {item.label}
                </div>

                {/* Bar track + value */}
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
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
                      left: 0, top: 0, bottom: 0,
                      width:           `${widthFraction * 100}%`,
                      background:      isHighlight
                        ? `linear-gradient(90deg, ${accent}cc, ${accent})`
                        : barColor,
                      borderRadius:    6,
                      transform:       `scaleX(${barScaleX})`,
                      transformOrigin: "left center",
                      boxShadow:       isHighlight ? `0 0 20px ${accent}50` : "none",
                    }} />

                    {/* Shimmer sweep — only on highlighted bar, only after it's grown */}
                    {isHighlight && barScaleX > 0.95 && (
                      <div style={{
                        position:     "absolute",
                        top: 0, bottom: 0,
                        left:         `${shimmerPos}%`,
                        width:        "20%",
                        background:   "linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)",
                        transform:    "skewX(-15deg)",
                        pointerEvents:"none",
                      }} />
                    )}
                  </div>

                  <div style={{
                    flexShrink:    0,
                    width:         VALUE_WIDTH,
                    fontSize:      isHighlight ? 34 : 28,
                    fontWeight:    700,
                    color:         valueColor,
                    letterSpacing: "-0.02em",
                    fontFamily:    FONT,
                    textShadow:    isHighlight ? `0 0 20px ${accent}50` : "none",
                  }}>
                    {item.value}{item.unit ? ` ${item.unit}` : ""}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom accent line */}
      <div style={{
        position:   "absolute",
        bottom: 0, left: 0, right: 0,
        height:     2,
        background: `linear-gradient(90deg, transparent, ${accent}30, transparent)`,
        zIndex:     2,
      }} />

      <TelemetryFrame frame={frame} />
    </div>
  );
};
