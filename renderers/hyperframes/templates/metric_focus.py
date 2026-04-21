from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import (
    beat_meta_html,
    chip_row_html,
    scene_data,
    section_label_html,
)

TEMPLATE_ID = "MetricFocus"


def build_scene(config: dict, context: dict) -> dict:
    data = scene_data(config)
    hero = data.get("hero", {})
    html = (
        beat_meta_html(context)
        + section_label_html(data.get("section_label", "Hook"))
        + '<div class="hf-hero hf-breath">'
        + (
            f'<div class="hf-hero-value hf-pulse" data-color="{e(hero.get("color", "cyan"))}" '
            f'data-countup-target="{e(hero.get("value", ""))}">{e(hero.get("value", ""))}</div>'
        )
        + f'<div class="hf-hero-label">{e(hero.get("label", ""))}</div>'
        + "</div>"
        + f'<div class="hf-context hf-slide-in">{e(data.get("context", ""))}</div>'
        + chip_row_html(data.get("chips", []))
    )
    return {
        "template_id": TEMPLATE_ID,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
