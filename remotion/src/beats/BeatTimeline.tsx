/**
 * BeatTimeline — Vertical chronological timeline (HUD aesthetic)
 *
 * Left column: year labels (C_CYAN)
 * Center: vertical spine with dots (C_CYAN)
 * Right column: event labels (C_WHITE)
 *
 * Events stagger-reveal top-to-bottom.
 * Spine draws down progressively as events appear.
 */
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { TimelineParams } from "../types";

const C_CYAN   = "#00E5FF";
const C_WHITE  = "#FDFDFD";
const C_YELLOW = "#FFD600";
const LEFT     = 50;

interface Props { params: TimelineParams }

export const BeatTimeline: React.FC<Props> = ({ params }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const events = params.timeline_events.slice(0, 6);
  const n      = events.length;

  const conceptOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const EVENT_START  = 18;
  const LAG_FRAMES   = 10;
  const TOTAL_ANIM   = EVENT_START + n * LAG_FRAMES;

  // Spine draws down progressively
  const spineProgress = interpolate(frame, [EVENT_START, TOTAL_ANIM], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const ROW_HEIGHT  = Math.min(220, Math.floor((1920 - 400) / n));
  const TOTAL_SPINE = (n - 1) * ROW_HEIGHT;

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

      {/* Timeline body */}
      <div style={{
        position: "absolute",
        top: 340,
        left: 40,
        right: 40,
        display: "grid",
        gridTemplateColumns: "200px 60px 1fr",
        rowGap: 0,
      }}>
        {events.map((event, i) => {
          const delay    = EVENT_START + i * LAG_FRAMES;
          const prog     = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: { damping: 200, stiffness: 380, overshootClamping: true },
          });
          const opacity  = interpolate(prog, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
          const slideX   = interpolate(prog, [0, 1], [-20, 0], { extrapolateRight: "clamp" });

          // Spine visibility at this row
          const spineVisible = spineProgress >= i / Math.max(n - 1, 1);

          return (
            <React.Fragment key={i}>
              {/* Year label */}
              <div style={{
                fontSize: 52,
                color: C_CYAN,
                opacity,
                transform: `translateX(${slideX}px)`,
                textAlign: "right",
                paddingRight: 20,
                lineHeight: `${ROW_HEIGHT}px`,
                letterSpacing: "0.04em",
              }}>
                {event.year}
              </div>

              {/* Spine column: dot + connecting line */}
              <div style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                height: ROW_HEIGHT,
              }}>
                {/* Dot */}
                <div style={{
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: C_CYAN,
                  border: `2px solid ${C_CYAN}`,
                  boxShadow: `0 0 12px ${C_CYAN}`,
                  marginTop: ROW_HEIGHT / 2 - 8,
                  opacity: opacity > 0.5 ? 1 : 0,
                  flexShrink: 0,
                }} />
                {/* Connecting line to next dot */}
                {i < n - 1 && (
                  <div style={{
                    width: 2,
                    flex: 1,
                    background: C_CYAN,
                    opacity: spineVisible ? 0.6 : 0,
                    marginTop: 4,
                  }} />
                )}
              </div>

              {/* Event label */}
              <div style={{
                fontSize: 52,
                color: C_WHITE,
                opacity,
                transform: `translateX(${-slideX}px)`,
                paddingLeft: 20,
                lineHeight: 1.25,
                alignSelf: "center",
                height: ROW_HEIGHT,
                display: "flex",
                alignItems: "center",
              }}>
                {event.label}
              </div>
            </React.Fragment>
          );
        })}
      </div>

    </div>
  );
};
