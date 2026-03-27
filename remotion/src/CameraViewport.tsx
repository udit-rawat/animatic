/**
 * CameraViewport.tsx — Infinite canvas + spring camera system (Phase 2)
 *
 * Component tree:
 *   <CameraViewport timing={timing} totalBeats={n}>   ← clips to 1080×1920, drives camera
 *     <VirtualCanvas totalBeats={n}>                  ← 1080 × (n × 1920) absolute canvas
 *       <BeatZone index={0} beatStartFrame={0}>        ← positioned at y=0, frame ctx
 *       <BeatZone index={1} beatStartFrame={330}>      ← positioned at y=1920, frame ctx
 *       ...
 *     </VirtualCanvas>
 *   </CameraViewport>
 *
 * CameraVelocityContext is exposed for Phase 4's <CRTWrapper> to gate
 * chromatic aberration on |cameraVelocity| > 15px/frame.
 */

import React, { createContext, useContext } from "react";
import type { TimingEntry } from "./types";
import { useCameraY } from "./hooks/useCameraY";
import { BeatFrameContext } from "./hooks/useBeatFrame";

// ── Camera velocity context (consumed by CRTWrapper in Phase 4) ───────────────

interface CameraVelocityContextValue {
  cameraVelocity: number;
}

export const CameraVelocityContext = createContext<CameraVelocityContextValue>({
  cameraVelocity: 0,
});

export function useCameraVelocity(): number {
  return useContext(CameraVelocityContext).cameraVelocity;
}

// ── CameraViewport ────────────────────────────────────────────────────────────

interface CameraViewportProps {
  totalBeats: number;
  timing: Record<string, TimingEntry>;
  children: React.ReactNode;
}

/**
 * Overflow-hidden viewport that translates its VirtualCanvas child by -cameraY.
 * Exposes cameraVelocity via context for CRT aberration gating (Phase 4).
 */
export const CameraViewport: React.FC<CameraViewportProps> = ({
  totalBeats,
  timing,
  children,
}) => {
  const { cameraY, cameraVelocity } = useCameraY(timing, totalBeats);

  return (
    <CameraVelocityContext.Provider value={{ cameraVelocity }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            transform: `translateY(-${cameraY}px)`,
          }}
        >
          {children}
        </div>
      </div>
    </CameraVelocityContext.Provider>
  );
};

// ── VirtualCanvas ─────────────────────────────────────────────────────────────

interface VirtualCanvasProps {
  totalBeats: number;
  children: React.ReactNode;
}

/**
 * Full-width canvas sized to fit all beats stacked vertically.
 * Height = totalBeats × 1920px.
 */
export const VirtualCanvas: React.FC<VirtualCanvasProps> = ({
  totalBeats,
  children,
}) => (
  <div
    style={{
      position: "relative",
      width: "100%",
      height: totalBeats * 1920,
    }}
  >
    {children}
  </div>
);

// ── BeatZone ──────────────────────────────────────────────────────────────────

interface BeatZoneProps {
  /** 0-based index on the virtual canvas (y = index × 1920) */
  index: number;
  /** Global frame at which this beat's narration starts — provides local frame context */
  beatStartFrame: number;
  children: React.ReactNode;
}

/**
 * Positions one beat at its y-slot on the VirtualCanvas and provides
 * BeatFrameContext so LayoutRenderer animated nodes see beat-local frames.
 */
export const BeatZone: React.FC<BeatZoneProps> = ({
  index,
  beatStartFrame,
  children,
}) => (
  <BeatFrameContext.Provider value={{ beatStartFrame }}>
    <div
      style={{
        position: "absolute",
        top: index * 1920,
        left: 0,
        width: "100%",
        height: 1920,
        background: "#0B0E14",
        overflow: "hidden",
        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
      }}
    >
      {children}
    </div>
  </BeatFrameContext.Provider>
);
