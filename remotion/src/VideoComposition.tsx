import React from "react";
import { Audio, Sequence, staticFile } from "remotion";
import type { BeatInfo, BeatParams, RemotionProps, TimingEntry } from "./types";
import { Beat1Hook }        from "./beats/Beat1Hook";
import { Beat2Pipeline }    from "./beats/Beat2Pipeline";
import { Beat3BeforeAfter } from "./beats/Beat3BeforeAfter";
import { Beat4Takeaway }    from "./beats/Beat4Takeaway";
import { BeatStatsGrid }    from "./beats/BeatStatsGrid";
import { BeatTimeline }     from "./beats/BeatTimeline";

const FPS = 30;

/**
 * Maps beat number to the narration_timing.json key.
 * Beat 1 → "hook", last beat → "takeaway_cta", middle beats → "concept_1", "concept_2", ...
 */
function beatToTimingKey(beatNum: number, totalBeats: number): string {
  if (beatNum === 1) return "hook";
  if (beatNum === totalBeats) return "takeaway_cta";
  return `concept_${beatNum - 1}`;  // beat 2 → concept_1, beat 3 → concept_2, ...
}

function toFrames(seconds: number): number {
  return Math.round(seconds * FPS);
}

interface BeatRouterProps {
  beat: BeatInfo;
  params: BeatParams;
}

const BeatRouter: React.FC<BeatRouterProps> = ({ beat, params }) => {
  switch (beat.template) {
    case "hook":
      return <Beat1Hook params={params as import("./types").HookParams} />;
    case "pipeline":
      return <Beat2Pipeline params={params as import("./types").PipelineParams} />;
    case "comparison":
      return <Beat3BeforeAfter params={params as import("./types").ComparisonParams} />;
    case "stats_grid":
      return <BeatStatsGrid params={params as import("./types").StatsGridParams} />;
    case "timeline":
      return <BeatTimeline params={params as import("./types").TimelineParams} />;
    case "takeaway":
      return <Beat4Takeaway params={params as import("./types").TakeawayParams} />;
    default:
      return null;
  }
};

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
      {/* TTS narration audio — baked into the render by Remotion's FFmpeg */}
      <Audio src={staticFile(audioSrc)} />

      {/* Beat sequences — each renders at the exact TTS-derived timestamp */}
      {beats.map((beat) => {
        const timingKey = beatToTimingKey(beat.beat, totalBeats);
        const entry: TimingEntry | undefined = timing[timingKey];

        if (!entry) {
          console.warn(`[VideoComposition] No timing entry for key "${timingKey}" (beat ${beat.beat})`);
          return null;
        }

        const from             = toFrames(entry.start);
        const durationInFrames = toFrames(entry.duration);
        const beatParams       = params[`beat_${beat.beat}`];

        if (!beatParams) {
          console.warn(`[VideoComposition] No params for beat_${beat.beat}`);
          return null;
        }

        return (
          <Sequence key={beat.beat} from={from} durationInFrames={durationInFrames}>
            <BeatRouter beat={beat} params={beatParams} />
          </Sequence>
        );
      })}
    </div>
  );
};
