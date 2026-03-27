import React from "react";
import { Composition, staticFile } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { VideoComposition } from "./VideoComposition";
import { LayoutRenderer } from "./LayoutRenderer";
import type { RemotionProps, BeatLayout, LayoutNode } from "./types";

const FPS     = 30;
const PADDING = FPS; // 1 second breathing room after narration ends

/**
 * dynamicDuration — async calculateMetadata for VideoComposition.
 *
 * Reads the actual audio file duration every render, so the video length
 * auto-adjusts to TTS output without manual totalFrames bookkeeping.
 * Falls back to props.totalFrames if audio file is unavailable (preview mode).
 */
async function dynamicDuration({
  props,
}: {
  props: Record<string, unknown>;
}): Promise<{ durationInFrames: number }> {
  const p = props as unknown as RemotionProps;
  try {
    const duration = await getAudioDurationInSeconds(staticFile(p.audioSrc));
    return { durationInFrames: Math.ceil(duration * FPS) + PADDING };
  } catch {
    // Audio not in public/ yet (e.g. studio preview) — fall back to prop value
    return { durationInFrames: p.totalFrames ?? 1440 };
  }
}

// ── Default props (new BeatLayout format) ─────────────────────────────────────
// All params are now BeatLayout objects: { animate_in, layout: LayoutNode }

const defaultProps: RemotionProps = {
  beats: [
    { beat: 1 },
    { beat: 2 },
    { beat: 3 },
    { beat: 4 },
  ],
  params: {
    beat_1: {
      animate_in: "spring_scale",
      layout: {
        type: "column",
        gap: 32,
        justify: "flex-start",
        padding: 60,
        children: [
          { type: "SectionLabel", text: "adamax.ai", color: "cyan" },
          { type: "Spacer", size: 650 },
          { type: "NumberCounter", value: "3B", label: "parameters", color: "green", delay: 0 },
          { type: "Spacer", size: 32 },
          { type: "TerminalText", text: "ElevenLabs beaten.", size: "lg",
            color: "white", typewriter: true, cursor: true, delay: 20 },
        ],
      },
    },
    beat_2: {
      animate_in: "spring_in",
      layout: {
        type: "column",
        gap: 32,
        padding: 60,
        children: [
          { type: "SectionLabel", text: "Voxtral TTS", color: "yellow" },
          { type: "Divider", color: "white", opacity: 0.12 },
          { type: "TerminalText", text: "Open-weight model, closed-source performance.",
            size: "sm", color: "white" },
          { type: "grid", columns: 2, gap: 24, children: [
            { type: "MetricCard", label: "Params", value: "> 3B",
              color: "cyan", glow: true, delay: 0 },
            { type: "MetricCard", label: "RAM",    value: "> 3GB",
              color: "cyan", glow: true, delay: 8 },
          ]},
        ],
      },
    },
    beat_3: {
      animate_in: "fade",
      layout: {
        type: "column",
        gap: 32,
        padding: 60,
        children: [
          { type: "SectionLabel", text: "Latency", color: "yellow" },
          { type: "Divider", color: "white", opacity: 0.12 },
          { type: "row", gap: 24, children: [
            { type: "column", gap: 16, children: [
              { type: "TerminalText", text: "Flash v2.5", size: "sm", color: "red" },
              { type: "MetricCard", label: "TTFA", value: "Slower",
                color: "red", delay: 0 },
            ]},
            { type: "column", gap: 16, children: [
              { type: "TerminalText", text: "Voxtral", size: "sm", color: "green" },
              { type: "MetricCard", label: "TTFA", value: "90ms",
                color: "green", glow: true, delay: 8 },
            ]},
          ]},
        ],
      },
    },
    beat_4: {
      animate_in: "typewriter",
      layout: {
        type: "column",
        gap: 32,
        padding: 60,
        children: [
          { type: "SectionLabel", text: "takeaway", color: "cyan" },
          { type: "Spacer", size: 700 },
          { type: "TerminalText",
            text: "Open weights now outperform closed ones. What's your bias?",
            size: "lg", color: "white", typewriter: true, cursor: true, delay: 0 },
        ],
      },
    },
  },
  timing: {
    hook:         { start: 0.0,    duration: 11.251, end: 11.251 },
    concept_1:    { start: 11.251, duration: 12.691, end: 23.942 },
    concept_2:    { start: 23.942, duration: 14.251, end: 38.193 },
    takeaway_cta: { start: 38.193, duration: 9.771,  end: 47.964 },
  },
  audioSrc: "narration.wav",
  totalFrames: Math.round(47.964 * 30),
};

// ── Phase 1 gate — kept for reference ────────────────────────────────────────
// Run: cd remotion && npx remotion render src/index.ts LayoutTest /tmp/gate_test.mp4

const GATE_TREE: LayoutNode = {
  type: "column",
  gap: 32,
  justify: "flex-start",
  padding: 60,
  children: [
    { type: "SectionLabel", text: "adamax.ai", color: "cyan" },
    { type: "Spacer", size: 650 },
    { type: "NumberCounter", value: "3B", label: "parameters", color: "green", delay: 0 },
    { type: "Spacer", size: 32 },
    { type: "TerminalText", text: "ElevenLabs beaten.", size: "lg",
      color: "white", typewriter: true, cursor: true, delay: 20 },
  ],
};

const GateTestComposition: React.FC = () => (
  <div style={{
    width: "100%", height: "100%",
    background: "#0A0A0A", position: "relative", overflow: "hidden",
    fontFamily: "'Inter', 'system-ui', sans-serif",
  }}>
    <LayoutRenderer node={GATE_TREE} />
  </div>
);

// ── Phase 2 gate — 4-beat test with camera pans ───────────────────────────────
// Run: cd remotion && npx remotion render src/index.ts Phase2Test /tmp/phase2_test.mp4
// Inspect: camera should spring-pan between the 4 beats at ~11s intervals.

const phase2Props: RemotionProps = {
  ...defaultProps,
  // Use compact timing so the 4-beat pan test renders quickly (~30s video)
  timing: {
    hook:         { start: 0.0,  duration: 7.5, end: 7.5  },
    concept_1:    { start: 7.5,  duration: 7.5, end: 15.0 },
    concept_2:    { start: 15.0, duration: 7.5, end: 22.5 },
    takeaway_cta: { start: 22.5, duration: 7.5, end: 30.0 },
  },
  audioSrc:    "narration.wav",
  totalFrames: Math.round(30.0 * 30),
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyComponent = React.ComponentType<any>;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VideoComposition"
        component={VideoComposition as AnyComponent}
        durationInFrames={defaultProps.totalFrames}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps as unknown as Record<string, unknown>}
        calculateMetadata={dynamicDuration}
      />

      {/* Phase 1 gate — LayoutRenderer with hardcoded Beat1Hook tree */}
      <Composition
        id="LayoutTest"
        component={GateTestComposition}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Phase 2 gate — 4-beat video, inspect spring camera pans between beats */}
      <Composition
        id="Phase2Test"
        component={VideoComposition as AnyComponent}
        durationInFrames={phase2Props.totalFrames}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={phase2Props as unknown as Record<string, unknown>}
        calculateMetadata={dynamicDuration}
      />
    </>
  );
};
