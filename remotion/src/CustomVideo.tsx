/**
 * CustomVideo.tsx — CheetahClaws Local Claude Code Agent
 * 614 frames · 30fps · 20.5s
 *
 * beat_1  frames   0– 82   Hook: hookLine1/hookLine2 frame 0, hookSub @30f, chips @55/70/85f
 * beat_2  frames  82–235   Model swap cards stagger @0/45/90f, pulse @120f
 * beat_3  frames 235–455   Slam lines @0/60/120f
 * beat_4  frames 455–614   Option 3 hard cut — ctaLine1/2/3
 *
 * All text is schema-editable in Remotion Studio left panel.
 */

import React from "react";
import { z } from "zod";
import {
  Sequence, useCurrentFrame, useVideoConfig,
  Audio, staticFile, spring, interpolate,
} from "remotion";
import {
  usePulseAt, useSlideIn,
  COLOR, FONT, HERO_NUMBER, BROADCAST_TEXT,
  SectionLabelRow, ParticleBackground, TelemetryFrame, useBreath,
} from "./layouts/_shared";
import { SPRING_HEAVY, SPRING_MEDIUM } from "./utils/springIn";

// ── Schema — every visible string/color editable in Studio ────────────────────

export const customVideoSchema = z.object({
  // Beat 1 — Hook
  beat1Section: z.string().default("LOCAL AI AGENCY"),
  hookLine1:    z.string().default("ZERO"),
  hookLine2:    z.string().default("CLOUD."),
  hookSub:      z.string().default("Claude Code. One command."),
  chip1:        z.string().default("14B params"),
  chip2:        z.string().default("Ollama"),
  chip3:        z.string().default("RTX 3090"),

  // Beat 2 — Model cards
  beat2Section:   z.string().default("SWAP 3 MODELS"),
  card1Value:     z.string().default("14B"),
  card1Label:     z.string().default("Model"),
  card1Sublabel:  z.string().default("Qwen / Llama / Mistral"),
  card2Value:     z.string().default("Ollama"),
  card2Label:     z.string().default("Endpoint"),
  card2Sublabel:  z.string().default("swap without code change"),
  card3Value:     z.string().default("RTX 3090"),
  card3Label:     z.string().default("Hardware"),
  card3Sublabel:  z.string().default("single GPU, full loop"),

  // Beat 3 — Slam lines
  beat3Section: z.string().default("AUTONOMOUS LOOP"),
  slamLine1:    z.string().default("1 command. Loops."),
  slamLine2:    z.string().default("Brainstorm → ship code."),
  slamLine3:    z.string().default("Saves 6 hours. Per feature."),

  // Beat 4 — CTA
  ctaLine1: z.string().default("14B."),
  ctaLine2: z.string().default("One 3090."),
  ctaLine3: z.string().default("Full agent loop."),

  // Global accent color
  accentColor: z.enum(["cyan", "green", "yellow"]).default("green"),
});

export type CustomVideoProps = z.infer<typeof customVideoSchema>;

// ── Config ─────────────────────────────────────────────────────────────────────

export const CustomVideoConfig = {
  durationInFrames: 614,
  fps:    30,
  width:  1080,
  height: 1920,
  defaultProps: {
    beat1Section: "LOCAL AI AGENCY",
    hookLine1:    "ZERO",
    hookLine2:    "CLOUD.",
    hookSub:      "Claude Code. One command.",
    chip1:        "14B params",
    chip2:        "Ollama",
    chip3:        "RTX 3090",
    beat2Section:  "SWAP 3 MODELS",
    card1Value:    "14B",
    card1Label:    "Model",
    card1Sublabel: "Qwen / Llama / Mistral",
    card2Value:    "Ollama",
    card2Label:    "Endpoint",
    card2Sublabel: "swap without code change",
    card3Value:    "RTX 3090",
    card3Label:    "Hardware",
    card3Sublabel: "single GPU, full loop",
    beat3Section: "AUTONOMOUS LOOP",
    slamLine1:    "1 command. Loops.",
    slamLine2:    "Brainstorm → ship code.",
    slamLine3:    "Saves 6 hours. Per feature.",
    ctaLine1:     "14B.",
    ctaLine2:     "One 3090.",
    ctaLine3:     "Full agent loop.",
    accentColor:  "green" as const,
  },
};

