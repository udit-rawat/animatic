"""HyperFrames template scene modules."""

from renderers.hyperframes.templates.bar_comparison import (
    TEMPLATE_ID as BAR_COMPARISON_ID,
    build_scene as build_bar_comparison,
)
from renderers.hyperframes.templates.comparison_split import (
    TEMPLATE_ID as COMPARISON_SPLIT_ID,
    build_scene as build_comparison_split,
)
from renderers.hyperframes.templates.data_grid import (
    TEMPLATE_ID as DATA_GRID_ID,
    build_scene as build_data_grid,
)
from renderers.hyperframes.templates.metric_focus import (
    TEMPLATE_ID as METRIC_FOCUS_ID,
    build_scene as build_metric_focus,
)
from renderers.hyperframes.templates.pipeline_flow import (
    TEMPLATE_ID as PIPELINE_FLOW_ID,
    build_scene as build_pipeline_flow,
)
from renderers.hyperframes.templates.statement_slam import (
    TEMPLATE_ID as STATEMENT_SLAM_ID,
    build_scene as build_statement_slam,
)
from renderers.hyperframes.templates.takeaway_scene import (
    TEMPLATE_ID as TAKEAWAY_SCENE_ID,
    build_scene as build_takeaway_scene,
)

TEMPLATE_REGISTRY = {
    BAR_COMPARISON_ID: build_bar_comparison,
    COMPARISON_SPLIT_ID: build_comparison_split,
    DATA_GRID_ID: build_data_grid,
    METRIC_FOCUS_ID: build_metric_focus,
    PIPELINE_FLOW_ID: build_pipeline_flow,
    STATEMENT_SLAM_ID: build_statement_slam,
    TAKEAWAY_SCENE_ID: build_takeaway_scene,
}
