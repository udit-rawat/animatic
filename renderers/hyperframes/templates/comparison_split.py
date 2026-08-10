from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import (
    beat_meta_html,
    scene_data,
    section_label_html,
)

TEMPLATE_ID = "ComparisonSplit"


def build_scene(config: dict, context: dict) -> dict:
    data = scene_data(config)

    def panel_html(panel: dict, *, highlighted: bool) -> str:
        metrics = "".join(
            '<article class="hf-card hf-slide-in" style="min-height: 110px;">'
            f'<div class="hf-card-label">{e(metric.get("label", ""))}</div>'
            f'<div class="hf-card-value" data-color="{e(metric.get("color", panel.get("color", "white")))}">{e(metric.get("value", ""))}</div>'
            "</article>"
            for metric in panel.get("metrics", [])
        )
        return (
            f'<section class="hf-panel {"hf-pulse" if highlighted else ""}" '
            f'data-highlight="{"true" if highlighted else "false"}">'
            f'<div class="hf-panel-heading" data-color="{e(panel.get("color", "white"))}">{e(panel.get("heading", ""))}</div>'
            f'<div class="hf-grid">{metrics}</div>'
            "</section>"
        )

    html = (
        beat_meta_html(context)
        + section_label_html(data.get("section_label", "Comparison"))
        + '<div class="hf-split">'
        + panel_html(data.get("left", {}), highlighted=False)
        + f'<div class="hf-divider-badge">{e(data.get("divider_label", "vs"))}</div>'
        + panel_html(data.get("right", {}), highlighted=True)
        + "</div>"
    )
    return {
        "template_id": TEMPLATE_ID,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
