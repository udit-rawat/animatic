#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESBUILD = ROOT / "remotion" / "node_modules" / ".bin" / "esbuild"

REACT_IMPORTS = """import React from '../../../remotion/node_modules/react/index.js';
import * as ReactDOMClient from '../../../remotion/node_modules/react-dom/client.js';
const ReactDOM = ReactDOMClient;

"""

RENDER_CLOCK = """function useMasterClock(){
  const [t,setT] = React.useState(0);
  const [playing,setPlaying] = React.useState(!window.__RENDER_EMBED__);
  const lastRef = React.useRef(null);
  const rafRef = React.useRef(null);

  React.useEffect(()=>{
    if (window.__RENDER_EMBED__) {
      const api = {
        seek(next){
          setT(Math.max(0, Math.min(TOTAL, Number(next) || 0)));
          setPlaying(false);
        },
        play(){ setPlaying(true); },
        pause(){ setPlaying(false); },
        duration(){ return TOTAL; },
        getTime(){ return t; }
      };
      window.__player = api;
      window.__playerReady = true;
      return () => {
        if (window.__player === api) delete window.__player;
        window.__playerReady = false;
      };
    }

    if(!playing){ lastRef.current=null; return; }
    const step = (ts)=>{
      if(lastRef.current==null) lastRef.current=ts;
      const dt = (ts-lastRef.current)/1000;
      lastRef.current=ts;
      setT(prev=>{
        let n = prev+dt;
        if(n>=TOTAL) n = n%TOTAL;
        return n;
      });
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return ()=>{ if(rafRef.current) cancelAnimationFrame(rafRef.current); lastRef.current=null; };
  },[playing, t]);

  return { t, setT, playing, setPlaying };
}"""

HOOK_UI_BLOCK = """  // Hook UI
  React.useEffect(()=>{
    if (window.__RENDER_EMBED__) return;
    const btnPlay = document.getElementById('btnPlay');
    const btnRestart = document.getElementById('btnRestart');
    const scrub = document.getElementById('scrub');
    const tcLabel = document.getElementById('tcLabel');
    if(!btnPlay) return;
    btnPlay.onclick = ()=> setPlaying(p=>!p);
    btnRestart.onclick = ()=> setT(0);
    scrub.oninput = (e)=> { setT(parseInt(e.target.value)/100); setPlaying(false); };
    btnPlay.textContent = playing ? '⏸' : '▶';
    scrub.value = String(Math.round(t*100));
    tcLabel.textContent = `${t.toFixed(2)} / ${TOTAL.toFixed(2)}`;
  }, [t, playing, setT, setPlaying]);"""

AUTO_SCALE_BLOCK = """  // Auto-scale canvas
  React.useEffect(()=>{
    if (window.__RENDER_EMBED__) return;
    const canvas = document.getElementById('canvas');
    const stage = document.getElementById('stage');
    function fit(){
      const padBottom = 60;
      const sw = stage.clientWidth;
      const sh = stage.clientHeight - padBottom;
      const scale = Math.min(sw/W, sh/H);
      canvas.style.transform = `scale(${scale})`;
    }
    fit();
    window.addEventListener('resize', fit);
    return ()=>window.removeEventListener('resize', fit);
  }, []);"""


def _extract_between(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.S)
    if not match:
        raise ValueError(f"pattern not found: {pattern}")
    return match.group(1)


def _extract_title(html: str) -> str:
    return _extract_between(r"<title>(.*?)</title>", html).strip()


def _extract_styles(html: str) -> str:
    blocks = re.findall(r"<style>(.*?)</style>", html, re.S)
    return "\n".join(block.strip() for block in blocks if block.strip())


def _extract_narration(html: str) -> dict:
    payload = _extract_between(
        r'<script[^>]+type="application/json"[^>]+id="narration"[^>]*>\s*(\{.*?\})\s*</script>',
        html,
    )
    return json.loads(payload)


def _extract_babel_source(html: str) -> str:
    return _extract_between(
        r'<script[^>]+type="text/babel"[^>]*>\s*(.*?)\s*</script>\s*</body>',
        html,
    )


def _patch_source(source: str) -> str:
    source = source.replace("\r\n", "\n")
    source = re.sub(
        r"function useMasterClock\(\)\{.*?return \{ t, setT, playing, setPlaying \};\n\}",
        RENDER_CLOCK,
        source,
        flags=re.S,
        count=1,
    )
    source = source.replace(
        """  // Hook UI
  React.useEffect(()=>{
    const btnPlay = document.getElementById('btnPlay');
    const btnRestart = document.getElementById('btnRestart');
    const scrub = document.getElementById('scrub');
    const tcLabel = document.getElementById('tcLabel');
    if(!btnPlay) return;
    btnPlay.onclick = ()=> setPlaying(p=>!p);
    btnRestart.onclick = ()=> setT(0);
    scrub.oninput = (e)=> { setT(parseInt(e.target.value)/100); setPlaying(false); };
    btnPlay.textContent = playing ? '⏸' : '▶';
    scrub.value = String(Math.round(t*100));
    tcLabel.textContent = `${t.toFixed(2)} / ${TOTAL.toFixed(2)}`;
  }, [t, playing, setT, setPlaying]);""",
        HOOK_UI_BLOCK,
    )
    source = source.replace(
        """  // Auto-scale canvas
  React.useEffect(()=>{
    const canvas = document.getElementById('canvas');
    const stage = document.getElementById('stage');
    function fit(){
      const padBottom = 60;
      const sw = stage.clientWidth;
      const sh = stage.clientHeight - padBottom;
      const scale = Math.min(sw/W, sh/H);
      canvas.style.transform = `scale(${scale})`;
    }
    fit();
    window.addEventListener('resize', fit);
    return ()=>window.removeEventListener('resize', fit);
  }, []);""",
        AUTO_SCALE_BLOCK,
    )
    if "window.__RENDER_EMBED__" not in source:
        source = source.replace(
            "// =============================================================================",
            "const __HF_RENDER__ = !!window.__RENDER_EMBED__;\n\n// =============================================================================",
            1,
        )
    return REACT_IMPORTS + source


