/**
 * BeatStatsGrid — HUD stats card grid
 *
 * 2–6 cards arranged in a CSS grid.
 * Cards stagger-reveal via LaggedStart equivalent (each card delays by 6 frames).
 * Each card: thin cyan border (box-shadow glow), LABEL in cyan, "> VALUE" in white.
 *
 * Grid layout mirrors Python _layout():
 *   n=1-2 : 2 columns
 *   n=3   : 3 columns (1 row)
 *   n=4   : 2×2
 *   n=5-6 : 3 columns
 */
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { StatsGridParams } from "../types";

const LEFT    = 50;
const C_CYAN  = "#00E5FF";
const C_WHITE = "#FDFDFD";
const C_YELLOW = "#FFD600";

interface Props { params: StatsGridParams }

function gridColumns(n: number): number {
  if (n <= 2) return 2;
  if (n === 3) return 3;
  if (n === 4) return 2;
  return 3; // 5-6
}

export const BeatStatsGrid: React.FC<Props> = ({ params }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const items   = params.grid_items.slice(0, 6);
  const n       = items.length;
  const cols    = gridColumns(n);

  // Concept text fades in over first 15 frames (0.5s)
  const conceptOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const CARD_START = 15; // cards begin after concept text
  const LAG_FRAMES = 6;  // stagger between cards

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", fontFamily: "inherit" }}>

      {/* Concept header — TEXT ZONE */}
      <div style={{
        position: "absolute",
        top: 120,
        left: LEFT,
        right: LEFT,
        fontSize: 72,
        color: C_YELLOW,
        opacity: conceptOpacity,
        letterSpacing: "0.02em",
        lineHeight: 1.2,
      }}>
        {params.concept_text}
      </div>

      {/* Stats grid — ANIM ZONE */}
      <div style={{
        position: "absolute",
        top: 380,
        left: LEFT,
        right: LEFT,
        bottom: 80,
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 24,
        alignContent: "center",
      }}>
        {items.map((item, i) => {
          const cardDelay = CARD_START + i * LAG_FRAMES;
          const cardProgress = spring({
            frame: Math.max(0, frame - cardDelay),
            fps,
            config: { damping: 200, stiffness: 380, overshootClamping: true },
          });
          const opacity   = interpolate(cardProgress, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });
          const translateY = interpolate(cardProgress, [0, 1], [20, 0], { extrapolateRight: "clamp" });

          return (
            <div
              key={i}
              style={{
                opacity,
                transform: `translateY(${translateY}px)`,
                background: "rgba(0, 229, 255, 0.04)",
                border: `2px solid ${C_CYAN}`,
                borderRadius: 4,
                padding: "32px 28px",
                display: "flex",
                flexDirection: "column",
                gap: 16,
                boxShadow: `0 0 20px ${C_CYAN}30, inset 0 0 20px ${C_CYAN}08`,
                minHeight: 200,
              }}
            >
              {/* Label */}
              <div style={{
                fontSize: 52,
                color: C_CYAN,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}>
                {item.label}
              </div>
              {/* Value with "> " terminal prefix */}
              <div style={{
                fontSize: 68,
                color: C_WHITE,
                fontWeight: "bold",
                letterSpacing: "0.02em",
                lineHeight: 1,
              }}>
                {item.value.startsWith(">") ? item.value : `> ${item.value}`}
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
};
