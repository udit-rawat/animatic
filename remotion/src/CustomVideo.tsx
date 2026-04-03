/**
 * CustomVideo.tsx — Gemma 4 by Google
 * 1108 frames · 30fps · 36.9s
 *
 * [hook]       frames   0–206   6.9s
 * [concept_1]  frames 206–567  12.0s
 * [concept_2]  frames 567–807   8.0s
 * [takeaway]   frames 807–1108 10.0s
 *
 * Theme: #0A0A0A · white · #FBBC04 yellow
 */
import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Audio,
  staticFile,
  AbsoluteFill,
} from "remotion";

// ── Timing ────────────────────────────────────────────────────────────────────
const T = {
  hook: { start: 0,   end: 206  },
  c1:   { start: 206, end: 567  },
  c2:   { start: 567, end: 807  },
  cta:  { start: 807, end: 1108 },
};
const TOTAL_FRAMES = 1108;

const BG     = "#0A0A0A";
const WHITE  = "#FFFFFF";
const YELLOW = "#FBBC04";

// ── Helpers ───────────────────────────────────────────────────────────────────
const clamp = (v: number, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));

const fi = (lf: number, from: number, dur = 14) =>
  clamp((lf - from) / dur);

const fo = (lf: number, from: number, dur = 14) =>
  clamp(1 - (lf - from) / dur);

// Deterministic particle positions (no Math.random)
const particles = Array.from({ length: 60 }, (_, i) => {
  const s1 = Math.sin(i * 127.1) * 43758.5453;
  const s2 = Math.sin(i * 311.7 + 99) * 43758.5453;
  const s3 = Math.sin(i * 74.3  + 33) * 43758.5453;
  const s4 = Math.sin(i * 210.9 + 17) * 43758.5453;
  const frac = (v: number) => v - Math.floor(v);
  return {
    x:  frac(s1) * 1080,
    y:  frac(s2) * 1920,
    vx: (frac(s3) - 0.5) * 0.6,
    vy: (frac(s4) - 0.5) * 0.6,
    r:  1.5 + frac(Math.sin(i * 53.1) * 9999) * 2,
  };
});

// Character-by-character reveal: returns visible char count
const charReveal = (lf: number, from: number, framesPerChar = 4) =>
  Math.floor(clamp((lf - from) / framesPerChar, 0, 999));

