# Design Language Brainstorm — adamax Remotion Templates

You are a motion design expert specialising in short-form vertical video (Instagram Reels, TikTok).
I am building an automated AI news Reel pipeline that renders videos programmatically using Remotion (React + TypeScript).

I need your help to define a **consistent, viral-worthy animation language** for my template system.
The videos are 30–45 seconds, 1080×1920, 30fps, dark background, one narrator voice, AI/tech content.

Below is a full technical dump of my current system — every template, every animation primitive, every color token.
Study it, then answer the questions at the bottom.

---

## CURRENT DESIGN TOKENS

```
Background:  #0A0A0A  (near-pure black)
Font:        Inter / system-ui, sans-serif

Color palette (NodeColor):
  green:   #10B981  (emerald)
  cyan:    #6366F1  (indigo — mislabelled "cyan" in code)
  yellow:  #8B5CF6  (violet — mislabelled "yellow" in code)
  red:     #EF4444
  white:   #F9FAFB
```

**Problem with current palette:** "cyan" is actually indigo (#6366F1) and "yellow" is actually violet (#8B5CF6). The naming is misleading and the colors themselves are very similar to each other. The palette lacks warmth, contrast punch, and a true anchor color.

---

## CURRENT SPRING PRESETS

```typescript
SPRING_CRISP: { damping: 28, stiffness: 220, overshootClamping: true }
// → Clean landing. Used for metric cards, data elements.

SPRING_HERO:  { damping: 28, stiffness: 180, overshootClamping: true }
// → Slightly slower reveal for hero numbers. More gravitas.

SPRING_SNAP:  { damping: 40, stiffness: 300, overshootClamping: true }
// → Fast snap for structural elements.
```

**Problem:** `overshootClamping: true` on all three means ZERO visible overshoot on any element. Everything lands perfectly clean. This is why it feels like PowerPoint — there is no physical weight or bounce anywhere.

---

## CURRENT ANIMATION UTILITIES

```typescript
slideUp(frame, fps, delay, preset)
// → fade in + translateY 16px → 0. Used for cards, list items.

scaleIn(frame, fps, delay, preset)
// → fade in + scale 0.75 → 1.0. Used for hero numbers.

popIn(frame, fps, delay)
// → fade in + scale 0.85 → 1.0. Used for GPU nodes.

staggerDelay(index, total, budgetFrames=24, baseDelay=0)
// → normalizes stagger timing across any array size.
```

**Problem:** Every element uses one of three identical entrance patterns. There is no motion vocabulary beyond "appears from below slightly" and "scales up slightly." No directional intent. No weight difference between a primary stat and a secondary label.

---

## CURRENT TEMPLATES (12 total)

### 1. MetricFocus
**Purpose:** Single dramatic stat reveal — e.g. "90ms TTFA", "3.8× throughput"
**Structure:** SectionLabel → giant hero number → supporting label → context sentence → chip row
**Current animation:**
- Hero number: scaleIn (0.75→1.0, HERO preset, delay 8)
- Context sentence: slideUp (delay 28, CRISP)
- Chips: staggered slideUp (delay 44+)
- Background: static #0A0A0A, no particles, no ambient motion
**After entrance:** Everything freezes completely. Zero motion for remaining 8–15 seconds.

### 2. DataGrid
**Purpose:** 2–4 metric cards in a grid — e.g. model benchmarks, cost comparisons
**Structure:** SectionLabel → N×M grid of cards (label + value + optional sublabel)
**Current animation:**
- Cards: staggered slideUp
- Highlight card: slightly brighter border
**After entrance:** Static.

### 3. TriStat
**Purpose:** Three metrics stacked — e.g. "Params: 3B / RAM: 3GB / License: Open"
**Structure:** Three rows, each with left accent bar + metric label + value
**Current animation:**
- Rows: staggered slideUp with 18-frame stagger
- Primary row: subtle glow treatment
**After entrance:** Static.

### 4. BarComparison
**Purpose:** Horizontal bar chart — e.g. benchmark scores across N models
**Structure:** SectionLabel → N rows (label + bar + value)
**Current animation:**
- Bars: spring scale from 0 to width (staggered)
- Highlight bar: accent glow
**After entrance:** Bars at full width, frozen.

### 5. ComparisonSplit
**Purpose:** Left vs right two-panel layout — e.g. Old model vs New model
**Structure:** Left panel | vertical divider | right panel. Each side has heading + metric cards.
**Current animation:**
- Left panel: slides in from left
- Right panel: slides in from right
- Metric cards: staggered slideUp within each panel
- Divider: fades in
**After entrance:** Static.

### 6. KineticBridge
**Purpose:** Sequential keyword carousel — e.g. "Privacy → Speed → Control"
**Structure:** Each keyword pops in full-screen center, holds ~44 frames, then fades
**Current animation:**
- Each keyword: spring scale + opacity
- One visible at a time, no overlap
**This is the most "video-like" template currently.**

### 7. StatementSlam
**Purpose:** 2–3 punchy statement lines — replaces KineticBridge for longer phrases
**Structure:** Lines spring in sequentially with 20-frame stagger. First line gets accent color.
**Current animation:**
- Lines: spring scale + opacity, 20-frame stagger
- First line: ambient breath pulse (useBreath — only template that uses it)
**After entrance:** Lines 2–3 are frozen. Only line 1 breathes.**

### 8. PipelineFlow
**Purpose:** Step-by-step architecture — e.g. "Input → Tokenize → Embed → Generate → Output"
**Structure:** Nodes + connectors, horizontal or vertical layout
**Current animation:**
- Nodes: staggered popIn
- Connectors: fade in between nodes
- Bottleneck node: red accent
**After entrance:** Static.

### 9. CodeDiff
**Purpose:** Before/after code comparison
**Structure:** Left block (before, dimmed, strikethrough) + right block (after, springs in line by line)
**Current animation:**
- Before block: fades in at 0.52 opacity
- After block: per-line spring entrance with 10-frame stagger per line
**After entrance:** Static.

### 10. TimelineFlow
**Purpose:** Chronological milestones — e.g. model release history
**Structure:** Vertical spine + milestone dots + labels
**Current animation:**
- Dots: staggered slideUp from left (15-frame stagger)
- Highlight dot: accent glow
**After entrance:** Static.

### 11. LeaderboardRank
**Purpose:** Ranked table — e.g. model leaderboard scores
**Structure:** N rows with rank badge + name + score. Rows animate in REVERSE (lower ranks first, winner last).
**Current animation:**
- Rows: staggered slideUp in reverse order
- Highlight row: accent background + glow
**After entrance:** Static.

### 12. TakeawayScene (outro — always the last beat)
**Purpose:** Kinetic CTA — headline word-reveal + CTA chip + progress border
**Structure:** Ambient floating glow dots (background) → frosted glass card (headline word-reveal) → CTA chip
**Current animation:**
- AmbientDots: 3 deterministic blurred glow orbs drifting continuously ✓
- Card: spring slide-up entrance, then continuous breath (scale ±1.1%) ✓
- Headline: per-word spring reveal (translateY 120→0, stagger 3 frames/word) ✓
- CTA chip: pop-in after headline completes ✓
- ProgressBorder: fills from 0→100% over beat duration ✓
**This is the ONLY template with continuous post-entrance motion.**

---

## SHARED HOOKS (exist but mostly unused)

```typescript
useBreath(frame, fps)
// → returns scale: 1 ± 0.012, opacityShift: ± 0.04  (0.25 Hz sine wave)
// → ONLY used in: StatementSlam (line 1 only), TakeawayScene (card)
// → Should be used in: every hero element in every template

useAudioMetrics()
// → returns rms, bassEnergy, midEnergy, highEnergy from FFT analysis
// → COMPLETELY UNUSED in any template
// → Could drive: glow intensity, scale pulse, particle speed
```

---

## THE CORE PROBLEM

Every template has two states:
1. **Animating in** (first ~1 second): looks alive
2. **After entrance** (remaining 5–15 seconds): completely frozen, static, dead

The viewer's eye has nothing to track after the entrance completes. This is why it feels like PowerPoint.

TakeawayScene is the exception — it has continuous motion because it was designed deliberately with AmbientDots + breath + ProgressBorder. Every other template needs the same deliberate "life layer."

---

## THE GOAL

Define a **consistent animation language** — a set of rules and primitives that apply across ALL templates — so that:

1. Every video feels like it belongs to the same brand
2. Every element that is "alive" (on screen) is always *moving*, even subtly
3. Hook and TakeawayScene have heavier, more physical motion than concept beats
4. The visual language is recognizable and ownable — a signature, not generic

---

## QUESTIONS FOR YOU

Please answer each one specifically:

**1. COLOR PALETTE**
The current palette (#10B981 green, #6366F1 "cyan", #8B5CF6 "yellow", #EF4444 red) on #0A0A0A background — what is wrong with it for Instagram Reels? Propose a revised 4-color palette with hex codes that has more contrast, punch, and visual hierarchy. Which color should be the primary accent (most used), which should be the signal color (used only for the most important element per screen)?

**2. MOTION TIERS**
Define 3 motion tiers for this system:
- **HEAVY** (hook + takeaway only): what spring config (damping, stiffness, mass, overshootClamping)? What entrance direction/distance? How much visible overshoot?
- **MEDIUM** (concept beats — data, comparisons): what config?
- **SOFT** (secondary text, labels, chips): what config or simple interpolation?

**3. LIFE LAYER (post-entrance continuous motion)**
For each of these 5 element types, define exactly what continuous motion it should have after landing:
- Hero number (e.g. "400M", "90ms")
- Metric card (label + value in a grid)
- Bar in BarComparison (after it reaches full width)
- CTA chip / badge
- Background (what replaces static #0A0A0A)

**4. PARTICLE FIELD**
Should there be a shared particle background across all templates? If yes: how many particles, what size, what opacity, what speed (px/frame), what shape (dot/line/spark)? Or is there a better background motion idea?

**5. TRANSITION BETWEEN BEATS**
Currently: the camera springs between beats on the infinite canvas (VirtualCanvas). The transition is a camera pan. What should happen visually AT the moment of transition to make it feel intentional and energetic rather than just a camera move?

**6. HOOK SECTION (custom per video)**
The hook is generated as a custom component every time. For an AI tech Reel, what makes a 5–7 second hook feel genuinely cinematic vs PowerPoint? Give me 3 specific visual concepts (not generic advice) that work for tech/AI content — e.g. "SVG path of logo draws itself over 40 frames then explodes into particles."

**7. TEMPLATE-SPECIFIC UPGRADES**
For each of these 4 templates, give ONE specific upgrade that adds continuous motion without rebuilding the template:
- MetricFocus (hero number sitting static after entrance)
- BarComparison (bars frozen at full width)
- ComparisonSplit (two panels frozen after sliding in)
- KineticBridge (already most animated — what would make it better?)

**8. SIGNATURE ELEMENT**
What is ONE visual element — something that appears in every single beat of every video — that becomes the brand signature? (TakeawayScene has the ProgressBorder — something like that but for the whole video.) Give a specific implementation idea.
