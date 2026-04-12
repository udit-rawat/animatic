/**
 * SceneRouter — semantic layout dispatcher.
 *
 * Sits above LayoutRenderer in the component tree. Receives a typed SceneData
 * discriminated union and routes to the correct abstract layout component.
 *
 * TakeawayScene is NOT handled here — it requires durationFrames from VideoComposition
 * and is rendered directly in the beat loop for that beat.
 */

import React from "react";
import type { SceneData } from "./types";
import { ComparisonSplit } from "./layouts/ComparisonSplit";
import { MetricFocus }     from "./layouts/MetricFocus";
import { PipelineFlow }    from "./layouts/PipelineFlow";
import { DataGrid }        from "./layouts/DataGrid";
import { KineticBridge }   from "./layouts/KineticBridge";
import { StatementSlam }    from "./layouts/StatementSlam";
import { TimelineFlow }     from "./layouts/TimelineFlow";
import { TriStat }          from "./layouts/TriStat";
import { LeaderboardRank }  from "./layouts/LeaderboardRank";
import { BarComparison }    from "./layouts/BarComparison";
import { CodeDiff }         from "./layouts/CodeDiff";
import { TerminalScene }    from "./layouts/TerminalScene";

export const SceneRouter: React.FC<{ data: SceneData }> = ({ data }) => {
  switch (data.layout) {
    case "ComparisonSplit":  return <ComparisonSplit data={data} />;
    case "MetricFocus":      return <MetricFocus data={data} />;
    case "PipelineFlow":     return <PipelineFlow data={data} />;
    case "DataGrid":         return <DataGrid data={data} />;
    case "KineticBridge":    return <KineticBridge data={data} />;
    case "StatementSlam":    return <StatementSlam data={data} />;
    case "TimelineFlow":     return <TimelineFlow data={data} />;
    case "TriStat":          return <TriStat data={data} />;
    case "LeaderboardRank":  return <LeaderboardRank data={data} />;
    case "BarComparison":    return <BarComparison data={data} />;
    case "CodeDiff":         return <CodeDiff data={data} />;
    case "TerminalScene":    return <TerminalScene data={data} />;
    case "TakeawayScene":    return null; // handled by VideoComposition with durationFrames
    default:                 return null;
  }
};
