"""Anti-repeat gates for reels. Mechanical checks, run before pitching and before rendering.

  python3 scripts/reel_gate.py topic  --spec reels/current/spec_<topic>_v1.json
  python3 scripts/reel_gate.py motion --spec reels/current/spec_<topic>_v1.json
  python3 scripts/reel_gate.py hook   --spec reels/current/spec_<topic>_v1.json --video draft.mp4   # first 3 s checklist
  python3 scripts/reel_gate.py record --spec reels/current/spec_<topic>_v1.json   # after shipping

The spec needs a "gate" block:
  "gate": {
    "lane": "reasoning",                       # memory lane is banned for the next 5 reels
    "keywords": ["budget forcing", "wait"],    # checked against every prior spec
    "mechanism": "one sentence, the hidden mechanism",
    "ending": "the technique the viewer can do tonight",
    "kind": "tool",                            # "story" (what a lab did) fails
    "opening": "cold-open-result",             # opening structure; must differ from the last 3
    "supersedes": ["spec_x_v0.json"],          # optional: unshipped drafts of the same reel, skipped in the overlap check
    "motion": {
      "soul": "what the mechanism looks like when it moves",
      "families": ["splice", "rewind"],        # must not repeat the last 3 reels
      "allow": {"bounce": "why this reel earns it"}   # optional, each needs a reason
    }
  }
Registry of shipped reels: output/hyperframes_custom/reel_registry.json (local, gitignored)."""
import argparse, glob, json, re, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "output/hyperframes_custom/reel_registry.json"
BAN_START, BAN_COUNT = "2026-10-13", 5
MEMORY_TERMS = [r"\bgb\b", r"\bvram\b", r"\bmemory\b", r"quantiz", r"offload", r"kv cache", r"\bram\b", r"\bfits?\b",
                r"gigabyte", r"\bbits?\b per weight", r"q4_k_m", r"unified memory"]
STORY_HINT = re.compile(r"\b(released|announced|lab|paper shows|history|was trained|their first version)\b", re.I)


def load(p): return json.loads(Path(p).read_text())
def registry(): return load(REG) if REG.exists() else []
def narration(spec): return " ".join(s.get("text", "") for s in spec.get("segments", []))
def first_sentence(text): return re.split(r"(?<=[.!?])\s", text.strip(), 1)[0] if text.strip() else ""


class Report:
    def __init__(self, name): self.name, self.fails, self.notes = name, [], []
    def fail(self, m): self.fails.append(m)
    def note(self, m): self.notes.append(m)
    def done(self):
        print(f"== {self.name} gate: {'FAIL' if self.fails else 'PASS'}")
        for m in self.fails: print("  ✗", m)
        for m in self.notes: print("  ·", m)
        return 1 if self.fails else 0


def check_opening(spec, g, reg, r):
    text = narration(spec)
    fs = first_sentence(text)
    # the retired template: "<Topic name>." as a sentence of its own, then the claim
    if fs and len(fs.split()) <= 4 and fs.endswith(".") and not fs.endswith("?"):
        r.fail(f'opening is the retired "Topic name. Claim." template: "{fs}"')
    op = g.get("opening", "").strip()
    if not op: r.fail("gate.opening (opening structure) is missing")
    recent = [x.get("opening") for x in reg[-3:]]
    if op and op in recent: r.fail(f'opening "{op}" was used in the last 3 reels {recent}')


def topic(spec, spec_path):
    r, g, reg = Report("topic"), spec.get("gate", {}), registry()
    for k in ["lane", "keywords", "mechanism", "ending", "kind"]:
        if not g.get(k): r.fail(f"gate.{k} is missing")
    mech = g.get("mechanism", "")
    if mech and len(re.findall(r"[.!?](\s|$)", mech.strip())) > 1: r.fail("mechanism must be ONE sentence")
    if g.get("kind") == "story": r.fail('kind "story" (what a lab did) is not allowed: R1 got 2.9 saves/1k')
    if STORY_HINT.search(mech): r.note("mechanism reads like a story; make sure the ending is something the viewer does")
    # memory/GB lane ban
    shipped_since = [x for x in reg if x.get("date", "") >= BAN_START and not x.get("backfill")]
    ban = len(shipped_since) < BAN_COUNT
    blob = " ".join([spec.get("title", ""), mech, " ".join(g.get("keywords", [])), narration(spec)]).lower()
    hits = sorted({t for t in MEMORY_TERMS if re.search(t, blob)})
    if ban and (g.get("lane", "").lower() in {"memory", "hardware", "gb"} or len(hits) >= 3):
        r.fail(f"memory/GB lane is banned for {BAN_COUNT - len(shipped_since)} more reel(s); terms hit: {hits}")
    elif hits: r.note(f"memory terms present: {hits}")
    # overlap with every prior spec (title + narration, not just titles)
    me = Path(spec_path).resolve()
    for f in sorted(glob.glob(str(ROOT / "reels/current/spec_*.json"))):
        if Path(f).resolve() == me: continue
        if Path(f).name in set(g.get("supersedes", [])): continue   # unshipped drafts this spec replaces
        try: o = load(f)
        except Exception: continue
        title, body = o.get("title", "").lower(), narration(o).lower()
        for kw in g.get("keywords", []):
            k = kw.lower()
            if k in title: r.fail(f'keyword "{kw}" is in a prior title: {Path(f).name} "{o.get("title")}"')
            elif re.search(r"\b" + re.escape(k) + r"\b", body): r.note(f'"{kw}" appears in prior narration: {Path(f).name}')
    check_opening(spec, g, reg, r)
    return r.done()


