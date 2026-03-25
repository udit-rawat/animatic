"""
Beat 4 — Takeaway

Large, centered, impactful. width=10.0 keeps it on 1-2 lines at FS_TAKEAWAY=160
so it fills the screen rather than wrapping into many small lines.
"""


def generate(params: dict, duration: float) -> str:
    text = params.get("takeaway_text", "").replace("\\", "\\\\").replace('"', '\\"')

    anim_in   = 1.5
    anim_out  = 0.5
    wait_time = max(round(duration - anim_in - anim_out, 2), 0.1)

    lines = []
    lines.append("        # ── BEAT 4: TAKEAWAY ─────────────────────────────────────────")
    # width=10.0: at FS_TAKEAWAY=160 a 10-word takeaway stays on 2 lines max
    lines.append(f'        _b4_text = Text("{text}", font_size=FS_TAKEAWAY, color=C_WHITE, font="Monospace", width=10.0)')
    lines.append("        _b4_text.move_to(np.array([0.0, 0.0, 0.0]))")
    lines.append(f"        self.play(Write(_b4_text), run_time={anim_in})")
    lines.append(f"        self.wait({wait_time})")
    lines.append(f"        self.play(FadeOut(_b4_text), run_time={anim_out})")

    return "\n".join(lines) + "\n"
