from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import (
    beat_meta_html,
    scene_data,
    section_label_html,
)

TEMPLATE_ID = "StatementSlam"


def build_scene(config: dict, context: dict) -> dict:
    data = scene_data(config)
    lines = data.get("lines", [])
    statements = "".join(
        f'<div class="hf-statement hf-slide-in {"hf-pulse" if i == 0 else ""}" '
        f'data-rank="{i}" style="animation-delay: {i * 140}ms;">{e(line)}</div>'
        for i, line in enumerate(lines)
    )
    html = (
        beat_meta_html(context)
        + section_label_html(data.get("section_label", "Insight"))
        + f'<div class="hf-statements">{statements}</div>'
    )
    return {
        "template_id": TEMPLATE_ID,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
