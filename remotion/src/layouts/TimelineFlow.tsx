/**
 * TimelineFlow — chronological sequence layout.
 *
 * Use for topics that have a clear narrative arc over time:
 * launches, collapses, product lifecycles, research milestones.
 *
 * Layout (always vertical — portrait 1080×1920):
 *   • Left spine: thin connecting line with dots per milestone.
 *   • Each item: dot → date label (muted, small) → event label (large) → optional value.
 *   • Highlighted item: accent dot with glow, larger text, accent colour.
 *
 * Motion model:
 *   Items slide in from the left with a 15-frame stagger between each.
 *   Highlighted item gets an extra glow pulse on entry.
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { TimelineFlowData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT, SectionLabelRow } from "./_shared";

const ITEM_STAGGER = 15; // frames between item entrances

export const TimelineFlow: React.FC<{ data: TimelineFlowData }> = ({ data }) => {
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
      gap:            36,
    }}>
      <SectionLabelRow text={data.section_label} color={data.accent_color ?? "cyan"} />

      {/* Timeline body */}
      <div style={{
        flex:           1,
        display:        "flex",
        flexDirection:  "column",
        justifyContent: "center",
        position:       "relative",
        paddingLeft:    52, // room for spine + dot
      }}>
        {/* Vertical spine */}
        <div style={{
          position:   "absolute",
          left:       20,
          top:        16,
          bottom:     16,
          width:      2,
          background: "rgba(255,255,255,0.08)",
          borderRadius: 1,
        }} />

        {data.items.map((item, i) => {
          const itemFrame = frame - i * ITEM_STAGGER;
          const progress  = itemFrame >= 0 ? spring({
            frame:  itemFrame,
            fps,
            config: { damping: 24, stiffness: 180, overshootClamping: false },
          }) : 0;

          const opacity    = interpolate(progress, [0, 0.22], [0, 1], { extrapolateRight: "clamp" });
          const translateX = interpolate(progress, [0, 1],    [-48, 0], { extrapolateRight: "clamp" });
          const dotSize    = item.highlight ? 18 : 11;
          const dotColor   = item.highlight ? accent : "rgba(255,255,255,0.22)";

          return (
            <div
              key={i}
              style={{
                display:         "flex",
                alignItems:      "center",
                gap:             24,
                marginBottom:    i < data.items.length - 1 ? 40 : 0,
                opacity,
                transform:       `translateX(${translateX}px)`,
                willChange:      "transform, opacity",
                position:        "relative",
              }}
            >
              {/* Dot — centred on the spine */}
              <div style={{
                position:     "absolute",
                left:         -(52 - 20) + (8 - dotSize / 2), // align to spine centre
                width:        dotSize,
                height:       dotSize,
                borderRadius: "50%",
                background:   dotColor,
                boxShadow:    item.highlight ? `0 0 20px ${accent}70` : "none",
                flexShrink:   0,
              }} />

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {/* Date micro-label */}
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

                {/* Event label + value */}
                <div style={{
                  display:     "flex",
                  alignItems:  "baseline",
                  gap:         18,
                  flexWrap:    "wrap",
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
