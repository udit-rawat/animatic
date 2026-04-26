# Animation Playbook

This file captures the visual system, motion rules, and practical decisions used for the final `Memory Wall` reel so future animations can reuse the same language.

## Core Direction

The winning direction is:

- clinical light-mode product demo
- object-based explanation, not text-first explainer slides
- soft physical depth
- restrained transitions
- premium system-tool feel

The reference feel is closer to:

- Apple
- Stripe
- Linear

It is explicitly **not**:

- cyberpunk
- neon AI art
- black-background motion graphics
- flashy social-edit gimmicks

## Color Theme

Use this exact palette as the base:

- `#F7F7F4` — canvas background
- `#FFFFFF` — cards and surfaces
- `#111111` — primary text
- `#5F6B76` — secondary text
- `#E7EBF0` — borders and dividers
- `#2563FF` — structure, graph lines, active emphasis
- `#E5484D` — incident / severity / risk
- `#16A34A` — success / validation / correct path
- `#F3EEE7` — warm depth tint

## Typography

- Headline / display: `SF Pro Display`
- Body / UI: `SF Pro Text`
- Code / technical labels: `SF Mono`

Rules:

- use near-black, not pure decorative contrast tricks
- keep UI text readable at reel scale
- use monospace only for code, terminal, and precise metadata

## What Worked

These decisions should be reused:

- white/off-white canvas with faint grid
- white floating cards with soft shadows
- tilted 3D cards with mild perspective
- cobalt graph lines on a quiet background
- smooth camera/world drift, not aggressive movement
- bottom-centered `@ada.max24` chip in the safe zone
- continuous scene language across the whole reel

## Motion Grammar

Each narration block should follow this structure:

1. entry
2. main reveal
3. support motion
4. settle

This was the key fix. If animation resolves too early, narration feels like it is talking over a dead frame.

### Entry

- fade in on white background
- slight push, lift, or object rise
- no hard cuts unless the concept truly resets

### Main Reveal

- one primary action only
- examples:
  - cards separate
  - graph lines draw
  - chips appear
  - comparison panels enter
  - terminal types

### Support Motion

- add one secondary beat after the main reveal
- examples:
  - slight world drift
  - path emphasis
  - ripple decay
  - panel settle
  - quiet follow-through motion

### Settle

- let the viewer read
- text-bearing objects should not keep floating aggressively
- the scene must remain alive, but calm

## Transition Rules

Use:

- fade into the white canvas
- soft overlap with timing delay
- scene handoff with breathing room

Do not use:

- blur-heavy carryover as the main transition
- blink cuts
- wipes
- glitch transitions
- flashy FX transitions

Best rule:

- outgoing scene fades down
- incoming scene fades up
- white background remains the continuity layer

## Card Style

Cards should feel like floating product objects, not flat rectangles.

Use:

- soft shadows
- rounded corners
- slight `rotateX / rotateY / rotate`
- mild perspective
- small per-card variation in angle

Do not:

- flatten all cards into the same plane
- use identical tilt everywhere
- over-rotate into dramatic 3D

## Graph / Relationship Scene Rules

The graph scenes worked best when:

- cards remained the hero
- lines stayed clean and saturated
- metadata was limited
- motion stayed readable

Rules:

- graph lines are structural, not decorative
- cards must remain readable before drifting
- metadata chips should be few and meaningful
- diagnosis scene should not carry too much graph noise behind it

## Metadata / Chip Rules

Use metadata chips sparingly.

Good chip content:

- `03:00 AM`
- `Production`
- `Retry Loop`
- `correct path`

Chip rules:

- slightly larger than default UI pills
- strong enough to read on mobile
- color-coded only when it serves meaning

Blue:

- structural / neutral active state

Red:

- incident / severity / production risk

Green:

- validation / resolution / successful path

## Opening Scene Rule

The opening should show failure through useful but insufficient outputs.

Do:

- show retrieval-like results
- make them legible and relevant

Do not:

- use generic placeholders like `[object Object]`

The right feeling is:

- “the system found something”
- “but it still does not understand enough”

## Readability Rules

- no floating keyword overlays as a default pattern
- avoid extra labels unless they earn their place
- keep important content inside Reels-safe zones
- text should settle before the next reveal competes with it
- one frame should never ask the viewer to parse too many moving words

## Reels Safe Zone Rules

Always keep important information away from:

- the right-side action rail
- the bottom caption / account area

Working rule for this project:

- central content column
- extra clearance on the right
- branding handle centered near the bottom safe area

## Narration Sync Rules

The narration worked best when:

- the reel was allowed to be longer
- the speech was not force-stretched upward
- only overlong segments were compressed
- animation duration covered the full spoken idea

Never optimize for short runtime at the cost of cadence.

Preferred rule:

- quality first
- natural spoken rhythm first
- then fit motion around it

## Render Rules

For final export:

- use the approved narration unchanged unless script quality is the issue
- render final delivery at high quality
- use `60 fps` only for the final premium pass if motion benefits from it

For iteration:

- `30 fps` is enough
- save `60 fps` for the final render

## What Not To Do

Avoid all of this unless a future concept explicitly needs it:

- neon cyan / purple glow language
- black sci-fi backgrounds
- constant ambient floating on text-heavy elements
- dense keyword overlays
- flashy transitions
- infographic slide energy
- excessive blur transitions
- abstract AI art aesthetics

## Reusable Formula For Upcoming Reels

For future technical explainers, start from this template:

1. open with a concrete system failure
2. show why retrieval / current logic is insufficient
3. turn isolated objects into a structured relationship view
4. reveal context one layer at a time
5. diagnose the meaningful case
6. resolve into a product / terminal / system conclusion

That is the animation system that worked.
