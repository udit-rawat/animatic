/**
 * CustomVideo.tsx — Microsoft markitdown. One command.
 * 660 frames · 30fps · 22.0s
 *
 * beat_1  frames   0–138   MetricFocus: "ZERO" hero @1f, chips @37/51/65f
 * beat_2  frames 138–332   TriStat: 3 stats slide @8/53/98f, pulse @58f
 * beat_3  frames 332–534   StatementSlam: lines @6/24/42f (18f stagger)
 * beat_4  frames 534–660   TakeawayScene: headline slam @1f, CTA @28f, pulse @45f
 */

import React from "react";
import { z } from "zod";
import {
  Sequence, useCurrentFrame, useVideoConfig,
  Audio, staticFile, spring, interpolate,
} from "remotion";
import {
  usePulseAt, useSlideIn, countUp,
  COLOR, FONT, HERO_NUMBER, BROADCAST_TEXT,
  SectionLabelRow, ParticleBackground, TelemetryFrame, useBreath,
} from "./layouts/_shared";
import { SPRING_HEAVY, SPRING_MEDIUM } from "./utils/springIn";

// ── Schema ────────────────────────────────────────────────────────────────────

export const customVideoSchema = z.object({
  beat1Section: z.string().default("DOCUMENT CONVERSION"),
  heroValue:    z.string().default("ZERO"),
  heroLabel:    z.string().default("API cost"),
  heroContext:  z.string().default("One pip. Converts 9 file types locally."),
  chip1:        z.string().default("PDF · DOCX · PPTX"),
  chip2:        z.string().default("Images · Audio"),
  chip3:        z.string().default("pip install markitdown"),

  beat2Section: z.string().default("9 FILE TYPES"),
  stat1Value:   z.string().default("9"),
  stat1Label:   z.string().default("File Types"),
  stat1Sub:     z.string().default("PDF DOCX PPTX XLS images audio"),
  stat2Value:   z.string().default("0 $"),
  stat2Label:   z.string().default("API Cost"),
  stat2Sub:     z.string().default("runs fully local"),
  stat3Value:   z.string().default("1 pip"),
  stat3Label:   z.string().default("Install"),
  stat3Sub:     z.string().default("pip install markitdown"),

  beat3Section: z.string().default("LOCAL PIPELINES"),
  slamLine1:    z.string().default("Skip brittle parsers."),
  slamLine2:    z.string().default("Zero paid APIs."),
  slamLine3:    z.string().default("One pip install."),

  ctaHeadline:  z.string().default("markitdown"),
  ctaSub:       z.string().default("Pull it. Run it."),

  accentColor: z.enum(["cyan", "green", "yellow"]).default("cyan"),
});

export type CustomVideoProps = z.infer<typeof customVideoSchema>;

export const CustomVideoConfig = {
  durationInFrames: 660,
  fps:    30,
  width:  1080,
  height: 1920,
  defaultProps: {
    beat1Section: "DOCUMENT CONVERSION",
    heroValue:    "ZERO",
    heroLabel:    "API cost",
    heroContext:  "One pip. Converts 9 file types locally.",
    chip1:        "PDF · DOCX · PPTX",
    chip2:        "Images · Audio",
    chip3:        "pip install markitdown",
    beat2Section: "9 FILE TYPES",
    stat1Value:   "9",
    stat1Label:   "File Types",
    stat1Sub:     "PDF DOCX PPTX XLS images audio",
    stat2Value:   "0 $",
    stat2Label:   "API Cost",
    stat2Sub:     "runs fully local",
    stat3Value:   "1 pip",
    stat3Label:   "Install",
    stat3Sub:     "pip install markitdown",
    beat3Section: "LOCAL PIPELINES",
    slamLine1:    "Skip brittle parsers.",
    slamLine2:    "Zero paid APIs.",
    slamLine3:    "One pip install.",
    ctaHeadline:  "markitdown",
    ctaSub:       "Pull it. Run it.",
    accentColor:  "cyan" as const,
  },
};

// ── Beat 1 — MetricFocus ──────────────────────────────────────────────────────
// hero @1f (opacity 1), context @21f, chip0 @37f, chip1 @51f, chip2 @65f, pulse @60f

