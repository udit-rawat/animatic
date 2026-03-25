"""
Beat 3 — Before / After contrast  (NO BARS — eliminates overflow bug)

Bars overflowed panels due to GrowFromCenter expanding outside the bounding rect.
Redesigned as a clean two-panel label comparison:
  Left panel  (RED border)  — BEFORE state: big label + detail line
  Right panel (GREEN border) — AFTER state:  big label + detail line

Layout:
  TEXT ZONE  — concept text at y=8.5, width=10.0 (1-2 lines at FS_CONCEPT)
  BUFFER     — empty
  ANIM ZONE  — two tall panels, centered at y=-3.0

Inside each panel (top → bottom):
  Section title  (FS_LABEL,  e.g. "FA2" / "FA3")  — y = panel_top - 1.5
  Detail line    (FS_DETAIL, e.g. "120ms prefill") — y = panel_center - 0.5
"""


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def generate(params: dict, duration: float) -> str:
    concept      = _esc(params.get("concept_text", ""))
    before_label = _esc(params.get("before_label", "BEFORE"))
    after_label  = _esc(params.get("after_label",  "AFTER"))
    before_det   = _esc(params.get("before_detail", ""))
    after_det    = _esc(params.get("after_detail",  ""))

    # Panel geometry — ANIM ZONE
    xL  = -3.0
    xR  =  3.0
    pw  =  5.0   # panel width
    ph  = 11.0   # panel height
    pcy = -3.0   # panel center y  → top: 2.5, bottom: -8.5

    # Content y positions (absolute)
    y_title  = round(pcy + ph / 2 - 1.5, 2)   # just inside top edge
    y_detail = round(pcy - 0.5, 2)             # mid-lower of panel

    # Text widths — tight to fit within panel half-width
    lbl_w = 2.3   # for section title (short label like "FA3")
    det_w = 2.3   # for detail line

    # Animation budget
    anim_concept = 0.5
    anim_panels  = 0.8
    anim_titles  = 0.6
    anim_detail  = 0.6
    anim_out     = 0.5
    total_anim   = anim_concept + anim_panels + anim_titles + anim_detail + anim_out
    wait_time    = max(round(duration - total_anim, 2), 0.1)

    lines = []
    lines.append("        # ── BEAT 3: BEFORE / AFTER ───────────────────────────────────")

    # Concept text — TEXT ZONE, wide width, 1-2 lines
    lines.append(f'        _b3_concept = Text("{concept}", font_size=FS_CONCEPT, color=C_WHITE, font="Monospace", width=10.0)')
    lines.append("        _b3_concept.move_to(np.array([0.0, 8.5, 0.0]))")
    lines.append(f"        self.play(FadeIn(_b3_concept), run_time={anim_concept})")

    # Panels — Create draws the border, fill_opacity=0 keeps interior transparent
    lines.append(f"        _b3_panL = Rectangle(width={pw}, height={ph}, color=C_RED, fill_opacity=0.05)")
    lines.append(f"        _b3_panL.move_to(np.array([{xL}, {pcy}, 0.0]))")
    lines.append(f"        _b3_panR = Rectangle(width={pw}, height={ph}, color=C_GREEN, fill_opacity=0.05)")
    lines.append(f"        _b3_panR.move_to(np.array([{xR}, {pcy}, 0.0]))")
    lines.append(f"        self.play(Create(_b3_panL), Create(_b3_panR), run_time={anim_panels})")

    # Section labels (BEFORE / AFTER names) — bold, near top of panel
    lines.append(f'        _b3_lblL = Text("{before_label}", font_size=FS_LABEL, color=C_RED, font="Monospace", width={lbl_w})')
    lines.append(f"        _b3_lblL.move_to(np.array([{xL}, {y_title}, 0.0]))")
    lines.append(f'        _b3_lblR = Text("{after_label}", font_size=FS_LABEL, color=C_GREEN, font="Monospace", width={lbl_w})')
    lines.append(f"        _b3_lblR.move_to(np.array([{xR}, {y_title}, 0.0]))")
    lines.append(f"        self.play(Write(_b3_lblL), Write(_b3_lblR), run_time={anim_titles})")

    # Detail lines — the key metric / fact
    lines.append(f'        _b3_detL = Text("{before_det}", font_size=FS_DETAIL, color=C_WHITE, font="Monospace", width={det_w})')
    lines.append(f"        _b3_detL.move_to(np.array([{xL}, {y_detail}, 0.0]))")
    lines.append(f'        _b3_detR = Text("{after_det}", font_size=FS_DETAIL, color=C_GREEN, font="Monospace", width={det_w})')
    lines.append(f"        _b3_detR.move_to(np.array([{xR}, {y_detail}, 0.0]))")
    lines.append(f"        self.play(FadeIn(_b3_detL), FadeIn(_b3_detR), run_time={anim_detail})")

    fadeout_objs = ["_b3_concept", "_b3_panL", "_b3_panR", "_b3_lblL", "_b3_lblR", "_b3_detL", "_b3_detR"]
    fadeout_str = ", ".join(f"FadeOut({o})" for o in fadeout_objs)
    lines.append(f"        self.wait({wait_time})")
    lines.append(f"        self.play({fadeout_str}, run_time={anim_out})")

    return "\n".join(lines) + "\n"
