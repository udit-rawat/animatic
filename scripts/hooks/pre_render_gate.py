"""Claude Code PreToolUse hook (Bash): block a final reel render until the motion gate passes.

Fires on `render_hyperframes.py --spec ...` and on `hyperframes render` that is not `-q draft`; `--dry-run` passes.
Finds the spec whose composition_dir is the render target, runs
`scripts/reel_gate.py motion`, and exits 2 (block, reason on stderr) if it fails.
Compositions dated before the gate existed (2026-10-13) and dirs without a spec pass through."""
import json, re, shlex, subprocess, sys, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE_START = "2026-10-13"

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
cmd = (data.get("tool_input") or {}).get("command", "")
if "render_hyperframes.py" not in cmd and not re.search(r"hyperframes(@[\w.]+)?\s+render\b", cmd):
    sys.exit(0)
if re.search(r"-q\s+draft|--quality[ =]draft|--dry-run", cmd):
    sys.exit(0)

spec_path = None
m = re.search(r"--spec\s+(\S+)", cmd)
if m:
    spec_path = Path(m.group(1).strip("'\""))
    if not spec_path.is_absolute(): spec_path = ROOT / spec_path
else:
    target = Path(data.get("cwd") or ROOT)
    cd = re.search(r"\bcd\s+(\"[^\"]+\"|'[^']+'|\S+)", cmd)
    if cd:
        p = Path(shlex.split(cd.group(1))[0]); target = p if p.is_absolute() else target / p
    rm = re.search(r"hyperframes(?:@[\w.]+)?\s+render\s+(\S+)", cmd)
    if rm and not rm.group(1).startswith("-"):
        p = Path(rm.group(1)); target = p if p.is_absolute() else target / p
    target = target.resolve()
    for f in glob.glob(str(ROOT / "reels/current/spec_*.json")):
        try: s = json.loads(Path(f).read_text())
        except Exception: continue
        cd_ = s.get("composition_dir")
        if cd_ and (ROOT / cd_).resolve() == target:
            spec_path = Path(f); break

if not spec_path or not spec_path.exists():
    sys.exit(0)
spec = json.loads(spec_path.read_text())
dm = re.search(r"(\d{4}-\d{2}-\d{2})", spec.get("composition_dir", ""))
if dm and dm.group(1) < GATE_START:
    sys.exit(0)

r = subprocess.run([sys.executable, str(ROOT / "scripts/reel_gate.py"), "motion", "--spec", str(spec_path)], capture_output=True, text=True)
if r.returncode != 0:
    sys.stderr.write("Render blocked by the motion gate (scripts/reel_gate.py motion):\n" + r.stdout +
                     "Fix the composition or declare a reasoned exception in gate.motion.allow.\n")
    sys.exit(2)
sys.exit(0)
