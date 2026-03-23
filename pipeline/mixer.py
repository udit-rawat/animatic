"""
mixer.py — merges output/video.mp4 + output/narration.wav → output/video_final.mp4
Uses ffmpeg. Trims to the shorter of the two (video wins if narration runs long).
"""
import os
import shutil
import subprocess

VIDEO_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "video.mp4")
AUDIO_PATH  = os.path.join(os.path.dirname(__file__), "..", "output", "narration.wav")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "video_final.mp4")


def main():
    if not os.path.exists(VIDEO_PATH):
        raise RuntimeError(f"Video not found: {VIDEO_PATH}. Run animator first.")
    if not os.path.exists(AUDIO_PATH):
        raise RuntimeError(f"Narration not found: {AUDIO_PATH}. Run narrator first.")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found — install with: brew install ffmpeg")

    # Get durations
    def _duration(path: str) -> float:
        import json as _json
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
            capture_output=True, text=True,
        )
        streams = _json.loads(r.stdout).get("streams", [])
        for s in streams:
            if "duration" in s:
                return float(s["duration"])
        return 0.0

    v_dur = _duration(VIDEO_PATH)
    a_dur = _duration(AUDIO_PATH)

    # Build video filter: stretch/compress video to match audio duration exactly
    if v_dur > 0 and a_dur > 0:
        pts_scale = v_dur / a_dur          # <1 speeds up video, >1 slows it down
        vf = f"setpts={pts_scale:.6f}*PTS"
        print(f"Syncing: video={v_dur:.1f}s  audio={a_dur:.1f}s  scale={pts_scale:.3f}x")
    else:
        vf = "setpts=PTS"
        print("Mixing video + narration audio...")

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", VIDEO_PATH,
            "-i", AUDIO_PATH,
            "-vf", vf,
            "-c:v", "libx264",    # re-encode needed for setpts
            "-crf", "18",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "192k",
            OUTPUT_PATH,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-600:]}")

    size_mb = os.path.getsize(OUTPUT_PATH) / 1_000_000
    print(f"✓ Final video saved → {OUTPUT_PATH}  ({size_mb:.1f} MB)")
    return OUTPUT_PATH


if __name__ == "__main__":
    main()
