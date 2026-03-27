/**
 * Beat2Pipeline — Vertical pipeline / mechanism (HUD aesthetic)
 *
 * Steps stagger-reveal top-to-bottom via spring, then connector arrows appear.
 * Each step: thin cyan border box (stroke_width=2 equivalent via CSS border).
 * Arrows: thin vertical line with arrowhead, C_GREEN.
 */
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { PipelineParams } from "../types";

const LEFT    = 50;
const C_CYAN  = "#00E5FF";
const C_GREEN = "#00FF41";
const C_WHITE = "#FDFDFD";
const C_YELLOW = "#FFD600";

interface Props { params: PipelineParams }

export const Beat2Pipeline: React.FC<Props> = ({ params }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const steps = params.pipeline_steps.slice(0, 5);
  const n     = steps.length;

  const conceptOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const STEP_START  = 15;
  const LAG_FRAMES  = 8;
  const ARROW_START = STEP_START + n * LAG_FRAMES + 6;

  // Box geometry
  const BOX_HEIGHT = 120;
  const ARROW_H    = 40;
  const TOTAL_H    = n * BOX_HEIGHT + (n - 1) * ARROW_H;
  const TOP_OFFSET = (1920 - 280 - TOTAL_H) / 2 + 280; // vertically centered below concept text

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

      {/* Pipeline stack */}
      <div style={{
        position: "absolute",
        top: TOP_OFFSET,
        left: 80,
        right: 80,
        display: "flex",
        flexDirection: "column",
        alignItems: "stretch",
      }}>
        {steps.map((step, i) => {
          const stepDelay = STEP_START + i * LAG_FRAMES;
          const stepProg  = spring({
            frame: Math.max(0, frame - stepDelay),
            fps,
            config: { damping: 200, stiffness: 380, overshootClamping: true },
          });
          const stepOpacity = interpolate(stepProg, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
          const stepScale   = interpolate(stepProg, [0, 1], [0.92, 1], { extrapolateRight: "clamp" });

          const arrowDelay = ARROW_START + i * 4;
          const arrowProg  = interpolate(frame, [arrowDelay, arrowDelay + 8], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          return (
            <React.Fragment key={i}>
              {/* Step box */}
              <div style={{
                opacity: stepOpacity,
                transform: `scaleY(${stepScale})`,
                transformOrigin: "top center",
                background: "rgba(0, 229, 255, 0.04)",
                border: `2px solid ${C_CYAN}`,
                borderRadius: 4,
                height: BOX_HEIGHT,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: `0 0 16px ${C_CYAN}30`,
              }}>
                <span style={{ fontSize: 56, color: C_WHITE, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  {step}
                </span>
              </div>

              {/* Connector arrow (not after last step) */}
              {i < n - 1 && (
                <div style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  height: ARROW_H,
                  opacity: arrowProg,
                }}>
                  <div style={{ width: 2, flex: 1, background: C_GREEN }} />
                  {/* Arrowhead */}
                  <div style={{
                    width: 0,
                    height: 0,
                    borderLeft: "10px solid transparent",
                    borderRight: "10px solid transparent",
                    borderTop: `14px solid ${C_GREEN}`,
                  }} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

    </div>
  );
};
