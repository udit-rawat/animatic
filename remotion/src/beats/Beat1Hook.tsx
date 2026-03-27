/**
 * Beat1Hook — Terminal / HUD aesthetic
 *
 * Layout (1080×1920 canvas, absolute positioning):
 *   y=120px  — "user@adamax:~$ " prompt (C_GREEN, instant)
 *   y=810px  — stat (FS_STAT=240px, C_GREEN, springs in via overdamped spring)
 *   y=1100px — hook phrase (FS_HOOK=90px, C_WHITE, typewriter effect)
 *   y=below hook — blinking "_" cursor (C_GREEN, blinks @15-frame intervals)
 *
 * All text left-anchored at x=50px (mirrors Manim's x=-6.5 console alignment).
 */
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { HookParams } from "../types";

const LEFT   = 50;   // px from left edge — terminal left anchor
const C_GREEN = "#00FF41";
const C_WHITE = "#FDFDFD";

interface Props { params: HookParams }

export const Beat1Hook: React.FC<Props> = ({ params }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const stat     = params.hook_stat;
  const hookText = params.hook_text;

  // ── 1. Stat springs in (frames 0 → ~36, ~1.2s) ──────────────────────────
  // overshootClamping: true + high damping = ease_out_expo equivalent, no bounce
  const statProgress = spring({
    frame,
    fps,
    config: { damping: 200, stiffness: 380, overshootClamping: true },
  });
  const statScale   = interpolate(statProgress, [0, 1], [0.5, 1.0]);
  const statOpacity = interpolate(statProgress, [0, 0.1], [0, 1], { extrapolateRight: "clamp" });

  // ── 2. Hook text typewriter (starts at frame 36) ─────────────────────────
  const HOOK_START     = 36; // 1.2s
  const CHARS_PER_FRAME = 1.5; // characters revealed per frame
  const charsVisible   = Math.floor(
    interpolate(frame, [HOOK_START, HOOK_START + hookText.length / CHARS_PER_FRAME], [0, hookText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );
  const visibleHook    = hookText.slice(0, charsVisible);
  const typewriterDone = charsVisible >= hookText.length;

  // ── 3. Blinking cursor (after typewriter completes, 15-frame on/off) ─────
  const BLINK_INTERVAL = 15; // frames per half-cycle = 0.5s period
  const cursorOn       = typewriterDone && (Math.floor(frame / BLINK_INTERVAL) % 2 === 0);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", fontFamily: "inherit" }}>

      {/* Terminal prompt — persistent throughout beat */}
      <div style={{
        position: "absolute",
        top: 120,
        left: LEFT,
        fontSize: 48,
        color: C_GREEN,
        letterSpacing: "0.02em",
        opacity: 1,
      }}>
        user@adamax:~$
      </div>

      {/* Stat — springs in from 50% → 100% scale */}
      <div style={{
        position: "absolute",
        top: 810,
        left: LEFT,
        fontSize: 240,
        fontWeight: "bold",
        color: C_GREEN,
        lineHeight: 1,
        opacity: statOpacity,
        transform: `scale(${statScale})`,
        transformOrigin: "left center",
        textShadow: `0 0 40px ${C_GREEN}80, 0 0 80px ${C_GREEN}40`,
      }}>
        {stat}
      </div>

      {/* Hook text — typewriter reveal */}
      <div style={{
        position: "absolute",
        top: 1100,
        left: LEFT,
        fontSize: 90,
        color: C_WHITE,
        maxWidth: 980,
        lineHeight: 1.25,
        letterSpacing: "0.01em",
        whiteSpace: "pre-wrap",
      }}>
        {visibleHook}
        {/* Blinking cursor inline after last character */}
        <span style={{
          color: C_GREEN,
          opacity: cursorOn ? 1 : 0,
          textShadow: `0 0 10px ${C_GREEN}`,
        }}>
          _
        </span>
      </div>

    </div>
  );
};
