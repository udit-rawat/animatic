"""
Beat 1 — Hook

Layout:
  y = 6.0  — stat (FS_STAT=300, no width cap — renders at full size)
  y =-1.0  — hook phrase (FS_HOOK=120, width=10.0 — near full frame width)

width=10.0 (vs old 5.5) keeps text on 1-2 lines instead of 4-5 lines,
making each line render visibly large instead of wrapping into tiny rows.

Animation: GrowFromCenter for stat (smooth, no stroke jitter), FadeIn for hook.
"""


def generate(params: dict, duration: float) -> str:
    stat = params.get("hook_stat", "").replace("\\", "\\\\").replace('"', '\\"')
    text = params.get("hook_text", "").replace("\\", "\\\\").replace('"', '\\"')

    anim_stat = 1.0   # GrowFromCenter(stat)
    anim_hook = 0.8   # FadeIn(hook)
    anim_out  = 0.5
    wait_time = max(round(duration - anim_stat - anim_hook - anim_out, 2), 0.1)

    return (
        "        # ── BEAT 1: HOOK ─────────────────────────────────────────────\n"
        f'        _b1_stat = Text("{stat}", font_size=FS_STAT, color=C_GREEN, font="Monospace")\n'
        "        _b1_stat.move_to(np.array([0.0, 6.0, 0.0]))\n"
        # Hook — wide constraint so text stays on 1-2 lines at full FS_HOOK size
        f'        _b1_hook = Text("{text}", font_size=FS_HOOK, color=C_WHITE, font="Monospace", width=10.0)\n'
        "        _b1_hook.move_to(np.array([0.0, -1.0, 0.0]))\n"
        f"        self.play(GrowFromCenter(_b1_stat), run_time={anim_stat})\n"
        f"        self.play(FadeIn(_b1_hook), run_time={anim_hook})\n"
        f"        self.wait({wait_time})\n"
        f"        self.play(FadeOut(_b1_stat), FadeOut(_b1_hook), run_time={anim_out})\n"
    )
