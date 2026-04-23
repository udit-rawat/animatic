from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import beat_meta_html, section_label_html


def build_external_clip_scene(scene: dict, context: dict) -> dict:
    overlay = scene.get("overlay_config", {})
    note = overlay.get("note") or "External generated clip slot"
    html = (
        beat_meta_html(context)
        + '<div class="hf-external">'
        + section_label_html("External Clip")
        + f'<div class="hf-headline hf-slide-in">{e(scene.get("slot_id", "clip_slot"))}</div>'
        + f'<div class="hf-context">Generator: {e(scene.get("generator", "other"))}</div>'
        + f'<div class="hf-muted-card">Prompt ref: {e(scene.get("prompt_ref", ""))}<br>{e(note)}</div>'
        + "</div>"
    )
    return {
        "template_id": "external_clip",
        "layout_mode": context["beat"].get("layout_mode", "caption_overlay"),
        "html": html,
    }