// ── Beat 1 ────────────────────────────────────────────────────────────────────

type Beat1Props = Pick<CustomVideoProps,
  "beat1Section"|"hookLine1"|"hookLine2"|"hookSub"|"chip1"|"chip2"|"chip3"|"accentColor">;

const Beat1: React.FC<Beat1Props> = ({
  beat1Section, hookLine1, hookLine2, hookSub, chip1, chip2, chip3, accentColor,
}) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.green;
  const { scale: bs } = useBreath(frame, fps);

  const heroSp    = spring({ frame, fps, config: SPRING_HEAVY });
  const heroScale = interpolate(heroSp, [0, 1], [0.6, 1], { extrapolateRight: "clamp" });
  const pulse     = usePulseAt(frame, [60], accent, 48);
  const sub       = useSlideIn(frame, "up", 30);
  const chip0sl   = useSlideIn(frame, "up", 55);
  const chip1sl   = useSlideIn(frame, "up", 70);
  const chip2sl   = useSlideIn(frame, "up", 85);
  const chipSls   = [chip0sl, chip1sl, chip2sl];
  const chips     = [chip1, chip2, chip3];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 40%, #0A1A0A 0%, #0A0A0A 70%)",
      position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
      paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72,
      boxSizing: "border-box", justifyContent: "center", gap: 28, fontFamily: FONT,
    }}>
      <ParticleBackground frame={frame} />
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 28 }}>
        <SectionLabelRow text={beat1Section} color="green" />
        <div style={{
          opacity: 1,
          transform: `scale(${heroScale * (frame > 22 ? bs : 1)})`,
          transformOrigin: "left center",
          boxShadow: pulse,
        }}>
          <div style={{ ...HERO_NUMBER, fontSize: 148, fontWeight: 800, color: accent, lineHeight: 0.95,
            textShadow: `0 0 60px ${accent}55, 0 0 120px ${accent}20` }}>
            {hookLine1}
          </div>
          <div style={{ ...HERO_NUMBER, fontSize: 148, fontWeight: 800, color: accent, lineHeight: 0.95,
            textShadow: `0 0 60px ${accent}55, 0 0 120px ${accent}20` }}>
            {hookLine2}
          </div>
        </div>
        <div style={{ ...sub, opacity: sub.opacity }}>
          <div style={{ ...BROADCAST_TEXT, fontSize: 52, fontWeight: 700, color: COLOR.white,
            lineHeight: 1.2, letterSpacing: "-0.01em" }}>
            {hookSub}
          </div>
        </div>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          {chipSls.map((sl, i) => (
            <span key={i} style={{ ...sl, display: "inline-block",
              background: `${accent}12`, border: `1px solid ${accent}35`,
              color: accent, padding: "10px 22px", borderRadius: 100,
              fontSize: 24, fontWeight: 600, fontFamily: FONT, letterSpacing: "0.04em" }}>
              {chips[i]}
            </span>
          ))}
        </div>
      </div>
      <TelemetryFrame frame={frame} />
    </div>
  );
};

// ── Beat 2 ────────────────────────────────────────────────────────────────────

type Beat2Props = Pick<CustomVideoProps,
  "beat2Section"|
  "card1Value"|"card1Label"|"card1Sublabel"|
  "card2Value"|"card2Label"|"card2Sublabel"|
  "card3Value"|"card3Label"|"card3Sublabel"|
  "accentColor">;

