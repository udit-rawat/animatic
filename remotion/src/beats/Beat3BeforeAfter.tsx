/**
 * Beat3BeforeAfter — Two-panel comparison (HUD aesthetic)
 *
 * Left panel (C_RED border)  — BEFORE state
 * Right panel (C_GREEN border) — AFTER state
 *
 * Animation: panels draw in via clip-path height, then labels Write-in, then details.
 * No width= bug — labels scale naturally via CSS max-width + font-size tuning.
 */
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { ComparisonParams } from "../types";

const LEFT     = 50;
const C_RED    = "#FF4444";
const C_GREEN  = "#00FF41";
const C_WHITE  = "#FDFDFD";
const C_YELLOW = "#FFD600";

interface Props { params: ComparisonParams }

function TypeIn({ text, startFrame, fps, fontSize, color }: {
  text: string; startFrame: number; fps: number; fontSize: number; color: string;
}) {
  const frame = useCurrentFrame();
  const charsVisible = Math.floor(interpolate(
    frame,
    [startFrame, startFrame + text.length * 1.5],
    [0, text.length],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  ));
  return (
    <span style={{ fontSize, color, fontFamily: "inherit", letterSpacing: "0.04em" }}>
      {text.slice(0, charsVisible)}
    </span>
  );
}

export const Beat3BeforeAfter: React.FC<Props> = ({ params }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const conceptOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  // Panel reveal: clip-path height from 0% → 100%
  const PANEL_START = 15;
  const panelProg = spring({
    frame: Math.max(0, frame - PANEL_START),
    fps,
    config: { damping: 150, stiffness: 280, overshootClamping: true },
  });
  const panelClip = interpolate(panelProg, [0, 1], [0, 100]);

  const LABEL_START  = PANEL_START + 18; // after panels mostly revealed
  const DETAIL_START = LABEL_START + 20;

  const detailOpacity = interpolate(frame, [DETAIL_START, DETAIL_START + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const panelStyle = (borderColor: string): React.CSSProperties => ({
    flex: 1,
    border: `2px solid ${borderColor}`,
    borderRadius: 4,
    padding: "40px 30px",
    display: "flex",
    flexDirection: "column",
    gap: 28,
    background: `${borderColor}08`,
    boxShadow: `0 0 24px ${borderColor}30, inset 0 0 24px ${borderColor}0A`,
    clipPath: `inset(0 0 ${100 - panelClip}% 0)`,
    overflow: "hidden",
  });

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", fontFamily: "inherit" }}>

      {/* Concept header */}
      <div style={{
        position: "absolute",
        top: 120,
        left: LEFT,
        right: LEFT,
        fontSize: 72,
        color: C_YELLOW,
        opacity: conceptOpacity,
        lineHeight: 1.2,
        letterSpacing: "0.02em",
      }}>
        {params.concept_text}
      </div>

      {/* Two panels side by side */}
      <div style={{
        position: "absolute",
        top: 320,
        left: LEFT,
        right: LEFT,
        bottom: 80,
        display: "flex",
        gap: 24,
      }}>
        {/* BEFORE panel */}
        <div style={panelStyle(C_RED)}>
          <div style={{ fontSize: 44, color: C_RED, letterSpacing: "0.06em" }}>
            BEFORE
          </div>
          <div style={{ fontSize: 72, fontWeight: "bold", color: C_RED, lineHeight: 1.1, maxWidth: "100%" }}>
            <TypeIn text={params.before_label} startFrame={LABEL_START} fps={fps} fontSize={72} color={C_RED} />
          </div>
          <div style={{ fontSize: 52, color: C_WHITE, opacity: detailOpacity, lineHeight: 1.3 }}>
            {params.before_detail}
          </div>
        </div>

        {/* AFTER panel */}
        <div style={panelStyle(C_GREEN)}>
          <div style={{ fontSize: 44, color: C_GREEN, letterSpacing: "0.06em" }}>
            AFTER
          </div>
          <div style={{ fontSize: 72, fontWeight: "bold", color: C_GREEN, lineHeight: 1.1, maxWidth: "100%" }}>
            <TypeIn text={params.after_label} startFrame={LABEL_START + 6} fps={fps} fontSize={72} color={C_GREEN} />
          </div>
          <div style={{ fontSize: 52, color: C_GREEN, opacity: detailOpacity, lineHeight: 1.3 }}>
            {params.after_detail}
          </div>
        </div>
      </div>

    </div>
  );
};
