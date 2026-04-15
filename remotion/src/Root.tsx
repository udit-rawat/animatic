import React from "react";
import { Composition, staticFile, AbsoluteFill } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { VideoComposition } from "./VideoComposition";
import { LayoutRenderer } from "./LayoutRenderer";
import { CustomVideo, CustomVideoConfig } from "./CustomVideo";
import { HookR3F } from "./layouts/HookR3F";
import { SampleMVP, SampleMVPConfig } from "./SampleMVP";
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

// ── Default props (Motion Design v3 — ScenePayload format) ───────────────────
// All beats use typed SceneData discriminated unions → routed by SceneRouter.
// beat_4 uses TakeawayScene with ambient breath + word reveal + progress border.

const defaultProps: RemotionProps = {
  beats: [
    { beat: 1 },
    { beat: 2 },
    { beat: 3 },
    { beat: 4 },
  ],
  scenes: {
    beat_1: {
      animate_in: "spring_scale",
      data: {
        layout:        "MetricFocus",
        section_label: "adamax.ai",
        hero:          { value: "3B", label: "parameters", color: "green" },
        context:       "Voxtral TTS beats ElevenLabs with an open-weight model.",
        chips:         ["open-weight", "3B params", "CPU-safe"],
      },
    },
    beat_2: {
      animate_in: "spring_in",
      data: {
        layout:        "DataGrid",
        section_label: "Voxtral TTS",
        metrics: [
          { label: "Params",   value: "> 3B",   color: "cyan",  glow: true },
          { label: "RAM",      value: "> 3GB",   color: "cyan"              },
          { label: "License",  value: "Open",    color: "green", glow: true },
          { label: "Quality",  value: "+ MOS",   color: "green"             },
        ],
        highlight_index: 0,
        caption: "First open-weight model to beat ElevenLabs on MOS benchmarks.",
      },
    },
    beat_3: {
      animate_in: "fade",
      data: {
        layout:        "ComparisonSplit",
        section_label: "Latency",
        divider_label: "vs",
        left:  {
          heading: "Flash v2.5",
          color:   "red",
          metrics: [
            { label: "TTFA",    value: "340ms"  },
            { label: "Quality", value: "Baseline" },
          ],
        },
        right: {
          heading: "Voxtral",
          color:   "green",
          metrics: [
            { label: "TTFA",    value: "90ms",  glow: true },
            { label: "Quality", value: "+12 MOS" },
          ],
        },
      },
    },
    beat_4: {
      animate_in: "none",
      data: {
        layout:        "TakeawayScene",
        section_label: "takeaway",
        headline:      "Open weights now outperform closed ones. Pick your stack wisely.",
        cta:           "Follow for daily ML breakdowns",
        accent_color:  "cyan",
      },
    },
  },
  timing: {
    hook:         { start: 0.0,    duration: 11.251, end: 11.251 },
    concept_1:    { start: 11.251, duration: 12.691, end: 23.942 },
    concept_2:    { start: 23.942, duration: 14.251, end: 38.193 },
    takeaway_cta: { start: 38.193, duration: 9.771,  end: 47.964 },
  },
  audioSrc:    "narration.wav",
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
  // Compact timing: 4-beat pan test renders in ~30s
  timing: {
    hook:         { start: 0.0,  duration: 7.5, end: 7.5  },
    concept_1:    { start: 7.5,  duration: 7.5, end: 15.0 },
    concept_2:    { start: 15.0, duration: 7.5, end: 22.5 },
    takeaway_cta: { start: 22.5, duration: 7.5, end: 30.0 },
  },
  audioSrc:    "narration.wav",
  totalFrames: Math.round(30.0 * 30),
  // scenes inherited from defaultProps spread — all 4 ScenePayload beats
};

// ── Phase 3 gate composition ──────────────────────────────────────────────────

const Phase3TestComposition: React.FC = () => (
  <AbsoluteFill style={{ background: "#040408" }}>
    <HookR3F
      text="AdaMax"
      subtext="adamax.ai"
      color="#00E5FF"
      heroValue="1M+"
      heroLabel="Tokens Per Second"
      hookLine="The compute moat just shifted. Speed is the new moat."
      slamFrame={70}
      plateHeight={420}
    />
  </AbsoluteFill>
);

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

      {/* Custom generated video — one-off per topic */}
      <Composition
        id="CustomVideo"
        component={CustomVideo}
        durationInFrames={CustomVideoConfig.durationInFrames}
        fps={CustomVideoConfig.fps}
        width={CustomVideoConfig.width}
        height={CustomVideoConfig.height}
      />

      {/* SampleMVP — KV Cache 10s demo: HookR3F + GlassmorphBeat + camera pan */}
      <Composition
        id="SampleMVP"
        component={SampleMVP}
        durationInFrames={SampleMVPConfig.durationInFrames}
        fps={SampleMVPConfig.fps}
        width={SampleMVPConfig.width}
        height={SampleMVPConfig.height}
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

      {/* Phase 3 gate — R3F metallic hook pilot. Inspect PBR lighting + entrance spring.
          Run: cd remotion && npx remotion render src/index.ts Phase3Test /tmp/phase3_test.mp4 */}
      <Composition
        id="Phase3Test"
        component={Phase3TestComposition}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
