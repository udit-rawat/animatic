"""
HyperFrames Phase 3 preview runner.

Current scope:
1. load `output/video_spec.json`
2. build a local HTML preview composition
3. write `index.html` + `composition.json` into a working directory

Phase 4 adds an execution bridge:
- package mode: always available, writes a standalone composition bundle
- render mode: executes an external command if configured

This keeps renderer work real without hardcoding an unknown HyperFrames CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

from renderers.hyperframes.composition_builder import build_composition

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional dependency
    tqdm = None


@dataclass
class HyperFramesRenderConfig:
    spec_path: Path
    output_path: Path
    working_dir: Path
    mode: str = "auto"
    render_command: str = ""
    entry_html_path: Path | None = None


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_PERCENT_RE = re.compile(r"(\d{1,3})%")


def _render_timeout_seconds() -> int:
    raw = os.environ.get("HYPERFRAMES_RENDER_TIMEOUT_SECONDS", "1800").strip()
    try:
        value = int(raw)
    except ValueError:
        return 1800
    return max(60, value)


def load_spec(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def _resolve_asset_path(spec_path: Path, asset_src: str) -> Path | None:
    if not asset_src:
        return None

    candidate = Path(asset_src)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    relative_candidates = [
        spec_path.parent / candidate,
        spec_path.parent.parent / candidate,
    ]
    for path in relative_candidates:
        if path.exists():
            return path
    return None


def _copy_packaged_assets(spec: dict, config: HyperFramesRenderConfig) -> dict:
    assets = spec.get("assets", {})
    audio_src = assets.get("audio_src", "")
    resolved_audio = _resolve_asset_path(config.spec_path, audio_src)
    if resolved_audio:
        destination = config.working_dir / resolved_audio.name
        if resolved_audio.resolve() != destination.resolve():
            shutil.copy2(resolved_audio, destination)
        assets["audio_src"] = destination.name
    return spec


def _copy_custom_composition(entry_html_path: Path, working_dir: Path) -> Path:
    source_dir = entry_html_path.parent
    for child in source_dir.iterdir():
        target = working_dir / child.name
        if child.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(child, target)
            continue
        if child.resolve() == target.resolve():
            continue
        shutil.copy2(child, target)

    packaged_entry = working_dir / "index.html"
    if entry_html_path.name != "index.html":
        shutil.copy2(entry_html_path, packaged_entry)
    return packaged_entry


def _package_composition(config: HyperFramesRenderConfig) -> tuple[dict, Path]:
    config.working_dir.mkdir(parents=True, exist_ok=True)
    spec = load_spec(config.spec_path)
    if config.entry_html_path and config.entry_html_path.exists():
        html_path = _copy_custom_composition(config.entry_html_path, config.working_dir)
        spec = _copy_packaged_assets(spec, config)
        composition = {
            "version": "custom",
            "meta": {
                "source": "custom_hyperframes_composition",
                "entry_html_path": str(config.entry_html_path),
            },
            "html": html_path.read_text(encoding="utf-8"),
        }
    else:
        spec = _copy_packaged_assets(spec, config)
        composition = build_composition(spec)
        html_path = config.working_dir / "index.html"
        html_path.write_text(composition["html"], encoding="utf-8")

    composition_path = config.working_dir / "composition.json"
    manifest_path = config.working_dir / "render_manifest.json"

    with composition_path.open("w") as f:
        json.dump(composition, f, indent=2)
    with manifest_path.open("w") as f:
        json.dump(
            {
                "spec_path": str(config.spec_path),
                "output_path": str(config.output_path),
                "mode": config.mode,
                "render_command": config.render_command,
                "entry_html_path": (
                    str(config.entry_html_path) if config.entry_html_path else ""
                ),
                "package_entrypoint": str(html_path),
            },
            f,
            indent=2,
        )

    return composition, html_path


def _resolved_render_command(config: HyperFramesRenderConfig) -> str:
    if config.render_command:
        return config.render_command
    env_command = os.environ.get("HYPERFRAMES_RENDER_CMD", "").strip()
    if env_command:
        return env_command

    hyperframes_bin = shutil.which("hyperframes")
    if hyperframes_bin:
        return f'"{hyperframes_bin}" render'

    cached_clis = sorted(
        Path.home().glob(".npm/_npx/*/node_modules/hyperframes/dist/cli.js"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if cached_clis:
        return f'node "{cached_clis[0]}" render'

    npx_bin = shutil.which("npx")
    if npx_bin:
        return f'"{npx_bin}" hyperframes render'

    return ""


def _resolve_rendered_artifact(config: HyperFramesRenderConfig) -> Path | None:
    render_dir = config.working_dir / "renders"
    candidates: list[Path] = []
    if render_dir.exists():
        candidates.extend(render_dir.glob("*.mp4"))
    if config.output_path.exists():
        candidates.append(config.output_path)
    if not candidates:
        return None

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    if latest.resolve() == config.output_path.resolve():
        return config.output_path

    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest, config.output_path)
    return config.output_path


def _should_use_tqdm() -> bool:
    raw = os.environ.get("HYPERFRAMES_TQDM", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"} and tqdm is not None


def _clean_progress_line(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text).strip()


def _update_tqdm_from_line(line: str, progress_bar) -> None:
    if progress_bar is None:
        return
    cleaned = _clean_progress_line(line)
    match = _PERCENT_RE.search(cleaned)
    if not match:
        return
    percent = max(0, min(100, int(match.group(1))))
    if percent > progress_bar.n:
        progress_bar.update(percent - progress_bar.n)
    description = cleaned
    if description:
        progress_bar.set_postfix_str(description[:80], refresh=False)


def _run_streaming_command(command: str, cwd: Path, timeout_seconds: int) -> int:
    progress_bar = None
    if _should_use_tqdm():
        progress_bar = tqdm(total=100, desc="HyperFrames", unit="%")

    process = subprocess.Popen(
        shlex.split(command),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,
    )
    buffer = ""
    started = time.monotonic()

    try:
        while True:
            if time.monotonic() - started > timeout_seconds:
                process.kill()
                raise RuntimeError(
                    f"HyperFrames render timed out after {timeout_seconds}s. "
                    "Increase HYPERFRAMES_RENDER_TIMEOUT_SECONDS if needed."
                )

            char = process.stdout.read(1) if process.stdout else ""
            if char == "":
                if process.poll() is not None:
                    break
                time.sleep(0.05)
                continue

            sys.stdout.write(char)
            sys.stdout.flush()

            if char in {"\r", "\n"}:
                _update_tqdm_from_line(buffer, progress_bar)
                buffer = ""
            else:
                buffer += char
                if len(buffer) > 1000:
                    buffer = buffer[-1000:]

        if buffer:
            _update_tqdm_from_line(buffer, progress_bar)
        return_code = process.wait()
        if progress_bar is not None and return_code == 0 and progress_bar.n < 100:
            progress_bar.update(100 - progress_bar.n)
        return return_code
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        raise
    finally:
        if progress_bar is not None:
            progress_bar.close()


def _run_external_render(
    config: HyperFramesRenderConfig, html_path: Path
) -> Path | None:
    cmd_template = _resolved_render_command(config)
    if not cmd_template:
        return None

    command = cmd_template.format(
        html=str(html_path),
        output=str(config.output_path),
        workdir=str(config.working_dir),
        spec=str(config.spec_path),
    )
    timeout_seconds = _render_timeout_seconds()
    print(f"[hyperframes] Running: {command}")
    print(f"[hyperframes] Workdir: {config.working_dir}")
    if config.output_path.exists():
        config.output_path.unlink()
    return_code = _run_streaming_command(command, config.working_dir, timeout_seconds)
    if return_code != 0:
        raise RuntimeError(
            f"HyperFrames external render command failed with exit code {return_code}."
        )
    return _resolve_rendered_artifact(config)


def render(config: HyperFramesRenderConfig) -> Path:
    composition, html_path = _package_composition(config)

    mode = config.mode
    if mode == "package":
        return html_path

    if mode == "render":
        rendered = _run_external_render(config, html_path)
        if rendered:
            return rendered
        raise RuntimeError(
            "HyperFrames render mode requested, but no render command was configured. "
            "Set HYPERFRAMES_RENDER_CMD or pass render_command."
        )

    # auto mode: package always, then try external render only if configured
    rendered = _run_external_render(config, html_path)
    if rendered:
        return rendered

    return html_path
