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

export const SceneRouter: React.FC<{ data: SceneData }> = ({ data }) => {
  switch (data.layout) {
    case "ComparisonSplit": return <ComparisonSplit data={data} />;
    case "MetricFocus":     return <MetricFocus data={data} />;
    case "PipelineFlow":    return <PipelineFlow data={data} />;
    case "DataGrid":        return <DataGrid data={data} />;
    case "TakeawayScene":   return null; // handled by VideoComposition directly
    default:                return null;
  }
};
