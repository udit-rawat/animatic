from __future__ import annotations

from renderers.hyperframes.helpers.primitives import e
from renderers.hyperframes.templates.base import beat_meta_html, scene_data, section_label_html

TEMPLATE_ID = "BarComparison"


def build_scene(config: dict, context: dict) -> dict:
    data = scene_data(config)
    items = data.get("items", [])

    def numeric(metric: dict) -> float:
        try:
            return float(metric.get("value", 0))
        except (TypeError, ValueError):
            return 0.0

    max_value = max((numeric(item) for item in items), default=1.0) or 1.0
    rows = []
    for i, item in enumerate(items):
        width = max(6, round((numeric(item) / max_value) * 100))
        label = item.get("label", "")
        value_text = f"{item.get('value', '')}{item.get('unit', '')}"
        rows.append(
            '<div class="hf-bar-row hf-slide-in" '
            f'style="animation-delay: {i * 100}ms;">'
            '<div class="hf-bar-topline">'
            f'<div class="hf-bar-label">{e(label)}</div>'
            f'<div class="hf-bar-value">{e(value_text)}</div>'
            '</div>'
            '<div class="hf-bar-track">'
            f'<div class="hf-bar-fill {"hf-pulse" if item.get("highlight") else ""}" style="width: {width}%;"></div>'
            '</div>'
            '</div>'
        )
    html = (
        beat_meta_html(context)
        + section_label_html(data.get("section_label", "Bar Comparison"))
        + '<div class="hf-bar-list">' + "".join(rows) + "</div>"
    )
    return {
        "template_id": TEMPLATE_ID,
        "layout_mode": context["beat"].get("layout_mode", "full_scene"),
        "html": html,
    }
