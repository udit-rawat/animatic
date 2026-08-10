from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import beat_meta_html, section_label_html


def build_custom_scene(scene: dict, context: dict) -> dict:
    assets = scene.get("assets", [])
    assets_html = ""
    if assets:
        assets_html = (
            '<div class="hf-chip-row">'
            + "".join(f'<span class="hf-chip">{e(asset)}</span>' for asset in assets)
            + "</div>"
        )

    entrypoint = scene.get("entrypoint", "")
    brief_ref = scene.get("brief_ref", "")
    html = (
        beat_meta_html(context)
        + '<div class="hf-custom">'
        + section_label_html("Custom Scene")
        + f'<div class="hf-headline hf-slide-in">{e(entrypoint or "Agent-authored bespoke scene")}</div>'
        + f'<div class="hf-context">Brief reference: {e(brief_ref or "inline custom scene")}</div>'
        + assets_html
        + "</div>"
    )
    return {
        "template_id": "custom",
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