def _build_shell(
    title: str, composition_id: str, duration: float, source_styles: str
) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Sans+Condensed:wght@600;700&display=swap" rel="stylesheet">
<style>
{source_styles}

  html, body {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; }}
  #composition-root {{ position:relative; width:1080px; height:1920px; overflow:hidden; }}
  #stage {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; overflow:hidden; }}
  #canvas {{ position:relative; width:1080px !important; height:1920px !important; overflow:hidden; flex-shrink:0; transform:none !important; box-shadow:none !important; }}
  #toolbar {{ display:none !important; }}
</style>
</head>
<body>
<div id="composition-root" data-composition-id="{composition_id}" data-start="0" data-duration="{duration}" data-width="1080" data-height="1920">
  <audio id="narration" data-start="0" data-duration="{duration}" data-track-index="0" src="narration.wav" data-volume="1"></audio>
  <div id="stage"><div id="canvas"></div></div>
  <div id="toolbar" aria-hidden="true">
    <button id="btnPlay">play</button>
    <button id="btnRestart">restart</button>
    <span id="tcLabel"></span>
    <input id="scrub" type="range" min="0" max="{int(round(duration * 100))}" value="0" step="1" />
  </div>
</div>
<script>
window.__RENDER_EMBED__ = true;
window.__playerReady = false;
window.__timelines = window.__timelines || {{}};
window.__timelines['{composition_id}'] = window.__timelines['{composition_id}'] || {{
  seek(t) {{ if (window.__player && typeof window.__player.seek === 'function') window.__player.seek(t); }},
  play() {{ if (window.__player && typeof window.__player.play === 'function') window.__player.play(); }},
  pause() {{ if (window.__player && typeof window.__player.pause === 'function') window.__player.pause(); }},
  duration() {{ return {duration}; }}
}};
</script>
<script src="app.bundle.js"></script>
</body>
</html>
"""


def _segments_from_narration(narration: dict) -> list[dict]:
    items = []
    for segment in narration["segments"]:
        start = float(segment["t"])
        end = float(segment["end"])
        items.append(
            {
                "id": str(segment["id"]),
                "start": start,
                "duration": round(end - start, 3),
                "text": str(segment["text"]),
            }
        )
    return items


def _build_spec(
    slug: str,
    title: str,
    composition_dir: Path,
    output_file: str,
    duration: float,
    narration: dict,
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "duration": duration,
        "fps": 30,
        "voice": "Aoede",
        "tts_provider": "gemini",
        "composition_dir": str(composition_dir.relative_to(ROOT)),
        "output_file": output_file,
        "audio_file": "narration.wav",
        "render": {
            "quality": "high",
            "crf": 6,
            "workers": 1,
        },
        "audio": {
            "sample_rate": 24000,
            "channels": 1,
            "mastering": True,
        },
        "segments": _segments_from_narration(narration),
    }


def import_reel(
    source_html: Path,
    composition_dir: Path,
    spec_path: Path,
    slug: str,
    output_file: str,
) -> None:
    html = source_html.read_text()
    title = _extract_title(html)
    styles = _extract_styles(html)
    narration = _extract_narration(html)
    duration = float(narration["totalSeconds"])
    source = _patch_source(_extract_babel_source(html))

    composition_dir.mkdir(parents=True, exist_ok=True)
    (composition_dir / "original.html").write_text(html)
    (composition_dir / "app.source.jsx").write_text(source)
    (composition_dir / "index.html").write_text(
        _build_shell(title, slug, duration, styles)
    )

    subprocess.run(
        [
            str(ESBUILD),
            str(composition_dir / "app.source.jsx"),
            "--bundle",
            "--format=iife",
            "--platform=browser",
            "--target=chrome120",
            f"--outfile={composition_dir / 'app.bundle.js'}",
        ],
        check=True,
    )

    spec = _build_spec(
        slug,
        title.replace("Reel · ", "").strip(),
        composition_dir,
        output_file,
        duration,
        narration,
    )
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a React/Babel reel HTML into a render-safe HyperFrames composition."
    )
    parser.add_argument("--source-html", required=True)
    parser.add_argument("--composition-dir", required=True)
    parser.add_argument("--spec-path", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    import_reel(
        source_html=Path(args.source_html),
        composition_dir=ROOT / args.composition_dir,
        spec_path=ROOT / args.spec_path,
        slug=args.slug,
        output_file=args.output_file,
    )


if __name__ == "__main__":
    main()
