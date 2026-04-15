/**
 * CustomVideo.tsx — Local Knowledge Graph for Claude Code
 * 615 frames · 30fps · 20.5s · Terminal Phosphor v1.1
 *
 * beat_1  frames   0–148   Hook — "8.2x" slam · claude_screen.mp4 bg (screen blend)
 * beat_2  frames 148–275   TriStat template — 3 metrics
 * beat_3  frames 275–468   StatementSlam template — 3 lines
 * beat_4  frames 468–615   TakeawayScene template — CTA
 *
 * Render: npx remotion render CustomVideo ../output/video.mp4 --gl=angle
 */

import React from "react";
import {
  useVideoConfig,
  Audio, Video, staticFile, spring, interpolate,
} from "remotion";

import { TriStat }       from "./layouts/TriStat";
import { StatementSlam } from "./layouts/StatementSlam";
import { TakeawayScene } from "./layouts/TakeawayScene";

import {
  usePulseAt,
  COLOR, FONT,
  TelemetryFrame, SectionLabelRow, useBreath,
} from "./layouts/_shared";
import { SPRING_HEAVY, SPRING_MEDIUM } from "./utils/springIn";
import { useCameraY }   from "./hooks/useCameraY";
import { useBeatFrame } from "./hooks/useBeatFrame";
import { CameraViewport, VirtualCanvas, BeatZone } from "./CameraViewport";

import type { TriStatData, StatementSlamData, TakeawaySceneData } from "./types";

const GREEN = "#00FF41";
const BG    = "#0A0E13";
const JB    = "'JetBrains Mono', 'Fira Code', monospace";

const TIMING = {
  hook:         { start: 0,      end: 4.931,  duration: 4.931 },
  concept_1:    { start: 4.931,  end: 9.182,  duration: 4.251 },
  concept_2:    { start: 9.182,  end: 15.593, duration: 6.411 },
  takeaway_cta: { start: 15.593, end: 20.484, duration: 4.891 },
};

const Beat1: React.FC = () => {
  const frame   = useBeatFrame();
  const { fps } = useVideoConfig();
  const { scale: bs } = useBreath(frame, fps);

  const videoOp = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const heroSp    = spring({ frame: Math.max(0, frame - 45), fps, config: SPRING_HEAVY });
  const heroScale = interpolate(heroSp, [0, 1], [0.5, 1], { extrapolateRight: "clamp" });
  const heroOp    = interpolate(heroSp, [0, 0.15], [0, 1], { extrapolateRight: "clamp" });

  const labelSp = spring({ frame: Math.max(0, frame - 57), fps, config: SPRING_MEDIUM });
  const labelOp = interpolate(labelSp, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });

  const hookSp = spring({ frame: Math.max(0, frame - 73), fps, config: SPRING_MEDIUM });
  const hookOp = interpolate(hookSp, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });
  const hookY  = interpolate(hookSp, [0, 1], [14, 0]);

  const pulse = usePulseAt(frame, [60, 110], GREEN, 20);
  const glow  = 16 + (Math.sin((frame / fps) * Math.PI * 2 * 0.55) * 0.5 + 0.5) * 10;

  return (
    <div style={{ width: "100%", height: "100%", background: BG, position: "relative", overflow: "hidden" }}>

      <Video
        src={staticFile("claude_screen.mp4")}
        style={{
          position: "absolute", inset: 0,
          width: "100%", height: "100%",
          objectFit: "cover",
          opacity: videoOp * 0.65,
          mixBlendMode: "screen",
          zIndex: 1,
        }}
        muted
      />

      <div style={{
        position: "absolute", inset: 0, zIndex: 2,
        display: "flex", flexDirection: "column",
        alignItems: "flex-start", justifyContent: "center",
        paddingTop: 120, paddingBottom: 180,
        paddingLeft: 72, paddingRight: 72,
        boxSizing: "border-box", gap: 16,
      }}>

        <SectionLabelRow text="TOKEN REDUCTION" color="green" />

        <div style={{
          opacity: heroOp,
          transform: `scale(${heroScale * (frame > 60 ? bs : 1)})`,
          transformOrigin: "left center",
          boxShadow: pulse,
        }}>
          <div style={{
            fontFamily: JB, fontSize: 148, fontWeight: 900,
            color: GREEN, lineHeight: 0.95, letterSpacing: "-2px",
            textShadow: `0 0 ${glow}px ${GREEN}70, 0 0 ${glow * 2}px ${GREEN}25`,
          }}>
            8.2x
          </div>
        </div>

        <div style={{ opacity: labelOp }}>
          <div style={{
            fontFamily: JB, fontSize: 28, fontWeight: 600,
            color: GREEN, letterSpacing: "0.1em", textTransform: "uppercase",
            textShadow: `0 0 12px ${GREEN}50`,
          }}>
            fewer tokens
          </div>
        </div>

        <div style={{ opacity: hookOp, transform: `translateY(${hookY}px)`, marginTop: 8 }}>
          <div style={{
            fontFamily: FONT, fontSize: 40, fontWeight: 700,
            color: "rgba(255,255,255,0.75)", lineHeight: 1.2,
          }}>
            Claude Code reads only what matters.
          </div>
        </div>

      </div>

      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 3 }}>
        <TelemetryFrame frame={frame} />
      </div>
    </div>
  );
};

const BEAT2_DATA: TriStatData = {
  layout: "TriStat", section_label: "CODE MAP", accent_color: "green",
  stats: [
    { value: "8.2x",  label: "fewer tokens", sublabel: "on code reviews",        color: "green", glow: true },
    { value: "49x",   label: "fewer tokens", sublabel: "on daily coding tasks",  color: "green" },
    { value: "1 map", label: "parse once",   sublabel: "tree-sitter AST cached", color: "white" },
  ],
};

const Beat2: React.FC = () => <TriStat data={BEAT2_DATA} />;

const BEAT3_DATA: StatementSlamData = {
  layout: "StatementSlam", section_label: "WHY IT WORKS", accent_color: "green",
  lines: [
    "Reads only relevant files.",
    "8.2x fewer review tokens.",
    "49x fewer on daily code.",
  ],
};

const Beat3: React.FC = () => <StatementSlam data={BEAT3_DATA} />;

const BEAT4_DATA: TakeawaySceneData = {
  layout: "TakeawayScene", section_label: "TAKEAWAY",
  headline: "8.2x fewer tokens. Run it.",
  cta: "pip install code-review-graph",
  accent_color: "green",
};

const Beat4: React.FC = () => <TakeawayScene data={BEAT4_DATA} durationFrames={147} />;

export const CustomVideoConfig = {
  durationInFrames: 615,
  fps: 30, width: 1080, height: 1920,
};

export const CustomVideo: React.FC = () => {
  const { cameraY } = useCameraY(TIMING, 4);

  return (
    <div style={{ width: "100%", height: "100%", background: BG, position: "relative" }}>
      <Audio src={staticFile("narration.wav")} />
      <CameraViewport cameraY={cameraY}>
        <VirtualCanvas totalBeats={4}>
          <BeatZone index={0} beatStartFrame={0}><Beat1 /></BeatZone>
          <BeatZone index={1} beatStartFrame={148}><Beat2 /></BeatZone>
          <BeatZone index={2} beatStartFrame={275}><Beat3 /></BeatZone>
          <BeatZone index={3} beatStartFrame={468}><Beat4 /></BeatZone>
        </VirtualCanvas>
      </CameraViewport>
    </div>
  );
};
