/**
 * VideoComposition.tsx — Motion Design v2 (Phase 4 — final)
 *
 * Full component tree:
 *   <VideoComposition>
 *     ├── <Audio />
 *     ├── <MatrixBackground bassEnergy midEnergy />      ← Phase 3: audio-reactive bg
 *     └── <CRTWrapper cameraVelocity highEnergy>         ← Phase 4: post-processing
 *         └── <CameraViewport cameraY>                   ← Phase 2: spring camera
 *             └── <VirtualCanvas totalBeats>
 *                 └── <BeatZone index beatStartFrame> × n
 *                     └── <LayoutRenderer node />        ← Phase 1: generative layout
 *
 * Hooks called at root (once per frame):
 *   useCameraY()      → cameraY (px) + cameraVelocity (px/frame)
 *   useAudioMetrics() → rms, bassEnergy, midEnergy, highEnergy (all 0-1)
 */

import React from "react";
import { Audio, staticFile } from "remotion";
import type { RemotionProps, TimingEntry } from "./types";
import { LayoutRenderer }    from "./LayoutRenderer";
import { CameraViewport, VirtualCanvas, BeatZone } from "./CameraViewport";
import { useCameraY }        from "./hooks/useCameraY";
import { useAudioMetrics }   from "./hooks/useAudioMetrics";
import { MatrixBackground }  from "./MatrixBackground";
import { CRTWrapper }        from "./CRTWrapper";

const FPS = 30;

/** Maps 1-based beat number to narration_timing.json key */
function beatToTimingKey(beatNum: number, totalBeats: number): string {
  if (beatNum === 1) return "hook";
  if (beatNum === totalBeats) return "takeaway_cta";
  return `concept_${beatNum - 1}`;
}

export const VideoComposition: React.FC<RemotionProps> = ({
  beats,
  params,
  timing,
  audioSrc,
}) => {
  const totalBeats = beats.length;

  // ── Camera — lifted here so velocity reaches CRTWrapper ─────────────────────
  const { cameraY, cameraVelocity } = useCameraY(timing, totalBeats);

  // ── Audio metrics — CSS custom properties cascade to all LayoutRenderer nodes
  const { rms, bassEnergy, midEnergy, highEnergy } = useAudioMetrics(audioSrc);

  return (
    <div
      style={{
        "--audio-rms":  rms,
        "--audio-bass": bassEnergy,
        "--audio-mid":  midEnergy,
        "--audio-high": highEnergy,
        width:      "100%",
        height:     "100%",
        background: "#0B0E14",
        position:   "relative",
        overflow:   "hidden",
        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
      } as React.CSSProperties}
    >
      <Audio src={staticFile(audioSrc)} />

      {/* Matrix data stream — fixed viewport background, behind camera content */}
      <MatrixBackground bassEnergy={bassEnergy} midEnergy={midEnergy} />

      {/* CRT post-processing wraps the camera system */}
      <CRTWrapper cameraVelocity={cameraVelocity} highEnergy={highEnergy}>
        <CameraViewport cameraY={cameraY}>
          <VirtualCanvas totalBeats={totalBeats}>
            {beats.map((beatInfo, index) => {
              const timingKey                      = beatToTimingKey(beatInfo.beat, totalBeats);
              const entry: TimingEntry | undefined = timing[timingKey];
              const beatLayout                     = params[`beat_${beatInfo.beat}`];

              if (!beatLayout) {
                console.warn(`[VideoComposition] No params for beat_${beatInfo.beat}`);
                return null;
              }

              const beatStartFrame = entry ? Math.round(entry.start * FPS) : 0;

              return (
                <BeatZone
                  key={beatInfo.beat}
                  index={index}
                  beatStartFrame={beatStartFrame}
                >
                  <LayoutRenderer node={beatLayout.layout} />
                </BeatZone>
              );
            })}
          </VirtualCanvas>
        </CameraViewport>
      </CRTWrapper>
    </div>
  );
};
