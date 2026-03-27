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
import { Audio, interpolate, staticFile, useVideoConfig } from "remotion";
import type { AnimateIn, RemotionProps, TimingEntry } from "./types";
import { LayoutRenderer }  from "./LayoutRenderer";
import { CameraViewport, VirtualCanvas, BeatZone } from "./CameraViewport";
import { useCameraY }      from "./hooks/useCameraY";
import { useBeatFrame }    from "./hooks/useBeatFrame";
import { SceneContext }    from "./context/SceneContext";
import { slideUp, scaleIn } from "./utils/springIn";

const FPS = 30;

/**
 * BeatAnimateIn — applies beat-level entrance animation based on animate_in.
 *
 * Must be rendered INSIDE BeatZone so useBeatFrame() sees beat-local frames.
 * Beat-local frame 0 = camera arrives at this beat (beatStartFrame).
 *
 * animate_in mapping:
 *   spring_in / slide_up → slideUp (HERO preset — slower, more gravitas)
 *   spring_scale         → scaleIn (HERO preset)
 *   fade                 → linear opacity 0→1 over 20 frames
 *   typewriter / none    → no wrapper transform; primitives own their animation
 */
const BeatAnimateIn: React.FC<{
  animateIn: AnimateIn;
  fps: number;
  children: React.ReactNode;
}> = ({ animateIn, fps, children }) => {
  const frame = useBeatFrame();

  let wrapStyle: React.CSSProperties = { width: "100%", height: "100%" };

  if (animateIn === "spring_in" || animateIn === "slide_up") {
    const { opacity, translateY } = slideUp(frame, fps, 0, "hero");
    wrapStyle = { ...wrapStyle, opacity, transform: `translateY(${translateY}px)` };
  } else if (animateIn === "spring_scale") {
    const { opacity, scale } = scaleIn(frame, fps, 0, "hero");
    wrapStyle = { ...wrapStyle, opacity, transform: `scale(${scale})` };
  } else if (animateIn === "fade") {
    const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
    wrapStyle = { ...wrapStyle, opacity };
  }

  return <div style={wrapStyle}>{children}</div>;
};

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
                <BeatAnimateIn animateIn={beatLayout.animate_in} fps={fps}>
                  <LayoutRenderer node={beatLayout.layout} />
                </BeatAnimateIn>
              </BeatZone>
            );
          })}
        </VirtualCanvas>
      </CameraViewport>
    </div>
    </SceneContext.Provider>
  );
};
