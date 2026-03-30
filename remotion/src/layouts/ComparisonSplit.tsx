/**
 * ComparisonSplit — A vs B side-by-side layout.
 *
 * Best for: before/after, baseline vs optimised, model X vs model Y.
 * Motion: left panel slides from left, right panel from right.
 * Metric cards inside each panel stagger with slideUp.
 */

import React from "react";
import { useVideoConfig } from "remotion";
import type { ComparisonSplitData, MetricItem } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { slideUp, springIn, staggerDelay } from "../utils/springIn";
import { COLOR, FONT, SectionLabelRow, HRule } from "./_shared";

// ── Inline MetricCard (avoids LayoutRenderer dependency) ──────────────────────

const Card: React.FC<{ m: MetricItem; frame: number; fps: number; delay: number }> =
  ({ m, frame, fps, delay }) => {
  const accent = COLOR[m.color ?? "cyan"];
  const { opacity, translateY } = slideUp(frame, fps, delay, "crisp");
  return (
    <div style={{
      background:   `rgba(255,255,255,0.03)`,
      border:       `1px solid ${accent}35`,
      borderRadius: 12,
      padding:      "24px 28px",
      opacity,
      transform:    `translateY(${translateY}px)`,
      boxShadow:    m.glow ? `0 0 32px ${accent}12` : undefined,
      boxSizing:    "border-box",
    }}>
      <div style={{
        fontSize:      22, fontWeight: 500, color: "#F9FAFB", opacity: 0.4,
        textTransform: "uppercase", letterSpacing: "0.12em", fontFamily: FONT, marginBottom: 8,
      }}>
        {m.label}
      </div>
      <div style={{
        fontSize: 60, fontWeight: 700, color: accent,
        lineHeight: 1.05, letterSpacing: "-0.03em", fontFamily: FONT,
      }}>
        {m.value}
      </div>
    </div>
  );
};

// ── Panel ─────────────────────────────────────────────────────────────────────

const Panel: React.FC<{
  heading:    string;
  color:      string;
  metrics:    MetricItem[];
  frame:      number;
  fps:        number;
  enterDelay: number;
  slideDir:   "left" | "right";
  isLast?:    boolean;
}> = ({ heading, color, metrics, frame, fps, enterDelay, slideDir, isLast }) => {
  const prog = springIn(frame, fps, enterDelay, "hero");
  const tx   = (slideDir === "left" ? -1 : 1) * (1 - prog) * 40;

  return (
    <div style={{
      flex:           1,
      display:        "flex",
      flexDirection:  "column",
      justifyContent: "center",
      gap:            20,
      padding:        "32px 28px",
      background:     `${color}07`,
      border:         `1px solid ${color}22`,
      borderRadius:   isLast ? "0 16px 16px 0" : "16px 0 0 16px",
      opacity:        prog,
      transform:      `translateX(${tx}px)`,
      boxSizing:      "border-box",
    }}>
      <div style={{
        fontSize:      28, fontWeight: 600, color,
        letterSpacing: "0.08em", textTransform: "uppercase", fontFamily: FONT,
      }}>
        {heading}
      </div>
      {metrics.map((m, i) => (
        <Card key={i} m={m} frame={frame} fps={fps}
          delay={staggerDelay(i, metrics.length, 16, enterDelay + 10)} />
      ))}
    </div>
  );
};

// ── Main ──────────────────────────────────────────────────────────────────────

export const ComparisonSplit: React.FC<{ data: ComparisonSplitData }> = ({ data }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const { left, right, section_label, divider_label = "vs" } = data;

  return (
    <div style={{
      padding:       60,
      display:       "flex",
      flexDirection: "column",
      gap:           32,
      height:        "100%",
      boxSizing:     "border-box",
    }}>
      <SectionLabelRow text={section_label} color="yellow" />
      <HRule />

      <div style={{ display: "flex", flex: 1, alignItems: "stretch", gap: 0 }}>
        <Panel
          heading={left.heading}
          color={COLOR[left.color]}
          metrics={left.metrics}
          frame={frame} fps={fps}
          enterDelay={6}
          slideDir="left"
        />

        {/* Centre divider */}
        <div style={{
          width:           2,
          background:      "rgba(255,255,255,0.07)",
          display:         "flex",
          alignItems:      "center",
          justifyContent:  "center",
          flexShrink:      0,
          position:        "relative",
        }}>
          <div style={{
            position:      "absolute",
            background:    "#0A0A0A",
            padding:       "12px 0",
            color:         "rgba(255,255,255,0.3)",
            fontSize:      20,
            fontWeight:    500,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            fontFamily:    FONT,
            writingMode:   "vertical-rl",
          }}>
            {divider_label}
          </div>
        </div>

        <Panel
          heading={right.heading}
          color={COLOR[right.color]}
          metrics={right.metrics}
          frame={frame} fps={fps}
          enterDelay={14}
          slideDir="right"
          isLast
        />
      </div>
    </div>
  );
};
