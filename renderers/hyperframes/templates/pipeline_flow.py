from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import beat_meta_html, scene_data, section_label_html

TEMPLATE_ID = "PipelineFlow"


def build_scene(config: dict, context: dict) -> dict:
    data = scene_data(config)
    steps = []
    for i, step in enumerate(data.get("steps", []), start=1):
        state = step.get("state", "idle")
        steps.append(
            f'<article class="hf-step hf-slide-in" data-state="{e(state)}" style="animation-delay: {(i - 1) * 100}ms;">'
            f'<div class="hf-step-index">{i}</div>'
            '<div class="hf-step-copy">'
            f'<div class="hf-step-label">{e(step.get("label", ""))}</div>'
            + (
                f'<div class="hf-step-sublabel">{e(step.get("sublabel", ""))}</div>'
                if step.get("sublabel")
                else ""
            )
            + '</div>'
            '</article>'
        )
    bottleneck = data.get("bottleneck_label", "")
    html = (
        beat_meta_html(context)
        + section_label_html(data.get("section_label", "Pipeline"))
        + '<div class="hf-flow">' + "".join(steps) + "</div>"
        + (f'<div class="hf-muted-card">{e(bottleneck)}</div>' if bottleneck else "")
    )
    return {
        "template_id": TEMPLATE_ID,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
