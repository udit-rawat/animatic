"""
Beat 2 — Pipeline / Mechanism (VERTICAL layout)

Portrait frames are taller than wide — stack steps vertically.
Concept text at top (TEXT ZONE), steps fill the ANIM ZONE below.

width=10.0 on concept text keeps it on 1-2 lines at full FS_CONCEPT size.
Steps use wide boxes (5.0 units) so short labels render at full FS_DETAIL size.
"""


def generate(params: dict, duration: float) -> str:
    concept = params.get("concept_text", "").replace("\\", "\\\\").replace('"', '\\"')
    steps   = [s.replace("\\", "\\\\").replace('"', '\\"') for s in params.get("pipeline_steps", [])]
    steps   = steps[:5] or ["INPUT", "PROCESS", "OUTPUT"]
    n       = len(steps)

    # ANIM ZONE: y = 2.0 down to y = -8.5 (10.5 units)
    v_span  = 10.5
    spacing = round(v_span / n, 3)
    box_h   = round(min(2.4, spacing - 0.8), 2)
    box_w   = 5.0   # wide: at FS_DETAIL=68, 5 units ≈ 7 chars per line
    y_first = 2.0
    centers = [round(y_first - i * spacing, 3) for i in range(n)]

    per_box   = round(min(0.4, (duration - 2.0) / (2 * n)), 2)
    per_arrow = round(per_box * 0.5, 2)

    lines = []
    lines.append("        # ── BEAT 2: PIPELINE (vertical) ─────────────────────────────")
    # Concept text — TEXT ZONE, wide constraint, 1-2 lines at FS_CONCEPT
    lines.append(f'        _b2_concept = Text("{concept}", font_size=FS_CONCEPT, color=C_YELLOW, font="Monospace", width=10.0)')
    lines.append("        _b2_concept.move_to(np.array([0.0, 8.5, 0.0]))")
    lines.append("        self.play(FadeIn(_b2_concept), run_time=0.5)")

    fadeout = ["_b2_concept"]

    for i, (step, cy) in enumerate(zip(steps, centers)):
        lines.append(f'        _b2_box{i} = Rectangle(width={box_w}, height={box_h}, color=C_CYAN)')
        lines.append(f"        _b2_box{i}.move_to(np.array([0.0, {cy}, 0.0]))")
        # No width= on labels — it scales short text up, causing inconsistent sizes.
        # Instead cap at box width only when the label naturally exceeds it.
        lines.append(f'        _b2_lbl{i} = Text("{step}", font_size=FS_DETAIL, color=C_WHITE, font="Monospace")')
        lines.append(f"        if _b2_lbl{i}.width > {round(box_w - 0.4, 1)}:")
        lines.append(f"            _b2_lbl{i}.scale_to_fit_width({round(box_w - 0.4, 1)})")
        lines.append(f"        _b2_lbl{i}.move_to(np.array([0.0, {cy}, 0.0]))")
        lines.append(f"        self.play(Create(_b2_box{i}), Write(_b2_lbl{i}), run_time={per_box})")
        fadeout += [f"_b2_box{i}", f"_b2_lbl{i}"]

        if i < n - 1:
            y_start = round(cy - box_h / 2 - 0.05, 3)
            y_end   = round(centers[i + 1] + box_h / 2 + 0.05, 3)
            lines.append(f"        _b2_arr{i} = Arrow(start=np.array([0.0, {y_start}, 0.0]), end=np.array([0.0, {y_end}, 0.0]), color=C_GREEN, buff=0)")
            lines.append(f"        self.play(GrowArrow(_b2_arr{i}), run_time={per_arrow})")
            fadeout.append(f"_b2_arr{i}")

    total_anim = 0.5 + n * per_box + (n - 1) * per_arrow + 0.5
    wait_time  = max(round(duration - total_anim, 2), 0.1)
    fadeout_str = ", ".join(f"FadeOut({o})" for o in fadeout)

    lines.append(f"        self.wait({wait_time})")
    lines.append(f"        self.play({fadeout_str}, run_time=0.5)")

    return "\n".join(lines) + "\n"
