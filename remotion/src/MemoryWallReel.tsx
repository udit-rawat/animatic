import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const FPS = 30;
const TOTAL_SECONDS = 44;

const SANS =
  '"SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif';
const MONO = '"SF Mono", ui-monospace, Menlo, Monaco, monospace';

const BG = "#F7F7F4";
const SURFACE = "#FFFFFF";
const TEXT = "#111111";
const MUTED = "#5F6B76";
const BORDER = "#E7EBF0";
const BLUE = "#2563FF";
const RED = "#E5484D";
const GREEN = "#16A34A";
const WARM = "#F3EEE7";

const SAFE_LEFT = 72;
const SAFE_RIGHT = 212;
const SAFE_TOP = 150;
const SAFE_BOTTOM = 330;
const SAFE_WIDTH = 1080 - SAFE_LEFT - SAFE_RIGHT;
const SAFE_CENTER_X = SAFE_LEFT + SAFE_WIDTH / 2;

const SCENE_WINDOWS = {
  problem: { start: 0, end: 5.5 },
  isolation: { start: 5.5, end: 12.5 },
  connection: { start: 12.5, end: 19 },
  intelligence: { start: 19, end: 25.5 },
  diagnosis: { start: 25.5, end: 34 },
  solution: { start: 34, end: 44 },
} as const;

const memoryWallTiles = Array.from({ length: 26 }, (_, i) => ({
  x: 60 + (i % 4) * 230 + ((i * 13) % 23),
  y: 180 + Math.floor(i / 4) * 92 + ((i * 17) % 19),
  w: 160 + ((i * 37) % 40),
  delay: i * 2,
}));

const graphCards = [
  { id: "deploy", label: "Deployed to AWS", x: 160, y: 240, w: 250, center: false, rotate: -5, tiltX: 4, tiltY: -14, depth: 34 },
  { id: "error", label: "Error 500", x: 560, y: 190, w: 220, center: false, rotate: 4, tiltX: -3, tiltY: 12, depth: 48 },
  { id: "bill", label: "Billed $500", x: 610, y: 540, w: 220, center: false, rotate: 6, tiltX: 4, tiltY: 16, depth: 30 },
  { id: "user", label: "User Context", x: 300, y: 420, w: 260, center: true, rotate: -3, tiltX: 4, tiltY: -10, depth: 64 },
] as const;

const lineDefs = [
  { id: "owner", path: "M430 465 C370 370, 310 330, 280 285", label: "owner", lx: 285, ly: 333 },
  { id: "triggered", path: "M560 460 C625 425, 665 350, 670 270", label: "triggered_by", lx: 628, ly: 356 },
  { id: "impact", path: "M515 525 C570 590, 640 640, 705 640", label: "financial_impact", lx: 555, ly: 612 },
] as const;

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));
const wave = (frame: number, speed: number, amplitude: number, offset = 0) =>
  Math.sin(frame / speed + offset) * amplitude;

const cardShadow = "0 18px 48px rgba(15, 23, 42, 0.10)";
const focusShadow = "0 28px 72px rgba(15, 23, 42, 0.14)";

