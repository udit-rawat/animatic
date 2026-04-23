"""
Base contract for HyperFrames template scenes.

Every template scene module should expose:
- `TEMPLATE_ID`
- `build_scene(config: dict, context: dict) -> dict`

The return type will later become a renderer-native scene description or an
HTML/CSS/JS asset bundle reference.
"""

from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e


def scene_context(beat: dict, spec: dict) -> dict:
    return {
        "beat": beat,
        "meta": spec.get("meta", {}),
        "topic": spec.get("topic", {}),
        "timing": spec.get("timing", {}),
        "narration": spec.get("narration", {}),
    }


def scene_data(config: dict) -> dict:
    return config.get("data", config)


def beat_meta_html(context: dict) -> str:
    beat = context.get("beat", {})
    return (
        f'<div class="hf-beat-meta">'
        f'{e(beat.get("id", "beat"))} · {e(beat.get("segment_ref", "custom"))}'
        f"</div>"
    )


def section_label_html(label: str) -> str:
    return f'<div class="hf-section-label">{e(label)}</div>'


def chip_row_html(chips: list[str]) -> str:
    if not chips:
        return ""
    return '<div class="hf-chip-row">' + "".join(
        f'<span class="hf-chip">{e(chip)}</span>' for chip in chips
    ) + "</div>"


def placeholder_scene(template_id: str, config: dict, context: dict) -> dict:
    data = scene_data(config)
    body = (
        section_label_html(data.get("section_label", template_id))
        + f'<div class="hf-muted-card">Template not ported yet: {e(template_id)}</div>'
    )
    return {
        "template_id": template_id,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": beat_meta_html(context) + body,
    }