BANNED_FONTS = {f.lower() for f in ["Inter", "Inter Tight", "Roboto", "Open Sans", "Noto Sans", "Arimo", "Lato", "Source Sans",
    "PT Sans", "Nunito", "Poppins", "Outfit", "Sora", "Montserrat", "Geist", "Geist Mono", "Space Grotesk", "JetBrains Mono",
    "Playfair Display", "Cormorant Garamond", "Bodoni Moda", "EB Garamond", "Cinzel", "Prata", "Syne", "Instrument Serif",
    "Arial", "Helvetica", "system-ui", "-apple-system"]}
STYLE_TELLS = {
    "gradient text (background-clip:text)": r"background-clip\s*:\s*text",
    "purple/indigo-to-blue gradient": r"#(667eea|764ba2|6366f1|8b5cf6|7c3aed|a855f7|4f46e5)",
    "glow (blurred coloured shadow)": r"(text|box)-shadow\s*:[^;]*\d+px\s+\d+px\s+([2-9]\d|1\d\d)px[^;]*(rgba?\((?!0,\s*0,\s*0)|#(?!000))",
    "glassmorphism (backdrop-filter blur)": r"backdrop-filter\s*:\s*blur",
    "neon / drop-shadow glow filter": r"filter\s*:\s*drop-shadow\([^)]*([2-9]\d)px",
}
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")
PRIMS = {
    "pop-zero": (r"\bscale\s*:\s*0(?![.\d])", 1, "pop-in from scale(0) reads synthetic; enter from 0.94-0.97"),
    "bounce": (r"back\.out|elastic|bounce\.out", 1, "bounce ease"),
    "slam": (r"scale\s*:\s*(1\.[5-9]\d*|[2-9](\.\d+)?)\s*,", 1, "oversized slam-in (scale >= 1.5 -> 1)"),
    "bar-grow": (r"scale[XY]\s*:\s*0(?![.\d])", 3, "bars/lines growing from zero (3+ uses)"),
}


def motion(spec):
    r, g, reg = Report("motion"), spec.get("gate", {}), registry()
    m = g.get("motion", {})
    allow = m.get("allow", {}) or {}
    for k, why in allow.items():
        if not str(why).strip(): r.fail(f'motion.allow["{k}"] needs a written reason')
    if not m.get("soul", "").strip(): r.fail("gate.motion.soul is missing (what the mechanism looks like moving)")
    fams = [f.lower() for f in m.get("families", [])]
    if not fams: r.fail("gate.motion.families is empty")
    recent = {f.lower() for x in reg[-3:] for f in x.get("families", [])}
    rep = sorted(set(fams) & recent)
    if rep: r.fail(f"motion families repeat the last 3 reels: {rep}")
    cdir = ROOT / spec["composition_dir"]
    src = ""
    for f in [cdir / "index.html", *sorted(cdir.glob("*.js"))]:
        if f.exists() and f.name not in {"layout.js"}: src += f.read_text(errors="ignore") + "\n"
    if not src: r.fail(f"no composition source in {cdir}"); return r.done()
    found = {}
    for name, (pat, thresh, desc) in PRIMS.items():
        n = len(re.findall(pat, src))
        if n >= thresh: found[name] = n
        if n >= thresh and name not in allow: r.fail(f"{name} x{n}: {desc}")
    if re.search(r"(textContent|innerHTML|innerText)\s*=[^;\n]*(toFixed|Math\.round|Math\.floor)", src):
        found["count-up"] = 1
        if "count-up" not in allow: r.fail("count-up numbers (toFixed into textContent): house-kit primitive")
    # style tells from the anti-list (output/hyperframes_custom/ANTI_LIST.md)
    for fam in sorted({m.group(1).strip() for m in re.finditer(r"(?:font-family\s*:|--[\w-]+\s*:)\s*[\"']?([A-Za-z][\w ]+?)[\"']?\s*[,;]", src)}):
        if fam.lower() in BANNED_FONTS and "font" not in allow: r.fail(f'banned font as primary family: "{fam}" (training-data default)')
    for name, pat in STYLE_TELLS.items():
        if re.search(pat, src, re.I) and name not in allow: r.fail(f"style tell: {name}")
    if EMOJI.search(src) and "emoji" not in allow: r.fail("emoji in the composition")
    r.note(f"primitives found: {found or 'none'}")
    check_opening(spec, g, reg, r)
    spec["_primitives"] = sorted(found)
    return r.done()


