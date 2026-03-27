/**
 * VideoComposition.tsx — Motion Design v2 (Tier 1 refactor: devtool aesthetic)
 *
 * Full component tree:
 *   <VideoComposition>
 *     ├── <Audio />
 *     └── <CameraViewport cameraY>
 *         └── <VirtualCanvas totalBeats>
 *             └── <BeatZone index beatStartFrame> × n
 *                 └── <LayoutRenderer node />
 *
 * CRTWrapper and MatrixBackground removed — replaced by clean #0A0A0A canvas.
 * Audio metrics no longer injected as CSS custom properties on visible elements.
 */

import React from "react";
import { Audio, staticFile, useVideoConfig } from "remotion";
import type { RemotionProps, TimingEntry } from "./types";
import { LayoutRenderer }  from "./LayoutRenderer";
import { CameraViewport, VirtualCanvas, BeatZone } from "./CameraViewport";
import { useCameraY }      from "./hooks/useCameraY";
import { SceneContext }    from "./context/SceneContext";

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
  cues = {},
}) => {
  const totalBeats      = beats.length;
  const { fps }         = useVideoConfig();
  const { cameraY }     = useCameraY(timing, totalBeats);

  return (
    <SceneContext.Provider value={{ cues, fps }}>
    <div
      style={{
        width:      "100%",
        height:     "100%",
        background: "#0A0A0A",
        position:   "relative",
        overflow:   "hidden",
        fontFamily: "'Inter', 'system-ui', sans-serif",
      }}
    >
      <Audio src={staticFile(audioSrc)} />

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
    </div>
    </SceneContext.Provider>
  );
};
