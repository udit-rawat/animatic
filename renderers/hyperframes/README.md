## HyperFrames Renderer Skeleton

Phase 2 creates the renderer boundary and module layout only.

Not included yet:
- bundled HyperFrames engine in this repo
- production output parity

Included now:
- runner contract
- composition builder contract
- helper primitive contract
- template module placeholders for Bucket A templates
- Phase 3 HTML preview generation
- Phase 4 execution bridge

### Planned Flow

`video_spec.json`
-> `renderers.hyperframes.runner`
-> `composition_builder`
-> template/custom scene modules
-> HyperFrames composition output

### Phase 4 Execution Modes

The runner now supports:

- package mode
  Always available. Writes:
  - `index.html`
  - `composition.json`
  - `render_manifest.json`

- render mode
  Executes an external command if configured.

Use env var:

- `HYPERFRAMES_RENDER_CMD`

Supported placeholders:

- `{html}`
- `{output}`
- `{workdir}`
- `{spec}`

Current bridge file:

- `pipeline/hyper_animator.py`

Current backend switch:

- `--renderer hyperframes`

If no external render command is configured, the pipeline leaves a complete
package in `output/hyperframes_build/`.

### Design Rules

- native to HTML/CSS/JS authoring
- no Remotion-specific data assumptions
- no React-first abstractions
- custom scenes and template scenes must share one spec
- `layout_mode` drives full-scene vs overlay behavior, not separate template families
