"""Emit layout.js for a HyperFrames composition from the spec's layout.safe_area block,
so every reel positions its content inside the Instagram Reels safe zone."""
import argparse, json
from pathlib import Path

ap = argparse.ArgumentParser(); ap.add_argument("--spec", required=True)
spec = json.loads(Path(ap.parse_args().spec).read_text())
root = Path(__file__).resolve().parents[1]
sa = spec["layout"]["safe_area"]
out = root / spec["composition_dir"] / "layout.js"
out.write_text("window.SAFE = " + json.dumps({"x": sa["x"], "y": sa["y"], "w": sa["width"], "h": sa["height"],
               "r": sa["x"] + sa["width"], "b": sa["y"] + sa["height"]}) + ";\n")
print("wrote", out, open(out).read().strip())
