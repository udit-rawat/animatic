from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import (
    beat_meta_html,
    scene_data,
    section_label_html,
)

TEMPLATE_ID = "DataGrid"


def build_scene(config: dict, context: dict) -> dict:
    data = scene_data(config)
    cards = []
    highlight_index = data.get("highlight_index")
    for i, metric in enumerate(data.get("metrics", [])):
        cards.append(
            '<article class="hf-card hf-slide-in" '
            f'data-highlight="{"true" if highlight_index == i or metric.get("glow") else "false"}" '
            f'style="animation-delay: {i * 90}ms;">'
            f'<div class="hf-card-label">{e(metric.get("label", ""))}</div>'
            f'<div class="hf-card-value" data-color="{e(metric.get("color", "white"))}">{e(metric.get("value", ""))}</div>'
            + (
                f'<div class="hf-card-caption">{e(data.get("caption", ""))}</div>'
                if i == 0 and data.get("caption")
                else ""
            )
            + "</article>"
        )
    html = (
        beat_meta_html(context)
        + section_label_html(data.get("section_label", "Data Grid"))
        + '<div class="hf-grid">' + "".join(cards) + "</div>"
    )
    return {
        "template_id": TEMPLATE_ID,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
