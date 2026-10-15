"""Verify a rendered reel keeps every content pixel inside the spec's layout.safe_area.
Samples frames from the MP4, flags pixels outside the safe rect that differ from the
background (dark or saturated on a light canvas; bright or saturated on a dark one)."""
import argparse, json, subprocess, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--spec", required=True); ap.add_argument("--video", required=True)
ap.add_argument("--fps", type=float, default=4.0); ap.add_argument("--theme", default="light", help="light | dark | auto (per-frame background, for reels that flip polarity)")
ap.add_argument("--bg", default="", help="comma-separated background hex colours, e.g. '#f2f1ec,#0c0c0c'")
a = ap.parse_args()
spec = json.load(open(a.spec)); sa = spec["layout"]["safe_area"]; W, H = 1080, 1920
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"fps={a.fps}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.int16)
out = np.ones((H, W), bool); out[sa["y"]:sa["y"] + sa["height"], sa["x"]:sa["x"] + sa["width"]] = False
worst = []
for i, f in enumerate(fr):
    lum = (0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2])
    chroma = f.max(-1) - f.min(-1)
    if a.bg:
        # background = any of the listed palette colours (e.g. paper and ink for a polarity-flip reel)
        cols = [np.array([int(c.strip().lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]) for c in a.bg.split(",")]
        bad = np.min([np.abs(f - c).max(-1) for c in cols], axis=0) > 30
    elif a.theme == "auto":
        # background = the median colour of the outside region in this frame; content = anything far from it
        bg = np.median(f[out], axis=0)
        bad = np.abs(f - bg).max(-1) > 30
    else:
        bad = ((lum < 228) | (chroma > 30)) if a.theme == "light" else ((lum > 60) | (chroma > 30))
    n = int((bad & out).sum())
    if n: worst.append((round(i / a.fps, 2), n))
print(f"frames checked: {len(fr)}; frames with content outside safe area: {len(worst)}")
print("worst:", sorted(worst, key=lambda x: -x[1])[:8])