def record(spec):
    g = spec.get("gate", {})
    reg = registry()
    reg = [x for x in reg if x.get("slug") != spec.get("slug")]
    reg.append({"slug": spec.get("slug"), "date": str(date.today()), "lane": g.get("lane"), "opening": g.get("opening"),
                "families": g.get("motion", {}).get("families", []), "kind": g.get("kind")})
    REG.write_text(json.dumps(reg, indent=1)); print("recorded", spec.get("slug"), "->", REG)
    return 0


def hook(spec, video):
    """The 8-point first-3-seconds checklist (Virality skill, @jayantcreates.ai winners vs flops),
    measured on a rendered MP4 plus the transcript. Spec needs gate.hook: {claim_word, frame0, captions}."""
    import subprocess
    import numpy as np
    from scipy import ndimage as ndi
    r, g = Report("hook"), spec.get("gate", {})
    h = g.get("hook", {})
    W, H, FPS = 270, 480, 20
    raw = subprocess.run(["ffmpeg", "-v", "error", "-t", "3.2", "-i", video, "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    if len(f) < 10: r.fail(f"could not read the first 3 s of {video}"); return r.done()
    bg = np.median(f[0])
    content0 = np.abs(f[0] - bg) > 24
    # 1. frame 0 is not empty and already moving
    fill0 = content0.mean()
    move0 = (np.abs(f[1] - f[0]) > 6).mean()
    if fill0 < 0.04: r.fail(f"1 frame 0 is near-empty ({fill0:.1%} of pixels are content)")
    if move0 < 0.002: r.fail(f"1 nothing moves on frame 0 ({move0:.2%} of pixels change by frame 1)")
    # 2. frame 0 shows something instantly recognisable: declared, judged by a human
    if not str(h.get("frame0", "")).strip(): r.fail("2 gate.hook.frame0 missing: name the recognisable thing on frame 0 (logo, app, the viewer's problem)")
    else: r.note(f"2 frame 0 (declared): {h['frame0']}")
    # 3. biggest element owns >= 40% of the frame (largest connected content blob, bounding box)
    lab, n = ndi.label(ndi.binary_dilation(content0, iterations=6))
    big = 0.0
    if n:
        sizes = ndi.sum(content0, lab, range(1, n + 1)); k = int(np.argmax(sizes)) + 1
        ys, xs = np.where(lab == k); big = (np.ptp(ys) + 1) * (np.ptp(xs) + 1) / (W * H)
    if big < 0.40: r.fail(f"3 biggest element on frame 0 covers {big:.0%} of the frame (need >= 40%)")
    else: r.note(f"3 biggest element {big:.0%}")
    # 4. something extraordinary before 3 s: one big visual event (>= 12% of pixels change within 0.25 s)
    step = FPS // 4
    ev = max(((np.abs(f[i] - f[i - step]) > 12).mean(), i / FPS) for i in range(step, len(f)))
    if ev[0] < 0.12: r.fail(f"4 no big visual event before 3 s (largest 0.25 s change: {ev[0]:.1%} at {ev[1]:.2f}s)")
    else: r.note(f"4 event: {ev[0]:.0%} of pixels change around {ev[1]:.2f}s")
    # 5 + 6. timings from the transcript
    tp = ROOT / spec["composition_dir"] / "transcript.json"
    if tp.exists():
        d = json.loads(tp.read_text()); ws = d if isinstance(d, list) else d.get("words", [])
        if ws and ws[0]["start"] > 0.5: r.fail(f"6 first spoken word at {ws[0]['start']:.2f}s (need <= 0.5 s)")
        cw = str(h.get("claim_word", "")).lower().strip(".,")
        hit = [w["start"] for w in ws if w["text"].lower().strip(".,?!") == cw and w["start"] < 4]
        if not cw: r.fail("5 gate.hook.claim_word missing")
        elif not hit: r.fail(f'5 claim word "{cw}" not found in the first 4 s of the transcript')
        elif not (1.0 <= hit[0] <= 1.8): r.fail(f'5 claim word "{cw}" lands at {hit[0]:.2f}s (aim 1.2 to 1.6 s)')
        else: r.note(f'5 claim "{cw}" at {hit[0]:.2f}s')
    else: r.fail(f"5/6 no transcript.json in {spec['composition_dir']}")
    # 7. works on mute: captions declared
    if not h.get("captions"): r.fail("7 gate.hook.captions is not true (word-by-word captions make it work on mute)")
    # 8. about the viewer: "you"/"your" in the first sentence of the narration
    fs = first_sentence(re.sub(r"^[^:]{20,}:\s*", "", narration(spec)))
    if not re.search(r"\byou(r|'re)?\b", fs, re.I): r.fail(f'8 first line is not about the viewer: "{fs[:80]}"')
    return r.done()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["topic", "motion", "hook", "record"]); ap.add_argument("--spec", required=True); ap.add_argument("--video")
    a = ap.parse_args(); s = load(a.spec)
    sys.exit({"topic": lambda: topic(s, a.spec), "motion": lambda: motion(s), "hook": lambda: hook(s, a.video or s.get("output_file")), "record": lambda: record(s)}[a.cmd]())
