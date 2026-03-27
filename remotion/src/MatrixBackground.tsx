/**
 * MatrixBackground.tsx — Deterministic matrix data stream (Motion Design v2 — Phase 3)
 *
 * Falling katakana + ASCII characters in a column grid.
 * Renders as a fixed viewport layer behind all beat content.
 *
 * Audio reactivity (per TDD §PILLAR 3):
 *   bassEnergy → fall speed:   speed = bassEnergy × 8 + 2  px/frame
 *   midEnergy  → opacity:      baseOpacity = midEnergy × 0.15 + 0.03
 *
 * Determinism rules (CRITICAL — Remotion renders frames in parallel workers):
 *   - ALL randomness uses Math.sin() / Math.cos() seeded on (col, t, frame).
 *   - Math.random() is NEVER used.
 *   - Character position and identity are pure functions of (frame, bassEnergy, col, t).
 */

import React from "react";
import { useCurrentFrame } from "remotion";

// ── Character set ─────────────────────────────────────────────────────────────

const KATAKANA =
  "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモラリルレロ";
const ASCII = "0123456789ABCDEF><+=-";
const CHARS = KATAKANA + ASCII;   // ~56 chars total

// ── Layout constants ──────────────────────────────────────────────────────────

const CHAR_SIZE = 36;                            // px — ~30 columns at 1080px wide
const NUM_COLS  = Math.floor(1080 / CHAR_SIZE);  // 30
const TRAIL_LEN = 14;                            // chars per falling trail
const CANVAS_H  = 1920;

// ── Component ─────────────────────────────────────────────────────────────────

interface MatrixBackgroundProps {
  bassEnergy: number;   // 0–1 → controls fall speed
  midEnergy:  number;   // 0–1 → controls character opacity
}

export const MatrixBackground: React.FC<MatrixBackgroundProps> = ({
  bassEnergy,
  midEnergy,
}) => {
  const frame = useCurrentFrame();

  const speed       = bassEnergy * 8 + 2;             // px / frame
  const baseOpacity = midEnergy  * 0.15 + 0.03;       // base alpha for trail tail
  const totalH      = CANVAS_H + TRAIL_LEN * CHAR_SIZE;

  const elements: React.ReactNode[] = [];

  for (let col = 0; col < NUM_COLS; col++) {
    // Deterministic per-column phase spreads columns across full canvas height
    const phase = Math.abs(Math.sin(col * 13.7)) * totalH;
    // Head Y of trail — wraps around totalH
    const headY = (frame * speed + phase) % totalH - TRAIL_LEN * CHAR_SIZE;

    for (let t = 0; t < TRAIL_LEN; t++) {
      const y = headY + t * CHAR_SIZE;
      if (y < -CHAR_SIZE || y > CANVAS_H) continue;

      // Quadratic fade from head (t=0) to tail (t=TRAIL_LEN-1)
      const fadeRatio = 1 - t / TRAIL_LEN;
      const isHead    = t === 0;
      const opacity   = Math.pow(fadeRatio, 2) * baseOpacity * (isHead ? 4 : 1);
      if (opacity < 0.007) continue;

      // Deterministic char selection — flickers every 3 frames for organic feel
      const charFrame = Math.floor(frame / 3);
      const charIdx   =
        Math.abs(
          Math.floor(Math.sin(col * 1000 + t * 37 + charFrame * 7) * 10000)
        ) % CHARS.length;

      elements.push(
        <div
          key={`${col}-${t}`}
          style={{
            position: "absolute",
            left: col * CHAR_SIZE,
            top:  Math.round(y),
            width:      CHAR_SIZE,
            height:     CHAR_SIZE,
            fontSize:   24,
            color:      isHead ? "#FFFFFF" : "#00FF41",
            opacity,
            textAlign:  "center",
            lineHeight: `${CHAR_SIZE}px`,
            fontFamily: "inherit",
            textShadow: isHead ? "0 0 6px #00FF41" : undefined,
          }}
        >
          {CHARS[charIdx]}
        </div>
      );
    }
  }

  return (
    <div
      style={{
        position:      "absolute",
        top:           0,
        left:          0,
        width:         "100%",
        height:        "100%",
        overflow:      "hidden",
        pointerEvents: "none",
      }}
    >
      {elements}
    </div>
  );
};