const scenePhase = (frame: number, start: number, end: number) => {
  const startFrame = start * FPS;
  const endFrame = end * FPS;
  const duration = endFrame - startFrame;
  const local = frame - startFrame;
  const enter = spring({
    frame: Math.max(0, local - 3),
    fps: FPS,
    config: { damping: 16, mass: 0.9, stiffness: 110 },
  });
  const fadeIn = interpolate(frame, [startFrame - 10, startFrame + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [endFrame - 14, endFrame + 8], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return {
    local,
    duration,
    progress: clamp(local / duration, 0, 1),
    opacity: fadeIn * fadeOut,
    enter,
  };
};

const HandleTag: React.FC = () => (
  <div
    style={{
      position: "absolute",
      bottom: 250,
      left: SAFE_CENTER_X - 156,
      width: 312,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 10,
      padding: "18px 24px",
      borderRadius: 999,
      border: `1px solid ${BORDER}`,
      background: "rgba(255,255,255,0.84)",
      boxShadow: "0 16px 40px rgba(15, 23, 42, 0.07)",
      color: MUTED,
      fontFamily: SANS,
      fontSize: 24,
      fontWeight: 600,
      letterSpacing: "-0.02em",
      zIndex: 50,
    }}
  >
    <div style={{ width: 8, height: 8, borderRadius: "50%", background: BLUE }} />
    <span>@ada.max24</span>
  </div>
);

const FloatingCard: React.FC<{
  x: number;
  y: number;
  w: number;
  label: string;
  opacity?: number;
  scale?: number;
  rotate?: number;
  tiltX?: number;
  tiltY?: number;
  depth?: number;
  shadow?: string;
  accent?: string;
}> = ({
  x,
  y,
  w,
  label,
  opacity = 1,
  scale = 1,
  rotate = 0,
  tiltX = 0,
  tiltY = 0,
  depth = 0,
  shadow = cardShadow,
  accent,
}) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: w,
      padding: "18px 20px",
      borderRadius: 24,
      background: SURFACE,
      border: `1px solid ${accent ?? BORDER}`,
      boxShadow: shadow,
      transformStyle: "preserve-3d",
      transformOrigin: "50% 50%",
      opacity,
      transform: `perspective(1400px) translateZ(${depth}px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) rotate(${rotate}deg) scale(${scale})`,
    }}
  >
    <div
      style={{
        fontFamily: SANS,
        color: TEXT,
        fontSize: 28,
        fontWeight: 580,
        letterSpacing: "-0.02em",
        lineHeight: 1.08,
      }}
    >
      {label}
    </div>
  </div>
);

