/**
 * TakeawayScene — kinetic outro layout. Kills the "dead air" problem.
 *
 * Anti-dead-air mechanisms:
 *   1. AmbientDots     — 3 deterministic floating glow orbs (no Math.random)
 *   2. BeatBreath      — continuous 0.25 Hz scale/opacity pulse on the card
 *   3. WordReveal      — headline splits into words, each springs in independently
 *   4. ProgressBorder  — glowing bar fills the full beat duration → forward momentum
 *   5. CTAChip         — pops in after headline completes (spring-scale, overshoot)
 *
 * Usage: wire in VideoComposition when scenePayload.data.layout === "TakeawayScene".
 * durationFrames must be passed from VideoComposition (Math.round(entry.duration * fps)).
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { TakeawaySceneData } from "../types";
import { useBeatFrame } from "../hooks/useBeatFrame";
import { COLOR, FONT } from "./_shared";

// ── Deterministic floating glow dot ──────────────────────────────────────────

const AmbientDot: React.FC<{
  frame: number;
  fps:   number;
  seed:  number;
  color: string;
}> = ({ frame, fps, seed, color }) => {
  const t      = frame / fps;
  const xBase  = (seed * 237.3) % 100;
  const yBase  = (seed * 173.1) % 80 + 10;
  const xDrift = Math.sin(t * 0.3 + seed) * 2.5;
  const yDrift = Math.cos(t * 0.2 + seed * 1.7) * 1.8;
  const pulse  = 0.14 + Math.sin(t * 0.4 + seed * 2.3) * 0.07;

  return (
    <div style={{
      position:     "absolute",
      left:         `${xBase + xDrift}%`,
      top:          `${yBase + yDrift}%`,
      width:        180,
      height:       180,
      borderRadius: "50%",
      background:   color,
      opacity:      pulse,
      filter:       "blur(72px)",
      transform:    "translate(-50%, -50%)",
      pointerEvents:"none",
    }} />
  );
};

// ── Per-word spring reveal ────────────────────────────────────────────────────

const WordReveal: React.FC<{
  text:      string;
  frame:     number;
  fps:       number;
  baseDelay: number;
  fontSize:  number;
  color:     string;
}> = ({ text, frame, fps, baseDelay, fontSize, color }) => {
  // trim() + split(/\s+/) guards against leading/trailing spaces and multi-space
  // runs that would produce empty "" tokens and invisible gap-eating spans.
  const words = text.trim().split(/\s+/);

  return (
    // BUG FIX: do NOT use gap/columnGap with "em" units on the container — em
    // resolves against the container's own font-size (typically 16px default),
    // NOT the span's font-size (68px here). At 16px, 0.28em ≈ 4.5px: invisible.
    // Fix: paddingRight on each span, where em resolves against the span's own
    // fontSize — so 0.3em at fontSize:68 = ~20px, correct word spacing.
    <div style={{ display: "flex", flexWrap: "wrap", lineHeight: 1.3 }}>
      {words.map((word, i) => {
        const delay    = baseDelay + i * 5;
        const progress = spring({
          frame: Math.max(0, frame - delay),
          fps,
          // BUG FIX: bounce-up spring.
          // Old: damping:24, stiffness:160, translateY from 28px — barely perceptible.
          // New: damping:18 (less resistance → real oscillation past rest),
          //      stiffness:220 (snappier initial velocity),
          //      translateY from 120px (comes from further below).
          // overshootClamping:false lets it spring past 0 → genuine bounce.
          config: { damping: 18, stiffness: 220, overshootClamping: false },
        });
        const isLast = i === words.length - 1;
        return (
          <span key={i} style={{
            display:     "inline-block",
            opacity:     interpolate(progress, [0, 0.2], [0, 1], { extrapolateRight: "clamp" }),
            transform:   `translateY(${interpolate(progress, [0, 1], [120, 0])}px)`,
            fontSize,
            fontWeight:  700,
            color,
            fontFamily:  FONT,
            letterSpacing: "-0.02em",
            // Correct word spacing: em resolves against THIS span's fontSize.
            paddingRight: isLast ? 0 : "0.3em",
          }}>
            {word}
          </span>
        );
      })}
    </div>
  );
};

// ── Progress border ────────────────────────────────────────────────────────────

const ProgressBorder: React.FC<{
  frame:          number;
  durationFrames: number;
  color:          string;
}> = ({ frame, durationFrames, color }) => {
  const pct = interpolate(frame, [0, durationFrames], [0, 100], { extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", bottom: 0, left: 0, width: "100%", height: 3,
      background: "rgba(255,255,255,0.04)",
    }}>
      <div style={{
        width:      `${pct}%`,
        height:     "100%",
        background: `linear-gradient(90deg, ${color}00, ${color}CC)`,
        boxShadow:  `0 0 14px ${color}80`,
      }} />
    </div>
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────

const ACCENT: Record<string, string> = {
  cyan:   COLOR.cyan,
  green:  COLOR.green,
  yellow: COLOR.yellow,
};

export const TakeawayScene: React.FC<{
  data:           TakeawaySceneData;
  durationFrames: number;
}> = ({ data, durationFrames }) => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const accent  = ACCENT[data.accent_color ?? "cyan"];

  // ── Card entrance (spring slide-up) ─────────────────────────────────────────
  const cardEntry = spring({ frame: Math.max(0, frame), fps,
    config: { damping: 28, stiffness: 160, overshootClamping: false } });
  const cardOpacity    = interpolate(cardEntry, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
  const cardTranslateY = interpolate(cardEntry, [0, 1], [44, 0]);

  // ── Continuous breath after entrance (kicks in at ~frame 20) ───────────────
  const breathPhase = (frame / fps) * Math.PI * 2 * 0.25;
  const breathScale = 1 + Math.sin(breathPhase) * 0.011;

  // ── Section label fade ──────────────────────────────────────────────────────
  const labelOpacity = interpolate(cardEntry, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });

  // ── CTA pop-in (after last word lands) ─────────────────────────────────────
  const wordCount = data.headline.split(" ").length;
  const ctaDelay  = 12 + wordCount * 5 + 18;
  const ctaEntry  = spring({ frame: Math.max(0, frame - ctaDelay), fps,
    config: { damping: 32, stiffness: 260, overshootClamping: true } });
  const ctaScale   = interpolate(ctaEntry, [0, 1], [0.6, 1]);
  const ctaOpacity = interpolate(ctaEntry, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{
      width:     "100%",
      height:    "100%",
      background:"#0A0A0A",
      position:  "relative",
      overflow:  "hidden",
      fontFamily: FONT,
    }}>
      {/* ── Ambient layer (behind content) ── */}
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <AmbientDot frame={frame} fps={fps} seed={1} color={`${accent}18`} />
        <AmbientDot frame={frame} fps={fps} seed={4} color={`${accent}0E`} />
        <AmbientDot frame={frame} fps={fps} seed={7} color="rgba(255,255,255,0.04)" />
      </div>

      {/* ── Content layer ── */}
      <div style={{
        position:      "relative",
        zIndex:        1,
        display:       "flex",
        flexDirection: "column",
        justifyContent:"center",
        height:        "100%",
        padding:       60,
        boxSizing:     "border-box",
        gap:           36,
      }}>
        {/* Section micro-label */}
        <div style={{
          fontSize:      20, fontWeight: 500, color: accent,
          letterSpacing: "0.18em", textTransform: "uppercase",
          opacity:       labelOpacity,
        }}>
          {data.section_label}
        </div>

        {/* Frosted glass card — breathes continuously */}
        <div style={{
          background:   "rgba(255,255,255,0.035)",
          border:       `1px solid ${accent}35`,
          borderRadius: 20,
          padding:      "52px 48px",
          boxShadow:    `0 0 80px ${accent}10, inset 0 1px 0 rgba(255,255,255,0.06)`,
          opacity:      cardOpacity,
          transform:    `translateY(${cardTranslateY}px) scale(${breathScale})`,
          position:     "relative",
          overflow:     "hidden",
        }}>
          {/* Inner accent line */}
          <div style={{
            position:   "absolute", top: 0, left: 48, right: 48, height: 1,
            background: `linear-gradient(90deg, transparent, ${accent}60, transparent)`,
          }} />

          <WordReveal
            text={data.headline}
            frame={frame}
            fps={fps}
            baseDelay={12}
            fontSize={68}
            color="#F9FAFB"
          />
        </div>

        {/* CTA chip */}
        {data.cta && (
          <div style={{
            alignSelf:     "flex-start",
            background:    `${accent}14`,
            border:        `1px solid ${accent}40`,
            borderRadius:  100,
            padding:       "14px 32px",
            fontSize:      28,
            color:         accent,
            fontWeight:    500,
            letterSpacing: "0.04em",
            opacity:       ctaOpacity,
            transform:     `scale(${ctaScale})`,
          }}>
            {data.cta}
          </div>
        )}
      </div>

      {/* ── Progress border fills over beat duration ── */}
      <ProgressBorder frame={frame} durationFrames={durationFrames} color={accent} />
    </div>
  );
};
