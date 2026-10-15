# Working on Animatic with Claude Code

Reels are authored in [Claude Code](https://claude.com/claude-code) sessions: the model writes the
spec and the composition, and the scripts in `scripts/` keep it honest with gates and checks.

## What is checked in

| Path | Purpose |
| --- | --- |
| `.claude/settings.json` | Shared project settings. Registers the PreToolUse hook below. |
| `scripts/hooks/pre_render_gate.py` | Blocks a final render (`render_hyperframes.py`, `hyperframes render`) until `reel_gate.py motion` passes. Draft renders (`-q draft`) and `--dry-run` pass through. |
| `scripts/reel_gate.py` | `topic` (before pitching), `motion` (before rendering), `hook` (on a draft MP4: first-3-seconds checklist), `record` (after posting). |
| `scripts/check_safe_area.py` | Flags pixels outside the spec's `layout.safe_area` on a rendered MP4. |
| `scripts/make_layout.py` | Writes `layout.js` (`window.SAFE`) into a composition from the spec's `layout.safe_area`. |

Personal permissions stay in `.claude/settings.local.json`, which is gitignored.

## Skills

Skills are installed per machine into `.claude/skills/` (gitignored). None are vendored here; each
keeps its own licence upstream.

| Skill | Source | Used for |
| --- | --- | --- |
| `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `gsap` | HyperFrames skills (user-level, `~/.claude/skills`) | Composition rules and seek-safe GSAP |
| `motion-design` | [richtabor/agent-skills](https://github.com/richtabor/agent-skills) | Easing and timing review |
| `motion-director` | [LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill) (MIT) | Choreography and transitions |
| `virality`, `going-viral` | [Ootto-AI/claude-content-skills](https://github.com/Ootto-AI/claude-content-skills) (MIT) | Hook checklist and CTA patterns |

Skills can also be discovered through the Skill Issue MCP catalogue:

```bash
claude mcp add --transport http skill-issue https://skill-issue.in/api/mcp
```

## Session loop

1. `python3 scripts/new_reel.py --title "..."` and fill the spec's `gate` block.
2. `python3 scripts/reel_gate.py topic --spec <spec>`; pitch the topic and a storyboard before any composition code.
3. Write the narration, check every number, then `python3 scripts/generate_tts.py --spec <spec>` (raw must equal synced).
4. `npx hyperframes transcribe narration.wav`, then author `index.html` against the word timings.
5. `npx hyperframes lint .`, snapshot contact sheets, a draft render, and `reel_gate.py hook --video draft.mp4`.
6. `python3 scripts/render_hyperframes.py --spec <spec>`; the hook runs the motion gate first.
