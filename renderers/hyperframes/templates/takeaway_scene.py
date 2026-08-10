from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import (
    beat_meta_html,
    scene_data,
    section_label_html,
)

TEMPLATE_ID = "TakeawayScene"


def build_scene(config: dict, context: dict) -> dict:
    data = scene_data(config)
    html = (
        beat_meta_html(context)
        + '<div class="hf-takeaway">'
        + section_label_html(data.get("section_label", "Takeaway"))
        + '<div class="hf-accent-line"></div>'
        + f'<div class="hf-headline hf-slide-in">{e(data.get("headline", ""))}</div>'
        + (
            f'<div class="hf-cta">{e(data.get("cta", ""))}</div>'
            if data.get("cta")
            else ""
        )
        + "</div>"
    )
    return {
        "template_id": TEMPLATE_ID,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
