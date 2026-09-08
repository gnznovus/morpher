# Morpher Planner

## Locked Decisions

- Project name: **Morpher**.
- Core architecture is compiler-style: input adapter → Design IR → compiler → output renderer.
- The Design IR must stay independent from Elementor and any specific output target.
- Figma prototype entry path is **local Figma plugin → local Morpher listener → `storage/figma-import/`**.
- The Figma plugin stays thin: select/export/send/status only. All normalization and compilation stays in Morpher.
- Local listener default: `http://127.0.0.1:8767/figma/import`.
- Re-sending the same Figma name replaces that import snapshot in place and reports that it was replaced; no numbered duplicates.
- Default source scan priority:
  1. `storage/figma-import/`
  2. `storage/input/`
- `storage/figma-import/` is preserved for reuse and debugging.
- Successfully processed files from `storage/input/` move to `storage/processed/` with `_P` added before the extension.
- Output naming:
  - `storage/output/html/{name}.html`
  - `storage/output/html/{name}.css`
  - `storage/output/elementor/{name}_template.json`
- Existing output is skipped by default.
- `--force` replaces existing outputs in place; it must not create numbered duplicates.
- Source files should only move to `processed/` after all required outputs succeed.
- Failed inputs stay in `input/` for retry.
- No ZIP/RAR input packaging for the prototype.
- Primary Figma structural input is JSON.
- Figma REST support is optional/later; preserved imports should minimize repeated API calls.

## Prototype Scope

### Phase 1 — Foundation

- [x] Create Python package/project configuration.
- [x] Create storage directory structure.
- [x] Add source-path and output-path helpers.
- [x] Add adapter protocol/base interface.
- [x] Add input adapter registry.
- [x] Add source scanner using registered extensions.
- [x] Add deterministic processed/output naming.
- [x] Add processing result model.
- [x] Add batch processor skeleton.
- [x] Add `--force` policy foundation.
- [x] Add CI smoke coverage.

### Phase 2 — Figma Plugin + Local Listener

- [x] Add local Figma development plugin scaffold.
- [x] Add minimal plugin UI with **Send selected node to Morpher**.
- [x] Export selected node using `JSON_REST_V1`.
- [x] POST export to local Morpher listener.
- [x] Add listener endpoint at `/figma/import`.
- [x] Save payload into `storage/figma-import/`.
- [x] Use safe deterministic filenames and replace same-name snapshots in place.
- [x] Add listener validation and storage tests.
- [x] Add `morpher-listen` CLI command.
- [x] Verify the development plugin loads in Figma Desktop.
- [x] Send one real frame from Figma to Morpher end-to-end.
- [ ] Preserve that real payload as the first compiler fixture.

### Phase 3 — Figma JSON + Design IR

- [x] Add `FigmaJsonAdapter`.
- [x] Define output-agnostic Design IR nodes.
- [x] Preserve original Figma node IDs for debugging.
- [x] Normalize basic Figma frame/group/text/image data.
- [ ] Support basic Auto Layout:
  - [x] horizontal / vertical direction
  - [x] gap
  - [x] padding
  - [ ] alignment
  - [x] fixed / hug / fill sizing
- [ ] Support basic styling:
  - [x] solid backgrounds
  - [x] typography
  - [ ] border
  - [x] border radius
  - [x] opacity
- [x] Warn on unsupported node types instead of silently dropping them.
- [x] Add fixture-style tests based on fields observed in real plugin output.
- [ ] Add the full real `Homepage-Hide.json` payload as a regression fixture.

### Phase 4 — HTML/CSS Renderer

- [ ] Generate semantic HTML from Design IR.
- [ ] Generate scoped CSS.
- [ ] Keep inline styles minimal.
- [ ] Support nested containers.
- [ ] Support text and image output.
- [ ] Produce `{name}.html` + `{name}.css` together.
- [ ] Add renderer tests.

### Phase 5 — Elementor Renderer

- [ ] Generate Elementor-compatible template JSON.
- [ ] Map IR container → Elementor Container.
- [ ] Map text → Heading or Text Editor using deterministic rules.
- [ ] Map image → Image widget.
- [ ] Keep Elementor-only details isolated inside renderer code.
- [ ] Validate generated template JSON against real Elementor import behavior.

### Phase 6 — Fidelity

- [ ] Add SVG support.
- [ ] Add image/SVG asset handling and deduplication.
- [ ] Add shadows and gradients.
- [ ] Improve absolute-positioned layer handling.
- [ ] Add screenshot-based visual comparison.
- [ ] Add mismatch reporting.
- [ ] Add responsive compilation.

### Later / Optional Inputs

- [ ] SVG adapter.
- [ ] PNG adapter.
- [ ] JPG/JPEG adapter.
- [ ] PDF adapter.
- [ ] Figma REST adapter.
- [ ] Published Figma plugin workflow.

### Later / Optional Outputs

- [ ] Gutenberg renderer.
- [ ] React renderer.
- [ ] Tailwind renderer.
- [ ] Other renderers through the same output-agnostic IR.

## First Prototype Success Test

Transport proof:

```text
Figma selected frame
  ↓ JSON_REST_V1
Morpher plugin
  ↓ localhost POST
Morpher listener
  ↓
storage/figma-import/{frame-name}.json
```

Compiler proof after transport is verified:

```text
Frame
└─ vertical auto-layout
   ├─ heading
   ├─ paragraph
   └─ image
```

Expected outputs:

```text
HTML/CSS
```

and:

```text
Elementor Container
├─ Heading
├─ Text Editor
└─ Image
```

The transport milestone succeeds when a real selected Figma frame reaches `storage/figma-import/` with no manual file movement. The compiler milestone succeeds when both outputs are generated from the same Design IR and visually represent the source frame closely enough to validate the architecture.