const BackgroundLayer: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = wave(frame, 50, 24);
  const gridX = wave(frame, 80, 12);
  const gridY = wave(frame, 96, 10, 0.7);
  return (
    <AbsoluteFill
      style={{
        background: BG,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(17,17,17,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(17,17,17,0.035) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          opacity: 0.32,
          transform: `translate(${gridX}px, ${gridY}px)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 780,
          height: 780,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(37,99,255,0.10), rgba(37,99,255,0))",
          top: -110,
          left: 90 + drift,
          filter: "blur(10px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 540,
          height: 540,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(243,238,231,0.95), rgba(243,238,231,0))",
          bottom: -80,
          right: 20 - drift * 0.4,
          filter: "blur(12px)",
        }}
      />
    </AbsoluteFill>
  );
};

const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const phase = scenePhase(frame, SCENE_WINDOWS.problem.start, SCENE_WINDOWS.problem.end);
  const push = interpolate(phase.progress, [0, 1], [1.04, 0.98]);
  const sweepX = interpolate(phase.progress, [0, 1], [-34, 16]) + wave(frame, 42, 8);
  const sweepY = wave(frame, 34, 10, 0.4);
  const codeBlur = interpolate(phase.progress, [0.15, 0.62], [0, 10], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const outputProgress = spring({
    frame: Math.max(0, phase.local - 30),
    fps,
    config: { damping: 16, stiffness: 120, mass: 0.8 },
  });

  return (
    <AbsoluteFill
      style={{
        opacity: phase.opacity,
        transform: `translate(${sweepX}px, ${sweepY}px) scale(${push})`,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 76,
          right: 76,
          top: 180,
          height: 1160,
          borderRadius: 34,
          overflow: "hidden",
        }}
      >
        {memoryWallTiles.map((tile, i) => {
          const tileOpacity = interpolate(phase.local - tile.delay, [0, 36], [0.08, 0.42], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: tile.x,
                top: tile.y + wave(frame, 24, 5, i * 0.24),
                width: tile.w,
                height: 56,
                borderRadius: 16,
                background: "rgba(255,255,255,0.55)",
                border: `1px solid rgba(231,235,240,${tileOpacity})`,
                opacity: tileOpacity,
                boxShadow: "0 10px 30px rgba(15, 23, 42, 0.04)",
              }}
            />
          );
        })}

        <div
          style={{
            position: "absolute",
            left: 60,
            top: 188,
            padding: "28px 34px",
            borderRadius: 28,
            background: SURFACE,
            border: `1px solid ${BORDER}`,
            boxShadow: focusShadow,
            transform: `translateY(${interpolate(phase.enter, [0, 1], [42, 0])}px)`,
          }}
        >
          <div
            style={{
              fontFamily: MONO,
              fontSize: 30,
              color: TEXT,
              filter: `blur(${codeBlur}px)`,
            }}
          >
            vector_db.query("production error")
          </div>
        </div>

        {["[object Object]", "[object Object]", "[object Object]"].map((label, i) => (
          <div
            key={label + i}
            style={{
              position: "absolute",
              left: 110 + i * 220 + wave(frame, 45, 12, i),
              top: 470 + i * 24 + wave(frame, 26, 10, i * 0.8),
              width: 240,
              padding: "18px 22px",
              borderRadius: 22,
              background: "rgba(255,255,255,0.88)",
              border: `1px solid ${BORDER}`,
              boxShadow: cardShadow,
              opacity: outputProgress,
              transform: `translateY(${interpolate(outputProgress, [0, 1], [50, 0])}px) translateX(${interpolate(outputProgress, [0, 1], [-12 + i * 6, 0])}px) rotate(${i === 1 ? -2 : i === 2 ? 2 : 0}deg)`,
            }}
          >
            <div style={{ fontFamily: MONO, fontSize: 24, color: MUTED }}>{label}</div>
          </div>
        ))}

        <div
          style={{
            position: "absolute",
            left: 70,
            bottom: 140,
            maxWidth: 620,
            fontFamily: SANS,
            fontSize: 86,
            fontWeight: 650,
            lineHeight: 0.96,
            letterSpacing: "-0.05em",
            color: TEXT,
          }}
        >
          Still making things up?
        </div>
      </div>
    </AbsoluteFill>
  );
};

const IsolationScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const phase = scenePhase(frame, SCENE_WINDOWS.isolation.start, SCENE_WINDOWS.isolation.end);
  const spread = interpolate(phase.progress, [0.1, 0.85], [40, 150], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const bob = wave(frame, 18, 8);
  const intro = spring({
    frame: Math.max(0, phase.local - 4),
    fps,
    config: { damping: 14, stiffness: 110, mass: 0.85 },
  });
  const driftX = interpolate(phase.progress, [0, 1], [22, -18]) + wave(frame, 52, 10);
  const driftY = wave(frame, 40, 12, 0.3);

  return (
    <AbsoluteFill style={{ opacity: phase.opacity }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `translate(${driftX}px, ${interpolate(intro, [0, 1], [40, 0]) + driftY}px) scale(${interpolate(phase.progress, [0, 1], [1.02, 1])})`,
        }}
      >
        <FloatingCard x={110 - spread * 0.28 + wave(frame, 44, 10, 0.4)} y={520 + bob} w={280} label="Deployed to AWS" rotate={-5} tiltX={4} tiltY={-12} depth={26} />
        <FloatingCard x={332 + wave(frame, 36, 8, 1.2)} y={398 - bob * 0.5 - wave(frame, 32, 10, 0.8)} w={250} label="Error 500" rotate={1.5} tiltX={-2} tiltY={8} depth={34} shadow={focusShadow} />
        <FloatingCard x={542 + spread * 0.38 + wave(frame, 48, 12, 2)} y={578 + bob * 0.3 + wave(frame, 34, 8, 1.5)} w={220} label="Billed $500" rotate={4} tiltX={3} tiltY={10} depth={24} />
      </div>
    </AbsoluteFill>
  );
};

const GraphWorld: React.FC<{
  connect: number;
  meta: number;
  orbit: number;
  focusError?: boolean;
}> = ({ connect, meta, orbit, focusError = false }) => {
  const frame = useCurrentFrame();
  const baseScale = 0.88;
  const focusScale = focusError ? 1.04 : 1;
  const worldX = wave(frame, 58, 10, 0.3);
  const worldY = wave(frame, 42, 12, 0.8);
  return (
    <div
      style={{
        position: "absolute",
        left: SAFE_LEFT + 12,
        top: SAFE_TOP + 70,
        width: 760,
        height: 760,
        transform: `translate(${worldX}px, ${worldY}px) perspective(1400px) rotateY(${orbit}deg) rotateX(${wave(frame, 80, 1.5)}deg) scale(${baseScale * focusScale})`,
        transformOrigin: "0 0",
        transformStyle: "preserve-3d",
      }}
    >
      <svg
        width="760"
        height="760"
        style={{ position: "absolute", inset: 0, overflow: "visible" }}
      >
        {lineDefs.map((line, index) => {
          const lineProgress = clamp((connect - lineDefs.findIndex((entry) => entry.id === line.id) * 0.17) / 0.5, 0, 1);
          const dashOffset = 380 - 380 * lineProgress;
          return (
            <g key={line.id}>
              <path
                d={line.path}
                fill="none"
                stroke={BLUE}
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray="380"
                strokeDashoffset={dashOffset}
                opacity={0.95}
              />
              <foreignObject x={line.lx} y={line.ly + wave(frame, 34, 4, index * 0.9)} width="190" height="52" opacity={clamp((meta - 0.18) / 0.4, 0, 1)}>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    height: 44,
                    padding: "0 14px",
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.92)",
                    border: `1px solid ${BORDER}`,
                    boxShadow: "0 12px 28px rgba(15, 23, 42, 0.08)",
                    fontFamily: MONO,
                    fontSize: 18,
                    color: BLUE,
                  }}
                >
                  {line.label}
                </div>
              </foreignObject>
            </g>
          );
        })}
        <circle
          cx="430"
          cy="465"
          r={String(interpolate(connect, [0, 1], [20, 250]) + wave(frame, 20, 5))}
          fill="none"
          stroke={BLUE}
          strokeWidth="3"
          opacity={interpolate(connect, [0, 0.2, 0.7], [0, 0.45, 0])}
        />
      </svg>

      {graphCards.map((card, index) => (
        <FloatingCard
          key={card.id}
          x={card.x + wave(frame, 46, 10, index)}
          y={card.y + wave(frame, 28, 12, index * 0.75)}
          w={card.w}
          label={card.label}
          rotate={card.rotate + wave(frame, 88, 0.8, index)}
          tiltX={card.tiltX + wave(frame, 110, 0.9, index * 0.4)}
          tiltY={card.tiltY + wave(frame, 96, 1.2, index * 0.3)}
          depth={card.depth + wave(frame, 75, 6, index)}
          shadow={card.center ? focusShadow : cardShadow}
          accent={card.center ? "rgba(37,99,255,0.32)" : undefined}
          scale={card.id === "error" && focusError ? 1.05 : 1 + wave(frame, 90, 0.01, index)}
        />
      ))}

      {meta > 0.05 ? (
        <>
          <div
            style={{
              position: "absolute",
              left: 522,
              top: 90 + wave(frame, 40, 5),
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 16px",
              borderRadius: 999,
              background: SURFACE,
              border: `1px solid ${BORDER}`,
              boxShadow: cardShadow,
              opacity: clamp((meta - 0.15) / 0.3, 0, 1),
              fontFamily: MONO,
              fontSize: 18,
              color: TEXT,
            }}
          >
            <span style={{ color: BLUE }}>03:00 AM</span>
          </div>
          <div
            style={{
              position: "absolute",
              left: 615,
              top: 470 + wave(frame, 33, 5, 0.8),
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 16px",
              borderRadius: 999,
              background: SURFACE,
              border: `1px solid ${BORDER}`,
              boxShadow: cardShadow,
              opacity: clamp((meta - 0.28) / 0.3, 0, 1),
              fontFamily: MONO,
              fontSize: 18,
              color: TEXT,
            }}
          >
            <span style={{ color: RED }}>Production</span>
          </div>
          <div
            style={{
              position: "absolute",
              left: 540,
              top: 715 + wave(frame, 37, 5, 1.3),
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 16px",
              borderRadius: 999,
              background: SURFACE,
              border: `1px solid ${BORDER}`,
              boxShadow: cardShadow,
              opacity: clamp((meta - 0.38) / 0.3, 0, 1),
              fontFamily: MONO,
              fontSize: 18,
              color: TEXT,
            }}
          >
            <span style={{ color: GREEN }}>Retry Loop</span>
          </div>
        </>
      ) : null}
    </div>
  );
};

const ConnectionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const phase = scenePhase(frame, SCENE_WINDOWS.connection.start, SCENE_WINDOWS.connection.end);
  const connect = spring({
    frame: Math.max(0, phase.local - 12),
    fps: FPS,
    config: { damping: 16, stiffness: 90, mass: 0.9 },
  });

  return (
    <AbsoluteFill style={{ opacity: phase.opacity }}>
      <GraphWorld connect={connect} meta={0.12} orbit={-6 + connect * 4} />
    </AbsoluteFill>
  );
};

const IntelligenceScene: React.FC = () => {
  const frame = useCurrentFrame();
  const phase = scenePhase(frame, SCENE_WINDOWS.intelligence.start, SCENE_WINDOWS.intelligence.end);
  const connect = 1;
  const meta = spring({
    frame: Math.max(0, phase.local - 10),
    fps: FPS,
    config: { damping: 16, stiffness: 80, mass: 1 },
  });

  return (
    <AbsoluteFill style={{ opacity: phase.opacity }}>
      <GraphWorld connect={connect} meta={meta} orbit={interpolate(phase.progress, [0, 1], [-3, 7])} />
    </AbsoluteFill>
  );
};

const DiagnosisScene: React.FC = () => {
  const frame = useCurrentFrame();
  const phase = scenePhase(frame, SCENE_WINDOWS.diagnosis.start, SCENE_WINDOWS.diagnosis.end);
  const zoom = interpolate(phase.progress, [0, 1], [1.08, 1]);
  const focusX = interpolate(phase.progress, [0, 1], [24, -12]) + wave(frame, 44, 8);
  const split = spring({
    frame: Math.max(0, phase.local - 16),
    fps: FPS,
    config: { damping: 15, stiffness: 110, mass: 0.9 },
  });

  return (
    <AbsoluteFill style={{ opacity: phase.opacity }}>
      <div
        style={{
          position: "absolute",
          left: SAFE_LEFT - 4,
          right: SAFE_RIGHT + 6,
          top: SAFE_TOP + 18,
          bottom: SAFE_BOTTOM + 120,
          transform: `translateX(${focusX}px) scale(${zoom})`,
        }}
      >
        <GraphWorld connect={1} meta={0.72} orbit={8} focusError />
      </div>

      <div
        style={{
          position: "absolute",
          left: SAFE_LEFT + 6,
          right: SAFE_RIGHT + 8,
          bottom: SAFE_BOTTOM + 30,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 18,
          opacity: split,
          transform: `translateY(${interpolate(split, [0, 1], [48, 0])}px)`,
        }}
      >
        <div
          style={{
            borderRadius: 30,
            padding: "28px 28px 32px",
            background: "rgba(255,255,255,0.82)",
            border: `1px solid ${BORDER}`,
            boxShadow: cardShadow,
            transform: `perspective(1400px) rotateY(7deg) rotateX(1.5deg) translateY(${wave(frame, 52, 4, 0.4)}px)`,
            transformOrigin: "50% 50%",
          }}
        >
          <div style={{ fontFamily: SANS, fontSize: 24, fontWeight: 560, color: MUTED }}>Minor log</div>
          <div
            style={{
              marginTop: 22,
              fontFamily: SANS,
              fontSize: 68,
              fontWeight: 620,
              lineHeight: 0.94,
              letterSpacing: "-0.05em",
              color: "#B8C0C7",
            }}
          >
            ignore
          </div>
        </div>

        <div
          style={{
            borderRadius: 30,
            padding: "28px 28px 32px",
            background: SURFACE,
            border: "1px solid rgba(229,72,77,0.28)",
            boxShadow: focusShadow,
            position: "relative",
            transform: `perspective(1400px) rotateY(-8deg) rotateX(1.8deg) translateY(${wave(frame, 48, 4, 1.2)}px)`,
            transformOrigin: "50% 50%",
          }}
        >
          <div style={{ fontFamily: SANS, fontSize: 24, fontWeight: 560, color: MUTED }}>3 A.M. incident</div>
          <div
            style={{
              marginTop: 22,
              fontFamily: SANS,
              fontSize: 68,
              fontWeight: 650,
              lineHeight: 0.94,
              letterSpacing: "-0.05em",
              color: TEXT,
            }}
          >
            SEV-1
          </div>
          <div
            style={{
              marginTop: 20,
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 16px",
              borderRadius: 999,
              background: "rgba(22,163,74,0.10)",
              color: GREEN,
              fontFamily: MONO,
              fontSize: 18,
              fontWeight: 600,
            }}
          >
            ✓ correct path
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const SolutionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const phase = scenePhase(frame, SCENE_WINDOWS.solution.start, SCENE_WINDOWS.solution.end);
  const local = Math.max(0, phase.local);
  const command = "npm install @mem0/memory";
  const typedChars = clamp(Math.floor((local - 26) / 2.1), 0, command.length);
  const typed = command.slice(0, typedChars);
  const progress = clamp((local - 92) / 60, 0, 1);
  const lockup = interpolate(local, [120, 180], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: phase.opacity }}>
      <div
        style={{
          position: "absolute",
          left: SAFE_LEFT + 8,
          right: SAFE_RIGHT + 10,
          top: SAFE_TOP + 170,
          borderRadius: 34,
          background: SURFACE,
          border: `1px solid ${BORDER}`,
          boxShadow: focusShadow,
          overflow: "hidden",
          transform: `translate(${wave(frame, 54, 8)}px, ${interpolate(phase.enter, [0, 1], [42, 0]) + wave(frame, 36, 8)}px) scale(${interpolate(phase.progress, [0, 1], [0.98, 1.01])})`,
        }}
      >
        <div
          style={{
            height: 62,
            borderBottom: `1px solid ${BORDER}`,
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "0 22px",
            background: "rgba(247,247,244,0.88)",
          }}
        >
          {["#FF5F57", "#FEBC2E", "#28C840"].map((color) => (
            <div key={color} style={{ width: 12, height: 12, borderRadius: "50%", background: color }} />
          ))}
        </div>

        <div
          style={{
            padding: "34px 36px 42px",
            fontFamily: MONO,
            fontSize: 30,
            color: TEXT,
            minHeight: 420,
          }}
        >
          <div style={{ color: BLUE }}>
            $ <span style={{ color: TEXT }}>{typed}</span>
            <span style={{ opacity: typedChars < command.length ? 1 : 0 }}>_</span>
          </div>

          <div
            style={{
              marginTop: 38,
              height: 14,
              borderRadius: 999,
              background: "#EEF2F6",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${progress * 100}%`,
                height: "100%",
                background: BLUE,
                borderRadius: 999,
              }}
            />
          </div>

          <div
            style={{
              marginTop: 24,
              opacity: progress > 0.96 ? 1 : 0,
              color: GREEN,
            }}
          >
            ✓ Installed
          </div>
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: SAFE_LEFT + 10,
          right: SAFE_RIGHT + 10,
          bottom: SAFE_BOTTOM + 48,
          textAlign: "center",
          opacity: lockup,
        }}
      >
        <div
          style={{
            fontFamily: SANS,
            fontSize: 86,
            fontWeight: 650,
            lineHeight: 0.96,
            letterSpacing: "-0.05em",
            color: TEXT,
          }}
        >
          Memory with structure.
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const MemoryWallReelConfig = {
  durationInFrames: TOTAL_SECONDS * FPS,
  fps: FPS,
  width: 1080,
  height: 1920,
};

export const MemoryWallReelDefaultProps = {
  audioSrc: "memory_wall_narration_v3.wav",
  totalFrames: TOTAL_SECONDS * FPS,
};

export const MemoryWallReel: React.FC<{ audioSrc: string }> = ({ audioSrc }) => {
  return (
    <AbsoluteFill style={{ background: BG }}>
      <BackgroundLayer />
      <Audio src={staticFile(audioSrc)} />
      <HandleTag />
      <ProblemScene />
      <IsolationScene />
      <ConnectionScene />
      <IntelligenceScene />
      <DiagnosisScene />
      <SolutionScene />
    </AbsoluteFill>
  );
};
