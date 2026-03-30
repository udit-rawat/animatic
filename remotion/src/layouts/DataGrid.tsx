/**
 * DataGrid — 2–4 metric cards in a responsive grid layout.
 *
 * Best for: benchmark specs, model comparisons, multi-metric snapshots.
 * Optional highlight_index gives one card a glow treatment.
 * Motion: staggered slideUp across all cards.
 */

import React from "react";
import { useVideoConfig } from "remotion";
import type { DataGridData, MetricItem } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { slideUp, staggerDelay } from "../utils/springIn";
import { COLOR, FONT, SectionLabelRow, HRule } from "./_shared";

const GridCard: React.FC<{
  m:           MetricItem;
  highlighted: boolean;
  frame:       number;
  fps:         number;
  delay:       number;
}> = ({ m, highlighted, frame, fps, delay }) => {
  const accent = COLOR[m.color ?? "cyan"];
  const { opacity, translateY } = slideUp(frame, fps, delay, "crisp");

  return (
    <div style={{
      opacity,
      transform:    `translateY(${translateY}px)`,
      background:   highlighted ? `${accent}0A` : "rgba(255,255,255,0.03)",
      border:       `1px solid ${highlighted || m.glow ? `${accent}45` : "rgba(255,255,255,0.08)"}`,
      borderRadius: 14,
      padding:      "28px 32px",
      boxShadow:    highlighted || m.glow ? `0 0 40px ${accent}10` : undefined,
      boxSizing:    "border-box",
    }}>
      <div style={{
        fontSize:      24, fontWeight: 500, color: "#F9FAFB", opacity: 0.4,
        textTransform: "uppercase", letterSpacing: "0.12em",
        fontFamily:    FONT, marginBottom: 10,
      }}>
        {m.label}
      </div>
      <div style={{
        fontSize:      68, fontWeight: 700, color: accent,
        lineHeight:    1.05, letterSpacing: "-0.03em", fontFamily: FONT,
      }}>
        {m.value}
      </div>
    </div>
  );
};

export const DataGrid: React.FC<{ data: DataGridData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const cols    = data.metrics.length <= 2 ? 2
                : data.metrics.length === 3 ? 3
                : 2;

  return (
    <div style={{
      padding:       60,
      display:       "flex",
      flexDirection: "column",
      gap:           32,
      height:        "100%",
      boxSizing:     "border-box",
    }}>
      <SectionLabelRow text={data.section_label} color="yellow" />
      <HRule />

      <div style={{
        display:               "grid",
        gridTemplateColumns:   `repeat(${cols}, 1fr)`,
        gap:                   20,
      }}>
        {data.metrics.map((m, i) => (
          <GridCard
            key={i}
            m={m}
            highlighted={i === data.highlight_index}
            frame={frame}
            fps={fps}
            delay={staggerDelay(i, data.metrics.length, 24, 0)}
          />
        ))}
      </div>

      {data.caption && (
        <div style={{ fontSize: 28, color: "#F9FAFB", opacity: 0.35, fontFamily: FONT }}>
          {data.caption}
        </div>
      )}
    </div>
  );
};
