/**
 * VideoComposition.tsx — Motion Design v2 (Phase 2)
 *
 * Replaces the Sequence + BeatRouter model with an infinite-canvas camera system:
 *   CameraViewport  — overflow:hidden viewport, drives spring camera pan
 *     VirtualCanvas — 1080 × (n_beats × 1920) absolute canvas
 *       BeatZone[0] — y=0,    provides beat-local frame context
 *       BeatZone[1] — y=1920, provides beat-local frame context
 *       ...
 *
 * All beats render simultaneously. The camera scrolls to the active beat.
 * Beat-local animations use useBeatFrame() (see BeatZone / BeatFrameContext).
 */

import React from "react";
import { Audio, staticFile } from "remotion";
import type { RemotionProps, TimingEntry } from "./types";
import { LayoutRenderer } from "./LayoutRenderer";
import { CameraViewport, VirtualCanvas, BeatZone } from "./CameraViewport";

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

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "#0B0E14",
        position: "relative",
        overflow: "hidden",
        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
      }}
    >
      <Audio src={staticFile(audioSrc)} />

      <CameraViewport timing={timing} totalBeats={totalBeats}>
        <VirtualCanvas totalBeats={totalBeats}>
          {beats.map((beatInfo, index) => {
            const timingKey                    = beatToTimingKey(beatInfo.beat, totalBeats);
            const entry: TimingEntry | undefined = timing[timingKey];
            const beatLayout                   = params[`beat_${beatInfo.beat}`];

            if (!beatLayout) {
              console.warn(`[VideoComposition] No params for beat_${beatInfo.beat}`);
              return null;
            }

            // beat-local frame 0 = when narration for this beat starts
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
    </div>
  );
};
