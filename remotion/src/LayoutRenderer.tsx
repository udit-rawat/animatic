/**
 * LayoutRenderer.tsx — Recursive LayoutNode renderer (Motion Design v2 — Phase 0)
 *
 * Replaces the fixed BeatRouter + individual beat files (Phase 1 will delete those).
 * Phase 0 scope: full container support + key primitives for gate test.
 *   Implemented: column, row, grid, Spacer, Divider, Chip
 *                TerminalPrompt, TerminalText, StatBox, LabelValueCard, CodeBlock
 *
 * Usage:
 *   <LayoutRenderer node={beatLayout.layout} />
 */

import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import type { LayoutNode, NodeColor, NodeSize } from "./types";
import { useBeatFrame } from "./hooks/useBeatFrame";

// ── Design tokens ──────────────────────────────────────────────────────────────

const COLOR_MAP: Record<NodeColor, string> = {
  green:  "#10B981",   // emerald  — positive metrics
  cyan:   "#6366F1",   // indigo   — primary accent / neutral info
  yellow: "#8B5CF6",   // violet   — section labels / headers
  red:    "#EF4444",   // red      — negative / bottleneck
  white:  "#F9FAFB",   // off-white — main body text
};

const SIZE_MAP: Record<NodeSize, number> = {
  xs: 36,
  sm: 48,
  md: 64,
  lg: 90,
  xl: 120,
};

function color(c: NodeColor | undefined, fallback: NodeColor = "white"): string {
  return COLOR_MAP[c ?? fallback];
}

// ── Root dispatcher ────────────────────────────────────────────────────────────

export const LayoutRenderer: React.FC<{ node: LayoutNode }> = ({ node }) => {
  switch (node.type) {
    // Containers
    case "column":        return <ColumnNode node={node} />;
    case "row":           return <RowNode node={node} />;
    case "grid":          return <GridNode node={node} />;
    // Structural primitives
    case "Spacer":        return <SpacerNode node={node} />;
    case "Divider":       return <DividerNode node={node} />;
    case "Chip":          return <ChipNode node={node} />;
    // Content primitives (animated)
    case "TerminalPrompt": return <TerminalPromptNode node={node} />;
    case "TerminalText":  return <TerminalTextNode node={node} />;
    case "StatBox":       return <StatBoxNode node={node} />;
    case "LabelValueCard": return <LabelValueCardNode node={node} />;
    case "CodeBlock":     return <CodeBlockNode node={node} />;
    default:
      return null;
  }
};

// ── Containers ─────────────────────────────────────────────────────────────────

const ColumnNode: React.FC<{ node: LayoutNode }> = ({ node }) => (
  <div style={{
    display: "flex",
    flexDirection: "column",
    gap: node.gap ?? 24,
    justifyContent: node.justify ?? "flex-start",
    alignItems: node.align ?? "flex-start",
    padding: node.padding ?? 0,
    width: "100%",
    height: "100%",
    boxSizing: "border-box",
  }}>
    {node.children?.map((child, i) => (
      <LayoutRenderer key={i} node={child} />
    ))}
  </div>
);

const RowNode: React.FC<{ node: LayoutNode }> = ({ node }) => (
  <div style={{
    display: "flex",
    flexDirection: "row",
    gap: node.gap ?? 24,
    justifyContent: node.justify ?? "flex-start",
    alignItems: node.align ?? "flex-start",
    padding: node.padding ?? 0,
    width: "100%",
    boxSizing: "border-box",
  }}>
    {node.children?.map((child, i) => (
      <LayoutRenderer key={i} node={child} />
    ))}
  </div>
);

const GridNode: React.FC<{ node: LayoutNode }> = ({ node }) => (
  <div style={{
    display: "grid",
    gridTemplateColumns: `repeat(${node.columns ?? 2}, 1fr)`,
    gap: node.gap ?? 24,
    padding: node.padding ?? 0,
    width: "100%",
    boxSizing: "border-box",
  }}>
    {node.children?.map((child, i) => (
      <LayoutRenderer key={i} node={child} />
    ))}
  </div>
);

// ── Structural primitives ──────────────────────────────────────────────────────

const SpacerNode: React.FC<{ node: LayoutNode }> = ({ node }) => (
  <div style={{
    height: typeof node.size === "number" ? node.size : 24,
    flexShrink: 0,
  }} />
);

const DividerNode: React.FC<{ node: LayoutNode }> = ({ node }) => (
  <div style={{
    width: "100%",
    height: 2,
    background: color(node.color, "white"),
    opacity: node.opacity ?? 0.25,
    flexShrink: 0,
  }} />
);

const ChipNode: React.FC<{ node: LayoutNode }> = ({ node }) => {
  const chipColor = color(node.color, "cyan");
  return (
    <span style={{
      display: "inline-block",
      background: `${chipColor}14`,
      border: `1px solid ${chipColor}40`,
      color: chipColor,
      padding: "8px 20px",
      borderRadius: 100,
      fontSize: 30,
      fontWeight: 500,
      fontFamily: "'Inter', 'system-ui', sans-serif",
      letterSpacing: "0.06em",
    }}>
      {node.text}
    </span>
  );
};

// ── Content primitives ─────────────────────────────────────────────────────────

/** Section identifier — uppercase micro-label in indigo, no animation */
const TerminalPromptNode: React.FC<{ node: LayoutNode }> = ({ node }) => (
  <div style={{
    fontSize: 22,
    fontWeight: 500,
    color: COLOR_MAP.cyan,
    fontFamily: "'Inter', 'system-ui', sans-serif",
    letterSpacing: "0.15em",
    textTransform: "uppercase",
    opacity: 0.7,
    flexShrink: 0,
  }}>
    {node.text ?? "adamax.ai"}
  </div>
);