type Beat1Props = Pick<CustomVideoProps,
  "beat1Section"|"heroValue"|"heroLabel"|"heroContext"|"chip1"|"chip2"|"chip3"|"accentColor">;

const Beat1: React.FC<Beat1Props> = ({
  beat1Section, heroValue, heroLabel, heroContext, chip1, chip2, chip3, accentColor,
}) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.cyan;
  const { scale: bs } = useBreath(frame, fps);

  const heroSp    = spring({ frame: Math.max(0, frame - 1), fps, config: SPRING_HEAVY });
  const heroScale = interpolate(heroSp, [0, 1], [0.6, 1], { extrapolateRight: "clamp" });
  const pulse     = usePulseAt(frame, [60], accent, 48);
  const ctx       = useSlideIn(frame, "up", 21);
  const chip0sl   = useSlideIn(frame, "up", 37);
  const chip1sl   = useSlideIn(frame, "up", 51);
  const chip2sl   = useSlideIn(frame, "up", 65);
  const chipSls   = [chip0sl, chip1sl, chip2sl];
  const chips     = [chip1, chip2, chip3];

  // countUp: animate hero number if numeric
  const heroSp2  = spring({ frame: Math.max(0, frame - 1), fps, config: SPRING_MEDIUM });
  const numeric  = parseFloat(heroValue);
  const displayed = isNaN(numeric) ? heroValue : countUp(String(numeric), heroSp2);

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 40%, #001A1A 0%, #0A0A0A 70%)",
      position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
      paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72,
      boxSizing: "border-box", justifyContent: "center", gap: 28, fontFamily: FONT,
    }}>
      <ParticleBackground frame={frame} />
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 28 }}>
        <SectionLabelRow text={beat1Section} color="cyan" />

        {/* Hero — visible at frame 1 */}
        <div style={{
          opacity: 1,
          transform: `scale(${heroScale * (frame > 22 ? bs : 1)})`,
          transformOrigin: "left center",
          boxShadow: pulse,
        }}>
          <div style={{ ...HERO_NUMBER, fontSize: 148, fontWeight: 800, color: accent, lineHeight: 0.95,
            textShadow: `0 0 60px ${accent}55, 0 0 120px ${accent}20` }}>
            {displayed}
          </div>
          <div style={{ ...BROADCAST_TEXT, fontSize: 28, fontWeight: 600,
            color: "rgba(255,255,255,0.5)", letterSpacing: "0.1em", marginTop: 8 }}>
            {heroLabel}
          </div>
        </div>

        {/* Context @21f */}
        <div style={{ ...ctx, opacity: ctx.opacity }}>
          <div style={{ ...BROADCAST_TEXT, fontSize: 44, fontWeight: 700, color: COLOR.white,
            lineHeight: 1.25, letterSpacing: "-0.01em" }}>
            {heroContext}
          </div>
        </div>

        {/* Chips @37/51/65f */}
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          {chipSls.map((sl, i) => (
            <span key={i} style={{ ...sl, display: "inline-block",
              background: `${accent}12`, border: `1px solid ${accent}35`,
              color: accent, padding: "10px 22px", borderRadius: 100,
              fontSize: 22, fontWeight: 600, fontFamily: FONT, letterSpacing: "0.04em" }}>
              {chips[i]}
            </span>
          ))}
        </div>
      </div>
      <TelemetryFrame frame={frame} />
    </div>
  );
};

// ── Beat 2 — TriStat ──────────────────────────────────────────────────────────
// 3 stat cards slide @8/53/98f, pulse on card 0 @58f

type Beat2Props = Pick<CustomVideoProps,
  "beat2Section"|"stat1Value"|"stat1Label"|"stat1Sub"|
  "stat2Value"|"stat2Label"|"stat2Sub"|
  "stat3Value"|"stat3Label"|"stat3Sub"|"accentColor">;

