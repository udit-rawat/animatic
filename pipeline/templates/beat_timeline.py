"""
Beat — Timeline

A vertical sequence of events. Concept text in TEXT ZONE.
A vertical spine line runs through the ANIM ZONE. Each event has:
  - a dot on the spine
  - year/version label to the LEFT
  - event description to the RIGHT

Portrait frame: 25.3 units tall, 14.2 units wide.
Spine at x=-1.0. Year labels at x=-4.5. Event text at x=2.5 (centered).

params (per-beat dict):
  concept_text:     str
  timeline_events:  list of {"year": str, "label": str}  (3–6 events)
"""


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def generate(params: dict, duration: float) -> str:
    concept = _esc(params.get("concept_text", ""))
    events  = params.get("timeline_events", [])[:6]
    if not events:
        events = [{"year": "?", "label": "Event"}]
    n = len(events)

    # Vertical layout — ANIM ZONE starts at y=2
    y_top = 1.5
    # Cap spacing at 4.5 so few-event timelines don't spread to frame bottom
    max_spacing = 4.5
    y_bot = max(-10.5, y_top - (n - 1) * max_spacing)
    spacing = round((y_top - y_bot) / max(n - 1, 1), 3) if n > 1 else 0
    centers = [round(y_top - i * spacing, 3) for i in range(n)]

    spine_x = -1.0
    year_x  = -4.5
    event_x =  2.5

    y_spine_top = round(y_top + 0.8, 2)
    y_spine_bot = round(y_bot - 0.8, 2)

    anim_concept  = 0.5
    anim_spine    = 0.6
    per_event     = round(min(0.7, (duration - 2.0) / max(n, 1)), 2)
    anim_out      = 0.5
    wait_time     = max(round(duration - anim_concept - anim_spine - n * per_event - anim_out, 2), 0.1)

    lines = []
    lines.append("        # ── BEAT: TIMELINE ────────────────────────────────────────────")

    # Concept text — TEXT ZONE
    lines.append(f'        _tl_concept = Text("{concept}", font_size=FS_CONCEPT, color=C_YELLOW, font="Monospace", width=10.0)')
    lines.append("        _tl_concept.move_to(np.array([0.0, 8.5, 0.0]))")
    lines.append(f"        self.play(FadeIn(_tl_concept), run_time={anim_concept})")

    # Vertical spine
    lines.append(f"        _tl_spine = Line(start=np.array([{spine_x}, {y_spine_top}, 0.0]), end=np.array([{spine_x}, {y_spine_bot}, 0.0]), color=C_CYAN, stroke_width=3)")
    lines.append(f"        self.play(Create(_tl_spine), run_time={anim_spine})")

    fadeout = ["_tl_concept", "_tl_spine"]

    for i, (event, cy) in enumerate(zip(events, centers)):
        year  = _esc(str(event.get("year", "")))
        label = _esc(str(event.get("label", "")))

        # Dot on spine
        lines.append(f"        _tl_dot{i} = Dot(point=np.array([{spine_x}, {cy}, 0.0]), radius=0.18, color=C_GREEN)")

        # Year (left of spine, right-aligned by centering at year_x)
        lines.append(f'        _tl_yr{i} = Text("{year}", font_size=FS_DETAIL, color=C_GREEN, font="Monospace")')
        lines.append(f"        _tl_yr{i}.move_to(np.array([{year_x}, {cy}, 0.0]))")

        # Event label (right of spine, with wrapping)
        lines.append(f'        _tl_ev{i} = Text("{label}", font_size=FS_DETAIL, color=C_WHITE, font="Monospace", width=6.5)')
        lines.append(f"        _tl_ev{i}.move_to(np.array([{event_x}, {cy}, 0.0]))")

        lines.append(f"        self.play(FadeIn(_tl_dot{i}), Write(_tl_yr{i}), FadeIn(_tl_ev{i}), run_time={per_event})")
        fadeout += [f"_tl_dot{i}", f"_tl_yr{i}", f"_tl_ev{i}"]

    fadeout_str = ", ".join(f"FadeOut({o})" for o in fadeout)
    lines.append(f"        self.wait({wait_time})")
    lines.append(f"        self.play({fadeout_str}, run_time={anim_out})")

    return "\n".join(lines) + "\n"
