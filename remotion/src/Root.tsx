import React from "react";
import { Composition } from "remotion";
import { VideoComposition } from "./VideoComposition";
import type { RemotionProps } from "./types";

// Default props for Remotion Studio preview (overridden by --props at render time)
const defaultProps: RemotionProps = {
  beats: [
    { beat: 1, template: "hook" },
    { beat: 2, template: "stats_grid" },
    { beat: 3, template: "comparison" },
    { beat: 4, template: "takeaway" },
  ],
  params: {
    beat_1: { template: "hook", hook_stat: "3B", hook_text: "ElevenLabs beaten." },
    beat_2: {
      template: "stats_grid",
      concept_text: "Voxtral TTS: open-weight model",
      grid_items: [
        { label: "Params", value: "> 3B" },
        { label: "RAM",    value: "> 3GB" },
      ],
    },
    beat_3: {
      template: "comparison",
      concept_text: "Faster, better speech synthesis",
      before_label: "Flash v2.5",
      after_label: "Voxtral",
      before_detail: "Slower TTFA",
      after_detail: "90ms TTFA",
    },
    beat_4: {
      template: "takeaway",
      takeaway_text: "Open weights now outperform closed ones. What's your bias?",
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

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoComposition"
      component={VideoComposition}
      durationInFrames={defaultProps.totalFrames}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      calculateMetadata={({ props }) => ({
        durationInFrames: (props as RemotionProps).totalFrames || defaultProps.totalFrames,
      })}
    />
  );
};