const Beat2: React.FC<Beat2Props> = ({
  beat2Section, stat1Value, stat1Label, stat1Sub,
  stat2Value, stat2Label, stat2Sub,
  stat3Value, stat3Label, stat3Sub, accentColor,
}) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.cyan;
  const pulse   = usePulseAt(frame, [58], accent, 48);

  const stats = [
    { value: stat1Value, label: stat1Label, sub: stat1Sub, color: accent,     startFrame: 8  },
    { value: stat2Value, label: stat2Label, sub: stat2Sub, color: COLOR.green, startFrame: 53 },
    { value: stat3Value, label: stat3Label, sub: stat3Sub, color: COLOR.white, startFrame: 98 },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 50%, #001A1A 0%, #0A0A0A 70%)",
      position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column",
      paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72,
      boxSizing: "border-box", fontFamily: FONT, gap: 28,
    }}>
      <ParticleBackground frame={frame} />
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", gap: 28, flex: 1 }}>
        <SectionLabelRow text={beat2Section} color="cyan" />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 24 }}>
          {stats.map((stat, i) => {
            const sp      = spring({ frame: Math.max(0, frame - stat.startFrame), fps, config: SPRING_MEDIUM });
            const opacity = interpolate(sp, [0, 0.2], [0, 1], { extrapolateRight: "clamp" });
            const translateX = interpolate(sp, [0, 1], [-40, 0], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                opacity,
                transform: `translateX(${translateX}px)`,
                willChange: "transform, opacity",
                background: `${stat.color}${i === 0 ? "10" : "07"}`,
                border: `1px solid ${stat.color}${i === 0 ? "45" : "20"}`,
                borderRadius: 16, padding: "28px 32px",
                display: "flex", alignItems: "center", gap: 24,
                boxShadow: i === 0 ? pulse : "none",
              }}>
                <div style={{ width: 4, alignSelf: "stretch", background: stat.color,
                  borderRadius: 2, opacity: i === 0 ? 1 : 0.5, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ ...HERO_NUMBER, fontSize: 80, fontWeight: 800,
                    color: stat.color, lineHeight: 1.0,
                    textShadow: i === 0 ? `0 0 50px ${stat.color}50` : "none" }}>
                    {stat.value}
                  </div>
                  <div style={{ ...BROADCAST_TEXT, fontSize: 22, fontWeight: 600,
                    color: COLOR.white, opacity: 0.8, marginTop: 6 }}>
                    {stat.label}
                  </div>
                  <div style={{ fontSize: 17, color: "rgba(255,255,255,0.35)",
                    marginTop: 4, fontFamily: FONT }}>
                    {stat.sub}
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

// ── Beat 3 — StatementSlam ────────────────────────────────────────────────────
// lines @6/24/42f (18f stagger), pulse line_0 @45/90f

type Beat3Props = Pick<CustomVideoProps, "beat3Section"|"slamLine1"|"slamLine2"|"slamLine3"|"accentColor">;

const Beat3: React.FC<Beat3Props> = ({ beat3Section, slamLine1, slamLine2, slamLine3, accentColor }) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.cyan;
  const { scale: bs } = useBreath(frame, fps);
  const glowPulse = Math.sin((frame / fps) * Math.PI * 2 * 0.4) * 0.5 + 0.5;
  const pulse0    = usePulseAt(frame, [45, 90], accent, 40);

  const sl0 = useSlideIn(frame, "up", 6);
  const sl1 = useSlideIn(frame, "up", 24);
  const sl2 = useSlideIn(frame, "up", 42);

  const lines = [slamLine1, slamLine2, slamLine3];
  const items = [
    { opacity: sl0.opacity, transform: `${sl0.transform}${frame > 22 ? ` scale(${bs})` : ""}`, pulse: pulse0 },
    { opacity: sl1.opacity, transform: sl1.transform, pulse: "none" },
    { opacity: sl2.opacity, transform: sl2.transform, pulse: "none" },
  ];

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 50%, #001A1A 0%, #0A0A0A 70%)",
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

// ── Beat 4 — TakeawayScene ────────────────────────────────────────────────────
// headline slam @1f, cta @28f, pulse @45f — Option 1 CTA

type Beat4Props = Pick<CustomVideoProps, "ctaHeadline"|"ctaSub"|"accentColor">;

const Beat4: React.FC<Beat4Props> = ({ ctaHeadline, ctaSub, accentColor }) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const accent  = COLOR[accentColor as keyof typeof COLOR] ?? COLOR.cyan;
  const { scale: bs } = useBreath(frame, fps);

  const headSp    = spring({ frame: Math.max(0, frame - 1), fps, config: SPRING_HEAVY });
  const headScale = interpolate(headSp, [0, 1], [0.65, 1], { extrapolateRight: "clamp" });
  const pulse     = usePulseAt(frame, [45], accent, 48);
  const ctaSl     = useSlideIn(frame, "up", 28);

  // "1 pip." chip slides @48f
  const pipSl = useSlideIn(frame, "up", 48);

  return (
    <div style={{
      width: "100%", height: "100%",
      background: "radial-gradient(ellipse at 50% 60%, #001A1A 0%, #0A0A0A 70%)",
      position: "relative", overflow: "hidden", fontFamily: FONT,
    }}>
      <ParticleBackground frame={frame} />
      <div style={{
        position: "absolute", inset: 0, zIndex: 2,
        display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center",
        paddingTop: 120, paddingBottom: 180, paddingLeft: 72, paddingRight: 72,
        boxSizing: "border-box", gap: 24, textAlign: "center",
      }}>
        {/* Headline slams @1f */}
        <div style={{
          opacity: 1,
          transform: `scale(${headScale * (frame > 22 ? bs : 1)})`,
          boxShadow: pulse,
        }}>
          <div style={{ ...HERO_NUMBER, fontSize: 116, fontWeight: 800, color: accent,
            lineHeight: 0.9, letterSpacing: "-0.04em",
            textShadow: `0 0 80px ${accent}60, 0 0 160px ${accent}25` }}>
            {ctaHeadline}
          </div>
        </div>

        {/* CTA @28f */}
        <div style={{ ...ctaSl, opacity: ctaSl.opacity }}>
          <div style={{ ...BROADCAST_TEXT, fontSize: 56, fontWeight: 700, color: COLOR.white,
            letterSpacing: "-0.01em", lineHeight: 1.1 }}>
            {ctaSub}
          </div>
        </div>

        {/* pip install chip @48f */}
        <div style={{ ...pipSl, opacity: pipSl.opacity }}>
          <div style={{
            fontSize: 24, fontWeight: 500,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            color: `${accent}90`, letterSpacing: "0.02em",
            background: `${accent}10`, border: `1px solid ${accent}25`,
            padding: "12px 28px", borderRadius: 8,
          }}>
            pip install markitdown
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
    beat1Section, heroValue, heroLabel, heroContext, chip1, chip2, chip3,
    beat2Section, stat1Value, stat1Label, stat1Sub,
    stat2Value, stat2Label, stat2Sub,
    stat3Value, stat3Label, stat3Sub,
    beat3Section, slamLine1, slamLine2, slamLine3,
    ctaHeadline, ctaSub,
    accentColor,
  } = props;

  return (
    <div style={{ width: "100%", height: "100%", background: "#0A0A0A", position: "relative" }}>
      <Audio src={staticFile("narration.wav")} />
      <Sequence from={0}   durationInFrames={138}>
        <Beat1
          beat1Section={beat1Section} heroValue={heroValue} heroLabel={heroLabel}
          heroContext={heroContext} chip1={chip1} chip2={chip2} chip3={chip3} accentColor={accentColor}
        />
      </Sequence>
      <Sequence from={138} durationInFrames={194}>
        <Beat2
          beat2Section={beat2Section}
          stat1Value={stat1Value} stat1Label={stat1Label} stat1Sub={stat1Sub}
          stat2Value={stat2Value} stat2Label={stat2Label} stat2Sub={stat2Sub}
          stat3Value={stat3Value} stat3Label={stat3Label} stat3Sub={stat3Sub}
          accentColor={accentColor}
        />
      </Sequence>
      <Sequence from={332} durationInFrames={202}>
        <Beat3
          beat3Section={beat3Section} slamLine1={slamLine1}
          slamLine2={slamLine2} slamLine3={slamLine3} accentColor={accentColor}
        />
      </Sequence>
      <Sequence from={534} durationInFrames={126}>
        <Beat4 ctaHeadline={ctaHeadline} ctaSub={ctaSub} accentColor={accentColor} />
      </Sequence>
    </div>
  );
};