const Beat2: React.FC<Beat2Props> = ({
  beat2Section,
  card1Value, card1Label, card1Sublabel,
  card2Value, card2Label, card2Sublabel,
  card3Value, card3Label, card3Sublabel,
  accentColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.green;
  const pulse  = usePulseAt(frame, [120], accent, 48);

  const cards = [
    { value: card1Value, label: card1Label, sublabel: card1Sublabel, color: accent },
    { value: card2Value, label: card2Label, sublabel: card2Sublabel, color: COLOR.cyan  },
    { value: card3Value, label: card3Label, sublabel: card3Sublabel, color: COLOR.white },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 50%, #111 0%, #0A0A0A 70%)",
      position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
      paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72,
      boxSizing: "border-box", fontFamily: FONT, gap: 28,
    }}>
      <ParticleBackground frame={frame} />
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 28, flex: 1 }}>
        <SectionLabelRow text={beat2Section} color="cyan" />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 20 }}>
          {cards.map((item, i) => {
            const sp      = spring({ frame: Math.max(0, frame - i * 45), fps, config: SPRING_MEDIUM });
            const opacity = interpolate(sp, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
            const scale   = interpolate(sp, [0, 1],   [0.92, 1], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                opacity, transform: `scale(${scale})`,
                transformOrigin: "left center", willChange: "transform, opacity",
                background: `${item.color}${i === 0 ? "10" : "07"}`,
                border: `1px solid ${item.color}${i === 0 ? "50" : "25"}`,
                borderRadius: 16, padding: "28px 32px",
                display: "flex", alignItems: "center", gap: 24,
                boxShadow: i === 0 ? pulse : "none",
              }}>
                <div style={{ width: 4, alignSelf: "stretch", background: item.color,
                  borderRadius: 2, opacity: i === 0 ? 1 : 0.5, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ ...HERO_NUMBER, fontSize: 80, fontWeight: 800,
                    color: item.color, lineHeight: 1.0,
                    textShadow: i === 0 ? `0 0 50px ${item.color}50` : "none" }}>
                    {item.value}
                  </div>
                  <div style={{ ...BROADCAST_TEXT, fontSize: 22, fontWeight: 600,
                    color: COLOR.white, opacity: 0.8, marginTop: 6 }}>
                    {item.label}
                  </div>
                  <div style={{ fontSize: 17, color: "rgba(255,255,255,0.35)",
                    marginTop: 4, fontFamily: FONT }}>
                    {item.sublabel}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <TelemetryFrame frame={frame} />
    </div>
  );
};

// ── Beat 3 ────────────────────────────────────────────────────────────────────

type Beat3Props = Pick<CustomVideoProps, "beat3Section"|"slamLine1"|"slamLine2"|"slamLine3"|"accentColor">;

const Beat3: React.FC<Beat3Props> = ({ beat3Section, slamLine1, slamLine2, slamLine3, accentColor }) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.cyan;
  const { scale: bs } = useBreath(frame, fps);
  const glowPulse = Math.sin((frame / fps) * Math.PI * 2 * 0.4) * 0.5 + 0.5;
  const pulse0    = usePulseAt(frame, [45, 90], accent, 40);

  const sp0 = spring({ frame, fps, config: SPRING_HEAVY });
  const sl1 = useSlideIn(frame, "up", 60);
  const sl2 = useSlideIn(frame, "up", 120);

  const lines = [slamLine1, slamLine2, slamLine3];
  const items = [
    { opacity: interpolate(sp0, [0, 0.2], [0, 1], { extrapolateRight: "clamp" }),
      transform: `translateY(${interpolate(sp0, [0, 1], [40, 0])}px)${frame > 22 ? ` scale(${bs})` : ""}`,
      pulse: pulse0 },
    { opacity: sl1.opacity, transform: sl1.transform, pulse: "none" },
    { opacity: sl2.opacity, transform: sl2.transform, pulse: "none" },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 50%, #111 0%, #0A0A0A 70%)",
      position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
      paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72,
      boxSizing: "border-box", fontFamily: FONT, gap: 40,
    }}>
      <ParticleBackground frame={frame} />
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 40, flex: 1 }}>
        <SectionLabelRow text={beat3Section} color="cyan" />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 36 }}>
          {lines.map((line, i) => (
            <div key={i} style={{
              opacity: items[i].opacity, transform: items[i].transform,
              transformOrigin: "left center", willChange: "transform, opacity",
              boxShadow: items[i].pulse,
            }}>
              <div style={{
                ...BROADCAST_TEXT,
                fontSize:      i === 0 ? 84 : 72,
                fontWeight:    800,
                color:         i === 0 ? accent : COLOR.white,
                lineHeight:    1.05,
                letterSpacing: "-0.03em",
                textShadow:    i === 0 ? `0 0 ${40 + glowPulse * 40}px ${accent}35` : "none",
              }}>
                {line}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${accent}40, transparent)`, zIndex: 2 }} />
      <TelemetryFrame frame={frame} />
    </div>
  );
};

// ── Beat 4 ────────────────────────────────────────────────────────────────────

type Beat4Props = Pick<CustomVideoProps, "ctaLine1"|"ctaLine2"|"ctaLine3"|"accentColor">;

const Beat4: React.FC<Beat4Props> = ({ ctaLine1, ctaLine2, ctaLine3, accentColor }) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.cyan;
  const { scale: bs } = useBreath(frame, fps);

  const sp      = spring({ frame: Math.max(0, frame - 1), fps, config: SPRING_HEAVY });
  const opacity = interpolate(sp, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
  const scale   = interpolate(sp, [0, 1],   [0.7, 1], { extrapolateRight: "clamp" });
  const pulse   = usePulseAt(frame, [45, 100], accent, 40);
  const labelOp = interpolate(
    spring({ frame, fps, config: SPRING_MEDIUM }), [0, 0.3], [0, 1], { extrapolateRight: "clamp" }
  );

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 60%, #111 0%, #0A0A0A 70%)",
      position: "relative", overflow: "hidden", fontFamily: FONT,
    }}>
      <ParticleBackground frame={frame} />
      <div style={{
        position: "absolute", inset: 0, zIndex: 2,
        display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center",
        paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72,
        boxSizing: "border-box", gap: 24, textAlign: "center",
      }}>
        <div style={{ ...BROADCAST_TEXT, fontSize: 20, fontWeight: 500, color: accent,
          letterSpacing: "0.18em", textTransform: "uppercase", opacity: labelOp }}>
          TAKEAWAY
        </div>
        <div style={{ opacity, transform: `scale(${scale * (frame > 22 ? bs : 1)})`, boxShadow: pulse }}>
          <div style={{ ...BROADCAST_TEXT, fontSize: 116, fontWeight: 800, color: accent,
            lineHeight: 0.95, letterSpacing: "-0.03em",
            textShadow: `0 0 60px ${accent}50, 0 0 120px ${accent}20` }}>
            {ctaLine1}
          </div>
          <div style={{ ...BROADCAST_TEXT, fontSize: 58, fontWeight: 700, color: COLOR.white,
            lineHeight: 1.2, letterSpacing: "-0.01em", marginTop: 16, opacity: 0.9 }}>
            {ctaLine2}
          </div>
          <div style={{ ...BROADCAST_TEXT, fontSize: 48, fontWeight: 600, color: COLOR.white,
            lineHeight: 1.2, letterSpacing: "-0.005em", marginTop: 12, opacity: 0.65 }}>
            {ctaLine3}
          </div>
        </div>
      </div>
      <TelemetryFrame frame={frame} />
    </div>
  );
};

// ── Root ───────────────────────────────────────────────────────────────────────

export const CustomVideo: React.FC<CustomVideoProps> = (props) => {
  const {
    beat1Section, hookLine1, hookLine2, hookSub, chip1, chip2, chip3,
    beat2Section, card1Value, card1Label, card1Sublabel,
    card2Value, card2Label, card2Sublabel,
    card3Value, card3Label, card3Sublabel,
    beat3Section, slamLine1, slamLine2, slamLine3,
    ctaLine1, ctaLine2, ctaLine3,
    accentColor,
  } = props;

  return (
    <div style={{ width: "100%", height: "100%", background: "#0A0A0A", position: "relative" }}>
      <Audio src={staticFile("narration.wav")} />
      <Sequence from={0}   durationInFrames={82}>
        <Beat1
          beat1Section={beat1Section} hookLine1={hookLine1} hookLine2={hookLine2}
          hookSub={hookSub} chip1={chip1} chip2={chip2} chip3={chip3} accentColor={accentColor}
        />
      </Sequence>
      <Sequence from={82}  durationInFrames={153}>
        <Beat2
          beat2Section={beat2Section}
          card1Value={card1Value} card1Label={card1Label} card1Sublabel={card1Sublabel}
          card2Value={card2Value} card2Label={card2Label} card2Sublabel={card2Sublabel}
          card3Value={card3Value} card3Label={card3Label} card3Sublabel={card3Sublabel}
          accentColor={accentColor}
        />
      </Sequence>
      <Sequence from={235} durationInFrames={220}>
        <Beat3
          beat3Section={beat3Section} slamLine1={slamLine1}
          slamLine2={slamLine2} slamLine3={slamLine3} accentColor={accentColor}
        />
      </Sequence>
      <Sequence from={455} durationInFrames={159}>
        <Beat4 ctaLine1={ctaLine1} ctaLine2={ctaLine2} ctaLine3={ctaLine3} accentColor={accentColor} />
      </Sequence>
    </div>
  );
};
