/**
 * TimelineFlow — chronological sequence layout.
 *
 * Motion upgrades (design pass):
 *   • MEDIUM spring tier for item entrances
 *   • Highlighted dot: continuous glow pulse
 *   • Spine: animated fill from top to bottom as items appear
 *   • ParticleBackground + TelemetryFrame
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { TimelineFlowData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { SPRING_MEDIUM } from "../utils/springIn";
import { COLOR, FONT, SectionLabelRow, ParticleBackground, TelemetryFrame } from "./_shared";

const ITEM_STAGGER = 15;

export const TimelineFlow: React.FC<{ data: TimelineFlowData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[data.accent_color ?? "cyan"];

  // Spine fill progress: fills as last item enters
  const lastItemFrame = (data.items.length - 1) * ITEM_STAGGER;
  const spineProgress = lastItemFrame > 0
    ? Math.min(1, Math.max(0, frame / (lastItemFrame + 20)))
    : Math.min(1, frame / 20);

  return (
    <div style={{
      width:          "100%",
      height:         "100%",
      background:     "radial-gradient(ellipse at 30% 50%, #111 0%, #0A0A0A 70%)",
      position:       "relative",
      overflow:       "hidden",
      display:        "flex",
      flexDirection:  "column",
      padding:        60,
      paddingTop:     52,
      boxSizing:      "border-box",
      fontFamily:     FONT,
      gap:            36,
    }}>

      <ParticleBackground frame={frame} />

      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 36, flex: 1 }}>
        <SectionLabelRow text={data.section_label} color={data.accent_color ?? "cyan"} />

        {/* Timeline body */}
        <div style={{
          flex:           1,
          display:        "flex",
          flexDirection:  "column",
          justifyContent: "center",
          position:       "relative",
          paddingLeft:    52,
        }}>
          {/* Vertical spine — base */}
          <div style={{
            position:     "absolute",
            left:         20,
            top:          16,
            bottom:       16,
            width:        2,
            background:   "rgba(255,255,255,0.06)",
            borderRadius: 1,
          }} />

          {/* Animated spine fill */}
          <div style={{
            position:     "absolute",
            left:         20,
            top:          16,
            height:       `${spineProgress * 100}%`,
            width:        2,
            background:   `linear-gradient(180deg, ${accent}60, ${accent}20)`,
            borderRadius: 1,
          }} />

          {data.items.map((item, i) => {
            const itemFrame = frame - i * ITEM_STAGGER;
            const progress  = itemFrame >= 0 ? spring({
              frame:  itemFrame,
              fps,
              config: SPRING_MEDIUM,
            }) : 0;

            const opacity    = interpolate(progress, [0, 0.22], [0, 1], { extrapolateRight: "clamp" });
            const translateX = interpolate(progress, [0, 1],    [-48, 0], { extrapolateRight: "clamp" });
            const dotSize    = item.highlight ? 18 : 11;
            const dotColor   = item.highlight ? accent : "rgba(255,255,255,0.22)";

            // Highlighted dot glow pulse
            const dotGlow = item.highlight && itemFrame > 20
              ? 10 + (Math.sin((frame / fps) * Math.PI * 2 * 0.4) * 0.5 + 0.5) * 20
              : 0;

            return (
              <div
                key={i}
                style={{
                  display:      "flex",
                  alignItems:   "center",
                  gap:          24,
                  marginBottom: i < data.items.length - 1 ? 40 : 0,
                  opacity,
                  transform:    `translateX(${translateX}px)`,
                  willChange:   "transform, opacity",
                  position:     "relative",
                }}
              >
                {/* Dot */}
                <div style={{
                  position:     "absolute",
                  left:         -(52 - 20) + (8 - dotSize / 2),
                  width:        dotSize,
                  height:       dotSize,
                  borderRadius: "50%",
                  background:   dotColor,
                  boxShadow:    item.highlight ? `0 0 ${dotGlow + 10}px ${accent}70` : "none",
                  flexShrink:   0,
                }} />

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize:      17,
                    fontWeight:    500,
                    color:         "rgba(255,255,255,0.35)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    marginBottom:  5,
                    fontFamily:    FONT,
                  }}>
                    {item.date}
                  </div>

                  <div style={{
                    display:    "flex",
                    alignItems: "baseline",
                    gap:        18,
                    flexWrap:   "wrap",
                  }}>
                    <div style={{
                      fontSize:      item.highlight ? 54 : 46,
                      fontWeight:    700,
                      color:         item.highlight ? accent : COLOR.white,
                      lineHeight:    1.1,
                      letterSpacing: "-0.025em",
                      fontFamily:    FONT,
                      textShadow:    item.highlight ? `0 0 40px ${accent}35` : "none",
                    }}>
                      {item.label}
                    </div>

                    {item.value && (
                      <div style={{
                        fontSize:      30,
                        fontWeight:    600,
                        color:         item.highlight ? accent : "rgba(255,255,255,0.45)",
                        fontFamily:    FONT,
                        letterSpacing: "-0.01em",
                      }}>
                        {item.value}
                      </div>
                    )}
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
        bottom:     0, left: 0, right: 0,
        height:     2,
        background: `linear-gradient(90deg, transparent, ${accent}30, transparent)`,
        zIndex:     2,
      }} />

      <TelemetryFrame frame={frame} />
    </div>
  );
};
