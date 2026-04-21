"""
Composition builder skeleton for HyperFrames.

Future responsibility:
- transform `video_spec.json` into a renderer-native composition
- dispatch beats by `scene.kind`
- apply `layout_mode`
- resolve template scene modules vs custom scene modules vs external clip slots
"""

from __future__ import annotations

from pathlib import Path

from renderers.hyperframes.custom_scene import build_custom_scene
from renderers.hyperframes.external_clip_scene import build_external_clip_scene
from renderers.hyperframes.helpers.primitives import e, runtime_css, runtime_js
from renderers.hyperframes.templates import TEMPLATE_REGISTRY
from renderers.hyperframes.templates.base import placeholder_scene, scene_context


def build_composition(spec: dict) -> dict:
    """Build a HyperFrames-compatible HTML composition from `video_spec.json`."""
    scene_fragments: list[str] = []
    scene_models: list[dict] = []
    meta = spec.get("meta", {})
    fps = int(meta.get("fps", 30) or 30)
    width = int(meta.get("width", 1080) or 1080)
    height = int(meta.get("height", 1920) or 1920)
    total_duration = float(spec.get("timing", {}).get("total_duration_seconds", 0) or 0)
    topic_slug = meta.get("topic_slug", "adamax-video") or "adamax-video"
    composition_id = f"adamax-{topic_slug}"
    audio_src = Path(spec.get("assets", {}).get("audio_src", "")).name

    for beat in spec.get("beats", []):
        context = scene_context(beat, spec)
        scene = beat.get("scene", {})
        kind = scene.get("kind")
        start_seconds = round(float(beat.get("start_frame", 0) or 0) / fps, 3)
        duration_seconds = round(float(beat.get("duration_frames", 1) or 1) / fps, 3)
        track_index = max(0, int(beat.get("index", 1) or 1) - 1)

        if kind == "template":
            template_id = scene.get("template_id")
            builder = TEMPLATE_REGISTRY.get(template_id)
            if builder:
                built = builder(scene.get("config", {}), context)
            else:
                built = placeholder_scene(template_id or "UnknownTemplate", scene.get("config", {}), context)
        elif kind == "custom":
            built = build_custom_scene(scene, context)
        elif kind == "external_clip":
            built = build_external_clip_scene(scene, context)
        else:
            built = {
                "template_id": scene.get("kind", "custom"),
                "layout_mode": beat.get("layout_mode", "full_scene"),
                "html": (
                    f'<div class="hf-beat-meta">{beat.get("id", "beat")} · {kind or "custom"}</div>'
                    '<div class="hf-muted-card">Custom or external clip scene not implemented in Phase 3.</div>'
                ),
            }

        scene_models.append(built)
        scene_fragments.append(
            f'<section id="{e(beat.get("id", "beat"))}" class="hf-beat clip" '
            f'data-layout-mode="{e(built["layout_mode"])}" '
            f'data-template-id="{e(built["template_id"])}" '
            f'data-start="{start_seconds}" '
            f'data-duration="{duration_seconds}" '
            f'data-track-index="{track_index}" '
            f'style="z-index: {track_index + 1};">{built["html"]}</section>'
        )

    title = spec.get("topic", {}).get("title", "AdaMax Video")
    audio_fragment = ""
    if audio_src:
        audio_fragment = (
            f'<audio id="narration-audio" class="clip" '
            f'data-start="0" '
            f'data-duration="{total_duration}" '
            f'data-track-index="{len(spec.get("beats", [])) + 2}" '
            f'src="{e(audio_src)}" preload="auto"></audio>'
        )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{runtime_css()}</style>
</head>
<body>
  <script>
    window.__timelines = window.__timelines || {{}};
    window.__playerReady = true;

    (() => {{
      const compositionId = {composition_id!r};
      const duration = {total_duration};
      let currentTime = 0;
      window.__timelines[compositionId] = {{
        pause() {{ return this; }},
        play() {{ return this; }},
        seek(time) {{ currentTime = Math.max(0, Math.min(duration, Number(time) || 0)); return this; }},
        totalTime(time) {{
          if (typeof time === 'number') return this.seek(time);
          return currentTime;
        }},
        time() {{ return currentTime; }},
        duration() {{ return duration; }},
      }};
    }})();
  </script>
  <div
    id="{e(composition_id)}"
    class="hf-root"
    data-composition-id="{e(composition_id)}"
    data-start="0"
    data-duration="{total_duration}"
    data-width="{width}"
    data-height="{height}"
  >
    <main class="hf-stage">
      {''.join(scene_fragments)}
      {audio_fragment}
    </main>
  </div>
  <script>{runtime_js()}</script>
</body>
</html>
"""
    return {
        "version": spec.get("version"),
        "meta": spec.get("meta", {}),
        "beats": spec.get("beats", []),
        "scenes": scene_models,
        "composition_id": composition_id,
        "html": html,
    }
