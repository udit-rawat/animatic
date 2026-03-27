/**
 * Beat4Takeaway — Closing takeaway (terminal typewriter)
 *
 * Fast typewriter reveal left-aligned at the terminal anchor.
 * After reveal: blinking cursor. Screen never static.
 *
 * Mirrors the Python beat4_takeaway.py AddTextLetterByLetter aesthetic
 * using per-character frame interpolation.
 */
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

const LEFT    = 50;
const C_WHITE = "#FDFDFD";
const C_GREEN = "#00FF41";

// "> " prefix marks it as terminal output, matching the Python FS_TAKEAWAY style
const PROMPT_PREFIX = "> ";

interface Props { params: { template: "takeaway"; takeaway_text: string } }

export const Beat4Takeaway: React.FC<Props> = ({ params }) => {
  const frame = useCurrentFrame();

  const fullText  = params.takeaway_text;
  const totalText = PROMPT_PREFIX + fullText;

  // Typewriter: ~1.5 chars per frame → full reveal in ~text.length/1.5 frames
  const CHARS_PER_FRAME = 1.5;
  const charsVisible    = Math.floor(
    interpolate(frame, [0, totalText.length / CHARS_PER_FRAME], [0, totalText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );
  const visibleText  = totalText.slice(0, charsVisible);
  const typewriterDone = charsVisible >= totalText.length;

  // Blinking cursor after reveal
  const BLINK_INTERVAL = 15;
  const cursorOn = typewriterDone && (Math.floor(frame / BLINK_INTERVAL) % 2 === 0);

  // Subtle overall opacity fade-in (first 8 frames)
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{
      position: "relative",
      width: "100%",
      height: "100%",
      fontFamily: "inherit",
      display: "flex",
      alignItems: "center",
    }}>
      <div style={{
        position: "absolute",
        left: LEFT,
        right: LEFT,
        top: "30%",
        opacity,
      }}>
        {/* Terminal prompt line above takeaway */}
        <div style={{
          fontSize: 44,
          color: C_GREEN,
          marginBottom: 24,
          letterSpacing: "0.02em",
          opacity: 0.7,
        }}>
          user@adamax:~$
        </div>

        {/* Takeaway text — large typewriter */}
        <div style={{
          fontSize: 100,
          color: C_WHITE,
          lineHeight: 1.3,
          letterSpacing: "0.01em",
          whiteSpace: "pre-wrap",
        }}>
          <span style={{ color: C_GREEN }}>{visibleText.slice(0, PROMPT_PREFIX.length)}</span>
          {visibleText.slice(PROMPT_PREFIX.length)}
          <span style={{ color: C_GREEN, opacity: cursorOn ? 1 : 0 }}>_</span>
        </div>
      </div>
    </div>
  );
};
