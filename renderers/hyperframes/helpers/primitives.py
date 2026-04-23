"""
HyperFrames helper primitives for Phase 3 preview output.

These are plain HTML/CSS/JS helpers, not React hooks. The current runtime is a
local preview surface, but the naming mirrors the motion concepts already used
in the Remotion renderer so scene modules can share one visual vocabulary.
"""

from __future__ import annotations

from html import escape


PRIMITIVE_IDS = ["pulse", "slide_in", "highlight", "count_up", "breath", "cue_seek"]


def e(text: object) -> str:
    return escape("" if text is None else str(text), quote=True)


def html_list(tag: str, items: list[str], class_name: str = "") -> str:
    cls = f' class="{e(class_name)}"' if class_name else ""
    return f"<{tag}{cls}>" + "".join(items) + f"</{tag}>"


def runtime_css() -> str:
    return """
:root {
  --hf-bg: #06070a;
  --hf-panel: rgba(255,255,255,0.06);
  --hf-border: rgba(255,255,255,0.12);
  --hf-text: #f8fafc;
  --hf-muted: rgba(248,250,252,0.72);
  --hf-cyan: #00e5ff;
  --hf-green: #10b981;
  --hf-yellow: #f59e0b;
  --hf-red: #ef4444;
  --hf-white: #ffffff;
  --hf-radius: 26px;
  --hf-shadow: 0 20px 80px rgba(0,0,0,0.32);
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #040408;
  color: var(--hf-text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}
body {
  min-height: 100vh;
  display: grid;
  place-items: center;
}
.hf-root {
  position: relative;
  width: 1080px;
  height: 1920px;
  overflow: hidden;
  background: radial-gradient(circle at top, #10172a 0%, #06070a 52%, #040408 100%);
}
.hf-stage {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.hf-beat {
  position: absolute;
  inset: 0;
  min-height: 100%;
  overflow: hidden;
  border-radius: 0;
  border: 0;
  background:
    radial-gradient(circle at 20% 12%, rgba(0,229,255,0.14), transparent 28%),
    radial-gradient(circle at 88% 22%, rgba(16,185,129,0.10), transparent 24%),
    linear-gradient(180deg, rgba(17,24,39,0.92), rgba(6,7,10,0.96));
  box-shadow: none;
  padding: 96px 72px;
}
.hf-beat[data-layout-mode="caption_overlay"] {
  padding-top: 620px;
}
.hf-beat[data-layout-mode="transparent_overlay"] {
  background: linear-gradient(180deg, rgba(17,24,39,0.45), rgba(6,7,10,0.72));
}
.hf-beat-meta {
  position: absolute;
  top: 36px;
  right: 36px;
  color: rgba(248,250,252,0.56);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.hf-section-label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--hf-cyan);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin-bottom: 24px;
}
.hf-section-label::before {
  content: "";
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
}
.hf-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 26px;
}
.hf-chip {
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  color: rgba(248,250,252,0.9);
  padding: 10px 16px;
  border-radius: 999px;
  font-size: 15px;
}
.hf-hero {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}
.hf-hero-value {
  font-size: clamp(72px, 9vw, 132px);
  font-weight: 800;
  line-height: 0.92;
  letter-spacing: -0.05em;
}
.hf-hero-label {
  color: var(--hf-muted);
  font-size: 22px;
  letter-spacing: 0.02em;
}
.hf-context {
  margin-top: 22px;
  max-width: 760px;
  color: rgba(248,250,252,0.84);
  font-size: 24px;
  line-height: 1.35;
}
.hf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin-top: 20px;
}
.hf-card {
  border-radius: 22px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  padding: 20px 22px;
  min-height: 148px;
}
.hf-card[data-highlight="true"] {
  border-color: rgba(0,229,255,0.44);
  box-shadow: 0 0 0 1px rgba(0,229,255,0.12), 0 0 28px rgba(0,229,255,0.12);
}
.hf-card-label {
  color: rgba(248,250,252,0.62);
  font-size: 14px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.hf-card-value {
  margin-top: 12px;
  font-size: clamp(34px, 4vw, 58px);
  line-height: 0.94;
  font-weight: 800;
  letter-spacing: -0.04em;
}
.hf-card-caption {
  margin-top: 10px;
  color: rgba(248,250,252,0.72);
  font-size: 16px;
  line-height: 1.3;
}
.hf-split {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: stretch;
  margin-top: 22px;
}
.hf-panel {
  border-radius: 24px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  padding: 22px;
}
.hf-panel[data-highlight="true"] {
  border-color: rgba(16,185,129,0.42);
  box-shadow: 0 0 0 1px rgba(16,185,129,0.14), 0 0 28px rgba(16,185,129,0.10);
}
.hf-panel-heading {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 18px;
}
.hf-divider-badge {
  align-self: center;
  padding: 10px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  color: rgba(248,250,252,0.58);
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.hf-bar-list {
  display: grid;
  gap: 18px;
  margin-top: 20px;
}
.hf-bar-row {
  display: grid;
  gap: 8px;
}
.hf-bar-topline {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: baseline;
}
.hf-bar-label {
  font-size: 18px;
  color: rgba(248,250,252,0.84);
}
.hf-bar-value {
  font-size: 16px;
  color: rgba(248,250,252,0.68);
}
.hf-bar-track {
  height: 18px;
  border-radius: 999px;
  background: rgba(255,255,255,0.07);
  overflow: hidden;
}
.hf-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(0,229,255,0.88), rgba(16,185,129,0.88));
  box-shadow: 0 0 24px rgba(0,229,255,0.16);
}
.hf-flow {
  display: grid;
  gap: 18px;
  margin-top: 22px;
}
.hf-step {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  align-items: center;
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  padding: 18px 20px;
}
.hf-step-index {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.08);
  color: rgba(248,250,252,0.8);
  font-size: 14px;
  font-weight: 700;
}
.hf-step-copy {
  display: grid;
  gap: 4px;
}
.hf-step-label {
  font-size: 22px;
  font-weight: 700;
}
.hf-step-sublabel {
  color: rgba(248,250,252,0.68);
  font-size: 16px;
}
.hf-step[data-state="bottleneck"] {
  border-color: rgba(239,68,68,0.44);
  box-shadow: 0 0 0 1px rgba(239,68,68,0.14), 0 0 24px rgba(239,68,68,0.12);
}
.hf-step[data-state="active"] .hf-step-index {
  background: rgba(0,229,255,0.16);
  color: var(--hf-cyan);
}
.hf-custom, .hf-external {
  display: grid;
  gap: 16px;
  align-content: start;
}
.hf-code {
  margin-top: 6px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(2,6,23,0.72);
  border: 1px solid rgba(255,255,255,0.08);
  color: rgba(226,232,240,0.92);
  font-family: "JetBrains Mono", "IBM Plex Mono", monospace;
  font-size: 15px;
  white-space: pre-wrap;
  line-height: 1.4;
}
.hf-statements {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}
.hf-statement {
  font-size: clamp(40px, 5.2vw, 78px);
  line-height: 1.02;
  font-weight: 800;
  letter-spacing: -0.04em;
}
.hf-statement[data-rank="0"] {
  color: var(--hf-cyan);
}
.hf-takeaway {
  display: grid;
  gap: 18px;
  align-content: center;
  min-height: 100%;
}
.hf-headline {
  font-size: clamp(48px, 6vw, 92px);
  line-height: 0.98;
  font-weight: 800;
  letter-spacing: -0.05em;
  max-width: 900px;
}
.hf-cta {
  color: var(--hf-muted);
  font-size: 22px;
}
.hf-accent-line {
  width: 180px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--hf-cyan), rgba(0,229,255,0.08));
}
.hf-muted-card {
  margin-top: 24px;
  padding: 18px 22px;
  border-radius: 18px;
  border: 1px dashed rgba(255,255,255,0.16);
  background: rgba(255,255,255,0.03);
  color: rgba(248,250,252,0.72);
  font-size: 18px;
}
.hf-pulse {
  animation: hfPulse 2.6s ease-in-out infinite;
}
.hf-slide-in {
  opacity: 0;
  transform: translateY(28px);
  animation: hfSlideIn 680ms cubic-bezier(.2,.8,.2,1) forwards;
}
.hf-countup {
  display: inline-block;
}
.hf-breath {
  animation: hfBreath 4s ease-in-out infinite;
}
@keyframes hfPulse {
  0%, 100% { filter: drop-shadow(0 0 0 rgba(0,229,255,0)); }
  50% { filter: drop-shadow(0 0 18px rgba(0,229,255,0.35)); }
}
@keyframes hfSlideIn {
  to { opacity: 1; transform: translateY(0); }
}
@keyframes hfBreath {
  0%, 100% { transform: scale(1); opacity: 0.96; }
  50% { transform: scale(1.01); opacity: 1; }
}
"""


def runtime_js() -> str:
    return """
(() => {
  const colorMap = {
    cyan: 'var(--hf-cyan)',
    green: 'var(--hf-green)',
    yellow: 'var(--hf-yellow)',
    red: 'var(--hf-red)',
    white: 'var(--hf-white)',
  };

  document.querySelectorAll('[data-color]').forEach((node) => {
    const color = node.getAttribute('data-color');
    if (color && colorMap[color]) node.style.color = colorMap[color];
  });

  document.querySelectorAll('[data-countup-target]').forEach((node) => {
    node.textContent = node.getAttribute('data-countup-target') || '';
  });
})();
"""
