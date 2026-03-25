"""
Beat — Stats Grid

A grid of labeled stat cards. Concept text in TEXT ZONE, cards fill ANIM ZONE.

Each card has:
  top   — label (e.g. "VRAM")   in C_CYAN, FS_DETAIL
  center — value (e.g. "32GB")   in C_WHITE, FS_LABEL, capped to card width

Grid layouts by item count:
  2 items → 2 side-by-side tall panels
  3 items → 3 stacked in a column
  4 items → 2×2 grid  ← most common
  5 items → top row 2, bottom row 3
  6 items → 2×3 grid

Portrait frame: 25.3 units tall, 14.2 units wide (x safe: ±7, y safe: ±12)
ANIM ZONE: y ≤ 2

params (per-beat dict):
  concept_text: str
  grid_items:   list of {"label": str, "value": str}  (2–6 items)
"""


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _layout(n: int):
    """Returns list of (cx, cy) and (card_w, card_h) for n cards."""
    if n == 2:
        positions = [(-3.5, -4.0), (3.5, -4.0)]
        dims = (5.5, 8.5)
    elif n == 3:
        positions = [(0.0, 0.0), (0.0, -5.0), (0.0, -10.0)]
        dims = (8.5, 3.8)
    elif n == 4:
        positions = [(-3.5, -0.5), (3.5, -0.5), (-3.5, -7.5), (3.5, -7.5)]
        dims = (5.5, 5.5)
    elif n == 5:
        positions = [(-3.5, 0.5), (3.5, 0.5), (-5.0, -6.5), (0.0, -6.5), (5.0, -6.5)]
        dims = (5.5, 5.0)
    else:  # 6
        positions = [(-5.0, 0.5), (0.0, 0.5), (5.0, 0.5),
                     (-5.0, -6.5), (0.0, -6.5), (5.0, -6.5)]
        dims = (4.2, 5.0)
    return positions[:n], dims


def generate(params: dict, duration: float) -> str:
    concept = _esc(params.get("concept_text", ""))
    items   = params.get("grid_items", [])[:6]
    if not items:
        items = [{"label": "STAT", "value": "N/A"}]
    n = len(items)

    positions, (card_w, card_h) = _layout(n)
    val_max_w = round(card_w - 0.8, 1)

    # Animation budget
    anim_concept = 0.5
    per_card     = round(min(0.5, (duration - 2.0) / max(n, 1)), 2)
    anim_out     = 0.5
    wait_time    = max(round(duration - anim_concept - n * per_card - anim_out, 2), 0.1)

    lines = []
    lines.append("        # ── BEAT: STATS GRID ─────────────────────────────────────────")

    # Concept text — TEXT ZONE
    lines.append(f'        _sg_concept = Text("{concept}", font_size=FS_CONCEPT, color=C_YELLOW, font="Monospace", width=10.0)')
    lines.append("        _sg_concept.move_to(np.array([0.0, 8.5, 0.0]))")
    lines.append(f"        self.play(FadeIn(_sg_concept), run_time={anim_concept})")

    fadeout = ["_sg_concept"]

    for i, (item, (cx, cy)) in enumerate(zip(items, positions)):
        label = _esc(item.get("label", ""))
        value = _esc(item.get("value", ""))

        y_label = round(cy + card_h / 2 - 0.9, 2)
        y_value = round(cy - 0.2, 2)

        # Card border
        lines.append(f"        _sg_box{i} = Rectangle(width={card_w}, height={card_h}, color=C_CYAN, fill_opacity=0.05)")
        lines.append(f"        _sg_box{i}.move_to(np.array([{cx}, {cy}, 0.0]))")

        # Label (small, near top of card)
        lines.append(f'        _sg_lbl{i} = Text("{label}", font_size=FS_DETAIL, color=C_CYAN, font="Monospace")')
        lines.append(f"        if _sg_lbl{i}.width > {round(card_w - 0.6, 1)}:")
        lines.append(f"            _sg_lbl{i}.scale_to_fit_width({round(card_w - 0.6, 1)})")
        lines.append(f"        _sg_lbl{i}.move_to(np.array([{cx}, {y_label}, 0.0]))")

        # Value (large, center of card)
        lines.append(f'        _sg_val{i} = Text("{value}", font_size=FS_LABEL, color=C_WHITE, font="Monospace")')
        lines.append(f"        if _sg_val{i}.width > {val_max_w}:")
        lines.append(f"            _sg_val{i}.scale_to_fit_width({val_max_w})")
        lines.append(f"        _sg_val{i}.move_to(np.array([{cx}, {y_value}, 0.0]))")

        lines.append(f"        self.play(Create(_sg_box{i}), FadeIn(_sg_lbl{i}), FadeIn(_sg_val{i}), run_time={per_card})")
        fadeout += [f"_sg_box{i}", f"_sg_lbl{i}", f"_sg_val{i}"]

    fadeout_str = ", ".join(f"FadeOut({o})" for o in fadeout)
    lines.append(f"        self.wait({wait_time})")
    lines.append(f"        self.play({fadeout_str}, run_time={anim_out})")

    return "\n".join(lines) + "\n"
