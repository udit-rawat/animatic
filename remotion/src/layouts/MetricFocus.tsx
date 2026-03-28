/**
 * MetricFocus — hero metric display layout.
 *
 * Best for: single dramatic stat reveal (90ms TTFA, 3.8× throughput, $0.002/call).
 * Structure:
 *   SectionLabel
 *   ── huge hero number (scale spring, HERO preset)
 *   ── supporting label
 *   ── context sentence (slide-up, delayed)
 *   ── optional chip row (staggered)
 */

import React from "react";
import { useVideoConfig } from "remotion";
import type { MetricFocusData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { scaleIn, slideUp, staggerDelay } from "../utils/springIn";
import { COLOR, FONT, SectionLabelRow } from "./_shared";

export const MetricFocus: React.FC<{ data: MetricFocusData }> = ({ data }) => {
  const frame      = useBeatFrame();
  const { fps }    = useVideoConfig();
  const accent     = COLOR[data.hero.color ?? "cyan"];

  const { opacity: heroOpacity, scale: heroScale } = scaleIn(frame, fps, 8, "hero");
  const ctx = slideUp(frame, fps, 28, "crisp");

  // Scale hero font down for values longer than 4 chars so they don't overflow.
  // 880 / 4 chars = exactly 220px (unchanged for short values like "3.8×", "40%").
  // 880 / 8 chars = 110px — safe for the 8-char max the schema enforces.
  const heroFontSize = Math.min(220, Math.floor(880 / Math.max(data.hero.value.length, 1)));

  return (
    <div style={{
      padding:        60,
      display:        "flex",
      flexDirection:  "column",
      gap:            32,
      height:         "100%",
      boxSizing:      "border-box",
      justifyContent: "center",
      fontFamily:     FONT,
    }}>
      <SectionLabelRow text={data.section_label} color="yellow" />

      {/* Hero number */}
      <div style={{
        opacity:         heroOpacity,
        transform:       `scale(${heroScale})`,
        transformOrigin: "left center",
      }}>
        <div style={{
          fontSize:      heroFontSize,
          fontWeight:    800,
          color:         accent,
          lineHeight:    0.9,
          letterSpacing: "-0.04em",
          fontFamily:    FONT,
          textShadow:    `0 0 120px ${accent}25`,
          maxWidth:      "100%",
          overflow:      "hidden",
          whiteSpace:    "nowrap",
        }}>
          {data.hero.value}
        </div>
        <div style={{
          fontSize:       36,
          fontWeight:     500,
          color:          "#F9FAFB",
          opacity:        0.45,
          letterSpacing:  "0.12em",
          textTransform:  "uppercase",
          fontFamily:     FONT,
          marginTop:      12,
        }}>
          {data.hero.label}
        </div>
      </div>

      {/* Context */}
      <div style={{
        opacity:    ctx.opacity * 0.65,
        transform:  `translateY(${ctx.translateY}px)`,
        fontSize:   44,
        color:      "#F9FAFB",
        lineHeight: 1.4,
        fontFamily: FONT,
        fontWeight: 400,
        maxWidth:   900,
      }}>
        {data.context}
      </div>

      {/* Chips */}
      {data.chips && data.chips.length > 0 && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {data.chips.map((chip, i) => {
            const sl = slideUp(
              frame, fps,
              staggerDelay(i, data.chips!.length, 16, 44),
              "crisp",
            );
            return (
              <span key={i} style={{
                opacity:       sl.opacity,
                transform:     `translateY(${sl.translateY}px)`,
                display:       "inline-block",
                background:    `${accent}12`,
                border:        `1px solid ${accent}35`,
                color:         accent,
                padding:       "10px 24px",
                borderRadius:  100,
                fontSize:      26,
                fontWeight:    500,
                fontFamily:    FONT,
                letterSpacing: "0.04em",
              }}>
                {chip}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};