/**
 * TerminalText — typewriter reveal + optional blinking cursor.
 *   typewriter: true  → reveal chars at 1.5 chars/frame starting at `delay` frame
 *   cursor: true      → show blinking "_" after typewriter completes
 */
const TerminalTextNode: React.FC<{ node: LayoutNode }> = ({ node }) => {
  const frame = useBeatFrame();
  const text      = node.text ?? "";
  const delay     = node.delay ?? 0;
  const fontSize  = typeof node.size === "number" ? node.size : SIZE_MAP[node.size ?? "md"];
  const textColor = color(node.color, "white");

  const CHARS_PER_FRAME = 1.5;

  const charsVisible = node.typewriter
    ? Math.floor(
        interpolate(
          frame,
          [delay, delay + text.length / CHARS_PER_FRAME],
          [0, text.length],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        )
      )
    : text.length;

  const typewriterDone = charsVisible >= text.length;
  const cursorOn = node.cursor && typewriterDone && Math.floor(frame / 15) % 2 === 0;

  return (
    <div style={{
      fontSize,
      color: textColor,
      lineHeight: 1.3,
      maxWidth: "100%",
      whiteSpace: "pre-wrap",
      wordBreak: "break-word",
      fontFamily: "'Inter', 'system-ui', sans-serif",
      fontWeight: 400,
    }}>
      {text.slice(0, charsVisible)}
      {node.cursor && (
        <span style={{
          color: COLOR_MAP.cyan,
          opacity: cursorOn ? 1 : 0,
        }}>
          |
        </span>
      )}
    </div>
  );
};

/**
 * StatBox — hero metric display.
 * Overdamped spring scale 0.5→1.0 starting at `delay` frame.
 */
const StatBoxNode: React.FC<{ node: LayoutNode }> = ({ node }) => {
  const frame = useBeatFrame();
  const { fps } = useVideoConfig();
  const delay     = node.delay ?? 0;
  const statColor = color(node.color, "green");

  const progress = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: { damping: 200, stiffness: 380, overshootClamping: true },
  });

  const scale   = interpolate(progress, [0, 1], [0.5, 1.0]);
  const opacity = interpolate(progress, [0, 0.1], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{ opacity, transform: `scale(${scale})`, transformOrigin: "left center" }}>
      <div style={{
        fontSize: 240,
        fontWeight: "bold",
        color: statColor,
        lineHeight: 1,
        fontFamily: "'Inter', 'system-ui', sans-serif",
        textShadow: `0 0 60px ${statColor}30`,
      }}>
        {node.value}
      </div>
      {node.label && (
        <div style={{
          fontSize: 48,
          color: COLOR_MAP.white,
          opacity: 0.55,
          marginTop: 8,
          fontFamily: "'Inter', 'system-ui', sans-serif",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}>
          {node.label}
        </div>
      )}
    </div>
  );
};

/**
 * LabelValueCard — bordered card with slide-up spring animation.
 * Stagger via `delay` prop (frame offset).
 */
const LabelValueCardNode: React.FC<{ node: LayoutNode }> = ({ node }) => {
  const frame = useBeatFrame();
  const { fps } = useVideoConfig();
  const delay       = node.delay ?? 0;
  const borderColor = color(node.border_color, "cyan");
  const valueColor  = color(node.color, "cyan");

  const progress = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: { damping: 200, stiffness: 380, overshootClamping: true },
  });

  const opacity    = interpolate(progress, [0, 0.1], [0, 1], { extrapolateRight: "clamp" });
  const translateY = interpolate(progress, [0, 1], [20, 0]);

  // Glassmorphism card: semi-transparent fill + low-opacity border tinted by accent color
  const accentHex = borderColor; // e.g. "#6366F1"
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: `1px solid ${accentHex}40`,
      padding: "28px 36px",
      borderRadius: 12,
      opacity,
      transform: `translateY(${translateY}px)`,
      boxShadow: node.glow ? `0 0 24px ${accentHex}18` : undefined,
      boxSizing: "border-box",
      flex: 1,
    }}>
      <div style={{
        fontSize: 28,
        fontWeight: 500,
        color: COLOR_MAP.white,
        opacity: 0.45,
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        fontFamily: "'Inter', 'system-ui', sans-serif",
        marginBottom: 8,
      }}>
        {node.label}
      </div>
      <div style={{
        fontSize: 68,
        color: valueColor,
        fontWeight: 700,
        lineHeight: 1.1,
        fontFamily: "'Inter', 'system-ui', sans-serif",
        letterSpacing: "-0.02em",
      }}>
        {node.value}
      </div>
    </div>
  );
};

/** CodeBlock — code display block with optional line highlight */
const CodeBlockNode: React.FC<{ node: LayoutNode }> = ({ node }) => (
  <pre style={{
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
    fontSize: SIZE_MAP.sm,
    color: COLOR_MAP.white,
    background: "rgba(255,255,255,0.03)",
    padding: 28,
    borderRadius: 12,
    margin: 0,
    overflowX: "hidden",
    border: "1px solid rgba(255,255,255,0.06)",
    width: "100%",
    boxSizing: "border-box",
  }}>
    {node.lines?.map((line, i) => (
      <div
        key={i}
        style={{
          color: i === node.highlight_line ? COLOR_MAP.yellow : COLOR_MAP.white,
          background: i === node.highlight_line ? `${COLOR_MAP.yellow}12` : undefined,
          padding: i === node.highlight_line ? "2px 8px" : "2px 0",
          borderRadius: i === node.highlight_line ? 4 : undefined,
          opacity: i === node.highlight_line ? 1 : 0.65,
        }}
      >
        {line}
      </div>
    ))}
  </pre>
);
