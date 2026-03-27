/**
 * CRTWrapper.tsx — CRT post-processing overlay (Motion Design v2 — Phase 4)
 *
 * Wraps VideoComposition content with 4 effect layers (z-order per TDD §PILLAR 4):
 *
 *   z=100  Scanlines       — repeating-linear-gradient, 4px pitch, always on, zero GPU cost
 *   z=101  Vignette        — radial-gradient, always on
 *   z=102  Chroma aberr.   — red/cyan channel split, gated: |cameraVelocity|>15 AND CRT_ABERRATION=1
 *   z=103  Screen grain    — 64×64 deterministic sin/cos tile, gated: highEnergy > 0.1
 *
 * WARNING: chromatic aberration uses mixBlendMode which can be slow in Puppeteer.
 * It is hard-gated behind CRT_ABERRATION=1 env var. Default is disabled.
 */

import React from "react";
import { useCurrentFrame } from "remotion";

// ── Grain pattern ─────────────────────────────────────────────────────────────
// 64×64 px tile built from 16×16 cells (4×4 px each).
// Deterministic: seeded on (x, y, frame) — no Math.random().

function makeGrainPattern(frame: number): string {
  const GRID = 16; // 16×16 cells → 64×64 px tile
  const rects: string[] = [];

  for (let y = 0; y < GRID; y++) {
    for (let x = 0; x < GRID; x++) {
      const v = Math.abs(Math.sin(x * 127.1 + y * 311.7 + frame * 74.3));
      rects.push(
        `<rect x="${x * 4}" y="${y * 4}" width="4" height="4" fill-opacity="${v.toFixed(3)}"/>`
      );
    }
  }

  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'>` +
    `<g fill='white'>${rects.join("")}</g></svg>`;

  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface CRTWrapperProps {
  /** px/frame camera movement — drives chromatic aberration gate */
  cameraVelocity: number;
  /** 0–1 presence/air energy from audio — drives screen grain gate */
  highEnergy: number;
  children: React.ReactNode;
}

export const CRTWrapper: React.FC<CRTWrapperProps> = ({
  cameraVelocity,
  highEnergy,
  children,
}) => {
  const frame = useCurrentFrame();

  // ── Effect 3: Chromatic aberration ────────────────────────────────────────
  // Hard-gated behind CRT_ABERRATION=1 env var to avoid Puppeteer perf hit.
  const aberrationEnabled =
    typeof process !== "undefined" &&
    process.env != null &&
    process.env.CRT_ABERRATION === "1";

  const velocityAbs  = Math.abs(cameraVelocity);
  const aberrationPx =
    aberrationEnabled && velocityAbs > 15
      ? Math.min(velocityAbs / 20, 4) // max 4px channel split
      : 0;

  // ── Effect 4: Screen grain ─────────────────────────────────────────────────
  const grainOpacity   = highEnergy > 0.1 ? highEnergy * 0.08 + 0.02 : 0;
  const grainPattern   = grainOpacity > 0 ? makeGrainPattern(frame) : "";

  return (
    <div
      style={{
        position: "relative",
        width:    "100%",
        height:   "100%",
        overflow: "hidden",
      }}
    >
      {children}

      {/* ── z=100: Scanlines — always on ─────────────────────────────────── */}
      {/* 4px pitch → 480 scanlines across 1920px. Pure CSS, no compute cost. */}
      <div
        style={{
          position:      "absolute",
          inset:         0,
          pointerEvents: "none",
          zIndex:        100,
          background:
            "repeating-linear-gradient(" +
            "0deg, " +
            "transparent 0px, transparent 3px, " +
            "rgba(0,0,0,0.12) 3px, rgba(0,0,0,0.12) 4px" +
            ")",
        }}
      />

      {/* ── z=101: Vignette — always on ──────────────────────────────────── */}
      <div
        style={{
          position:      "absolute",
          inset:         0,
          pointerEvents: "none",
          zIndex:        101,
          background:
            "radial-gradient(" +
            "ellipse 85% 85% at 50% 50%, " +
            "transparent 55%, " +
            "rgba(0,0,0,0.55) 100%" +
            ")",
        }}
      />

      {/* ── z=102: Chromatic aberration — gated ──────────────────────────── */}
      {aberrationPx > 0 && (
        <>
          {/* Red channel: shift right */}
          <div
            style={{
              position:      "absolute",
              inset:         0,
              transform:     `translateX(${aberrationPx}px)`,
              background:    "rgba(255, 0, 60, 0.06)",
              mixBlendMode:  "screen",
              pointerEvents: "none",
              zIndex:        102,
            }}
          />
          {/* Cyan channel: shift left */}
          <div
            style={{
              position:      "absolute",
              inset:         0,
              transform:     `translateX(-${aberrationPx}px)`,
              background:    "rgba(0, 255, 220, 0.06)",
              mixBlendMode:  "screen",
              pointerEvents: "none",
              zIndex:        102,
            }}
          />
        </>
      )}

      {/* ── z=103: Screen grain — gated on highEnergy > 0.1 ─────────────── */}
      {grainOpacity > 0 && (
        <div
          style={{
            position:           "absolute",
            inset:              0,
            pointerEvents:      "none",
            zIndex:             103,
            opacity:            grainOpacity,
            backgroundImage:    `url("${grainPattern}")`,
            backgroundRepeat:   "repeat",
            backgroundSize:     "64px 64px",
          }}
        />
      )}
    </div>
  );
};