// ═══════════════════════════════════════════════════════════════════════════════
// HOOK  frames 0–206
// ═══════════════════════════════════════════════════════════════════════════════
const HookSection: React.FC<{ lf: number; fps: number }> = ({ lf, fps }) => {
  // ── Line draw (0–40) ──────────────────────────────────────────────────────
  const lineW = interpolate(lf, [0, 40], [0, 540], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // ── Line explosion (40–55): line expands to full screen height ────────────
  const explodeH = interpolate(lf, [40, 52], [2, 1920], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const explodeO = interpolate(lf, [40, 55], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const showLine    = lf < 55;
  const showContent = lf >= 55;

  // ── GEMMA 4 drop (60–90) ──────────────────────────────────────────────────
  const gemmaY = lf >= 60
    ? interpolate(
        spring({ frame: lf - 60, fps, config: { damping: 11, stiffness: 160, mass: 0.9 } }),
        [0, 1], [-280, 0]
      )
    : -280;
  const gemmaO = fi(lf, 60, 8);

  // ── FREE. drop (78–108) ───────────────────────────────────────────────────
  const freeY = lf >= 78
    ? interpolate(
        spring({ frame: lf - 78, fps, config: { damping: 11, stiffness: 160, mass: 0.9 } }),
        [0, 1], [-180, 0]
      )
    : -180;
  const freeO = fi(lf, 78, 8);

  // ── Particles (alive from frame 100) ─────────────────────────────────────
  const particleO = fi(lf, 100, 20);

  // ── Char reveals ─────────────────────────────────────────────────────────
  const lines = [
    { text: "No paywall.",    from: 118 },
    { text: "Runs offline.",  from: 142 },
    { text: "Just download.", from: 166 },
  ];

  return (
    <AbsoluteFill style={{ background: BG, overflow: "hidden" }}>

      {/* ── Line draw → explosion ── */}
      {showLine && (
        <div style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width:  lf < 40 ? lineW * 2 : 1080,
          height: lf < 40 ? 2 : explodeH,
          background: WHITE,
          opacity: lf < 40 ? 1 : explodeO,
        }} />
      )}

      {/* ── Particles ── */}
      {showContent && (
        <div style={{ position: "absolute", inset: 0, opacity: particleO, pointerEvents: "none" }}>
          {particles.map((p, i) => (
            <div key={i} style={{
              position: "absolute",
              left: (p.x + p.vx * lf + 1080) % 1080,
              top:  (p.y + p.vy * lf + 1920) % 1920,
              width:  p.r * 2,
              height: p.r * 2,
              borderRadius: "50%",
              background: WHITE,
              opacity: 0.07,
            }} />
          ))}
        </div>
      )}

      {/* ── GEMMA 4 ── */}
      {showContent && (
        <div style={{
          position: "absolute",
          top: "28%",
          width: "100%",
          textAlign: "center",
          opacity: gemmaO,
          transform: `translateY(${gemmaY}px)`,
        }}>
          <div style={{
            fontSize: 148,
            fontWeight: 900,
            color: WHITE,
            fontFamily: "Inter, system-ui, sans-serif",
            lineHeight: 1,
            letterSpacing: "-0.03em",
          }}>GEMMA</div>
        </div>
      )}

      {/* ── FREE. (yellow, drops after GEMMA) ── */}
      {showContent && (
        <div style={{
          position: "absolute",
          top: "50%",
          width: "100%",
          textAlign: "center",
          opacity: freeO,
          transform: `translateY(${freeY}px)`,
        }}>
          <div style={{
            fontSize: 200,
            fontWeight: 900,
            color: YELLOW,
            fontFamily: "Inter, system-ui, sans-serif",
            lineHeight: 0.85,
            letterSpacing: "-0.04em",
            textShadow: `0 0 80px rgba(251,188,4,0.5)`,
          }}>4</div>
        </div>
      )}

      {/* ── Char-reveal detail lines ── */}
      {showContent && (
        <div style={{
          position: "absolute",
          bottom: 175,
          width: "100%",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
        }}>
          {lines.map((l, i) => {
            const visible = charReveal(lf, l.from, 3);
            const text    = l.text.slice(0, visible);
            const opa     = fi(lf, l.from, 6);
            if (opa <= 0) return null;
            return (
              <div key={i} style={{
                fontSize: 30,
                fontWeight: 500,
                color: WHITE,
                fontFamily: "Inter, 'Courier New', monospace",
                opacity: Math.min(1, opa + 0.1),
                letterSpacing: "0.02em",
              }}>{text}</div>
            );
          })}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// CONCEPT 1  frames 206–567
// Directional sentence entrances → counter to 400M
// ═══════════════════════════════════════════════════════════════════════════════
const Concept1Section: React.FC<{ lf: number; fps: number }> = ({ lf, fps }) => {
  // 4-frame flash
  const flashO = interpolate(lf, [0, 4], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // ── Three directional sentences (lf 4–300) ────────────────────────────────
  type Dir = "left" | "right" | "top";
  const sentences: { text: string; dir: Dir; arriveAt: number; stackY: number }[] = [
    { text: "Complex reasoning.", dir: "left",  arriveAt: 10,  stackY: -100 },
    { text: "Planning.",          dir: "right", arriveAt: 55,  stackY:    0 },
    { text: "Building agents.",   dir: "top",   arriveAt: 100, stackY:  100 },
  ];

  // Each sentence: slides in to center, holds full opacity, then dims + moves to stack pos
  // Stack exit starts at lf 200
  const showSentences = lf < 300;
  const showStat      = lf >= 290;

  // "Gemma 4 handles all of it." (lf 200–270)
  const handlesO = lf >= 200
    ? clamp(fi(lf, 200, 16) * fo(lf, 250, 20))
    : 0;

  // Counter 0→400 (lf 300–380)
  const counterVal = Math.round(
    interpolate(lf, [300, 390], [0, 400], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    })
  );
  const counterO = fi(lf, 300, 10);

  // "million" slides up (lf 390–420)
  const millionO = fi(lf, 390, 16);
  const millionY = interpolate(lf, [390, 415], [30, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // "This one is stronger." (lf 430–567)
  const strongerO = fi(lf, 430, 20);

  return (
    <AbsoluteFill style={{ background: BG, overflow: "hidden" }}>
      {/* flash */}
      <AbsoluteFill style={{ background: WHITE, opacity: flashO, pointerEvents: "none" }} />

      {/* ── Directional sentences ── */}
      {showSentences && sentences.map((s, i) => {
        const arrived = lf >= s.arriveAt;
        if (!arrived) return null;

        const progress = spring({
          frame: lf - s.arriveAt,
          fps,
          config: { damping: 18, stiffness: 140, mass: 0.8 },
        });

        // Slide from direction → center
        const offX = s.dir === "left" ? -700 : s.dir === "right" ? 700 : 0;
        const offY = s.dir === "top"  ? -500 : 0;
        const cx   = interpolate(progress, [0, 1], [offX, 0]);
        const cy   = interpolate(progress, [0, 1], [offY, 0]);

        // After lf 200: drift to stack position + dim
        const exitProgress = clamp((lf - 200) / 40);
        const stackX = interpolate(exitProgress, [0, 1], [0, 0]);
        const stackY = interpolate(exitProgress, [0, 1], [0, s.stackY]);
        const dimO   = interpolate(exitProgress, [0, 1], [1, 0.28]);
        const scaleE = interpolate(exitProgress, [0, 1], [1, 0.72]);

        return (
          <div key={i} style={{
            position: "absolute",
            top: "50%",
            width: "100%",
            textAlign: "center",
            transform: `translate(${cx + stackX}px, calc(-50% + ${cy + stackY}px)) scale(${scaleE})`,
            opacity: dimO,
          }}>
            <div style={{
              fontSize: 68,
              fontWeight: 900,
              color: WHITE,
              fontFamily: "Inter, system-ui, sans-serif",
              letterSpacing: "-0.02em",
            }}>{s.text}</div>
          </div>
        );
      })}

      {/* "Gemma 4 handles all of it." */}
      {lf >= 200 && lf < 300 && (
        <div style={{
          position: "absolute",
          bottom: 220,
          width: "100%",
          textAlign: "center",
          opacity: handlesO,
        }}>
          <div style={{
            fontSize: 36,
            fontWeight: 500,
            color: WHITE,
            fontFamily: "Inter, system-ui, sans-serif",
            fontStyle: "italic",
          }}>Gemma 4 handles all of it.</div>
        </div>
      )}

      {/* ── 400M counter ── */}
      {showStat && (
        <div style={{
          position: "absolute",
          top: "42%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          textAlign: "center",
        }}>
          <div style={{
            fontSize: 220,
            fontWeight: 900,
            color: YELLOW,
            fontFamily: "Inter, system-ui, sans-serif",
            lineHeight: 0.85,
            letterSpacing: "-0.05em",
            opacity: counterO,
            textShadow: `0 0 100px rgba(251,188,4,0.45)`,
          }}>{counterVal}</div>

          <div style={{
            fontSize: 72,
            fontWeight: 700,
            color: WHITE,
            fontFamily: "Inter, system-ui, sans-serif",
            opacity: millionO,
            transform: `translateY(${millionY}px)`,
            marginTop: 4,
          }}>million.</div>

          <div style={{
            fontSize: 38,
            fontWeight: 500,
            color: WHITE,
            fontFamily: "Inter, system-ui, sans-serif",
            fontStyle: "italic",
            opacity: strongerO,
            marginTop: 30,
          }}>This one is stronger.</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// CONCEPT 2  frames 567–807
// ═══════════════════════════════════════════════════════════════════════════════
const Concept2Section: React.FC<{ lf: number }> = ({ lf }) => {
  const flashO = interpolate(lf, [0, 4], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const mkLine = (from: number) => ({
    o: fi(lf, from, 10),
    y: interpolate(lf, [from, from + 22], [36, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    }),
  });

  const l1 = mkLine(10);
  const l2 = mkLine(52);
  const l3 = mkLine(90);
  const fasterO = fi(lf, 155, 16);

  return (
    <AbsoluteFill style={{ background: BG }}>
      <AbsoluteFill style={{ background: WHITE, opacity: flashO, pointerEvents: "none" }} />

      <div style={{
        position: "absolute",
        top: "35%",
        width: "100%",
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 20,
      }}>
        {[
          { label: "Your laptop.",  ...l1 },
          { label: "No cloud.",     ...l2 },
          { label: "No fees.",      ...l3 },
        ].map((item, i) => (
          <div key={i} style={{
            fontSize: 74,
            fontWeight: 900,
            color: WHITE,
            fontFamily: "Inter, system-ui, sans-serif",
            letterSpacing: "-0.025em",
            opacity: item.o,
            transform: `translateY(${item.y}px)`,
          }}>{item.label}</div>
        ))}
      </div>

      <div style={{
        position: "absolute",
        bottom: 190,
        width: "100%",
        textAlign: "center",
        opacity: fasterO,
      }}>
        <div style={{
          fontSize: 52,
          fontWeight: 700,
          color: YELLOW,
          fontFamily: "Inter, system-ui, sans-serif",
        }}>Faster than ever.</div>
      </div>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// TAKEAWAY  frames 807–1108
// ═══════════════════════════════════════════════════════════════════════════════
const TakeawaySection: React.FC<{ lf: number }> = ({ lf }) => {
  const flashO  = interpolate(lf, [0, 4], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const ruleO   = fi(lf, 6, 10);
  const textO   = fi(lf, 20, 22);
  const textY   = interpolate(lf, [20, 44], [22, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const liveO   = fi(lf, 130, 14);
  const saveO   = fi(lf, 196, 14);
  const arrowP  = interpolate(lf % 30, [0, 15, 30], [0.35, 1, 0.35], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: BG }}>
      <AbsoluteFill style={{ background: WHITE, opacity: flashO, pointerEvents: "none" }} />

      <div style={{
        position: "absolute", top: 158, width: "100%", textAlign: "center",
        opacity: ruleO,
      }}>
        <div style={{
          fontSize: 20, fontWeight: 700, color: YELLOW,
          fontFamily: "Inter, system-ui, sans-serif",
          letterSpacing: "0.5em", textTransform: "uppercase",
        }}>● RULE</div>
      </div>

      <div style={{
        position: "absolute", top: 250, left: 68, right: 68,
        opacity: textO, transform: `translateY(${textY}px)`,
      }}>
        <div style={{
          fontSize: 54, fontWeight: 800, color: WHITE,
          fontFamily: "Inter, system-ui, sans-serif",
          lineHeight: 1.28, textAlign: "center",
        }}>
          When Google open-sources{" "}
          <span style={{ color: YELLOW }}>their strongest model</span>
          {" "}— you move immediately.
        </div>
      </div>

      <div style={{
        position: "absolute", top: "60%", width: "100%", textAlign: "center",
        opacity: liveO,
      }}>
        <div style={{
          fontSize: 64, fontWeight: 800, color: YELLOW,
          fontFamily: "Inter, system-ui, sans-serif",
        }}>Gemma 4 is live.</div>
      </div>

      <div style={{
        position: "absolute", bottom: 155, width: "100%", textAlign: "center",
        opacity: saveO,
      }}>
        <div style={{
          fontSize: 44, fontWeight: 900, color: WHITE,
          fontFamily: "Inter, system-ui, sans-serif",
          letterSpacing: "0.04em",
        }}>
          SAVE THIS <span style={{ opacity: arrowP }}>↓</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// ROOT
// ═══════════════════════════════════════════════════════════════════════════════
export const CustomVideo = () => {
  const frame      = useCurrentFrame();
  const { fps }    = useVideoConfig();
  const lf = (k: keyof typeof T) => frame - T[k].start;

  return (
    <AbsoluteFill>
      <Audio src={staticFile("narration.wav")} />
      {frame >= T.hook.start && frame < T.hook.end && (
        <HookSection lf={lf("hook")} fps={fps} />
      )}
      {frame >= T.c1.start && frame < T.c1.end && (
        <Concept1Section lf={lf("c1")} fps={fps} />
      )}
      {frame >= T.c2.start && frame < T.c2.end && (
        <Concept2Section lf={lf("c2")} />
      )}
      {frame >= T.cta.start && frame <= T.cta.end && (
        <TakeawaySection lf={lf("cta")} />
      )}
    </AbsoluteFill>
  );
};

export const CustomVideoConfig = {
  width:            1080,
  height:           1920,
  fps:              30,
  durationInFrames: TOTAL_FRAMES,
};
