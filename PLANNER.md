# Morpher Planner

## Locked Decisions

- Project name: **Morpher**.
- Core architecture is compiler-style: input adapter → Design IR → compiler → output renderer.
- The Design IR must stay independent from Elementor and any specific output target.
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

- [ ] Create Python package/project configuration.
- [ ] Create storage directory structure.
- [ ] Add source-path and output-path helpers.
- [ ] Add adapter protocol/base interface.
- [ ] Add input adapter registry.
- [ ] Add source scanner using registered extensions.
- [ ] Add deterministic processed/output naming.
- [ ] Add processing result model.
- [ ] Add batch processor skeleton.
- [ ] Add `--force` policy foundation.
- [ ] Add unit tests for storage/scanner/naming behavior.

### Phase 2 — Figma JSON + Design IR

- [ ] Add `FigmaJsonAdapter`.
- [ ] Define output-agnostic Design IR nodes.
- [ ] Preserve original Figma node IDs for debugging.
- [ ] Normalize basic Figma frame/group/text/image data.
- [ ] Support basic Auto Layout:
  - [ ] horizontal / vertical direction
  - [ ] gap
  - [ ] padding
  - [ ] alignment
  - [ ] fixed / hug / fill sizing
- [ ] Support basic styling:
  - [ ] solid backgrounds
  - [ ] typography
  - [ ] border
  - [ ] border radius
  - [ ] opacity
- [ ] Add fixture-based tests.

### Phase 3 — HTML/CSS Renderer

- [ ] Generate semantic HTML from Design IR.
- [ ] Generate scoped CSS.
- [ ] Keep inline styles minimal.
- [ ] Support nested containers.
- [ ] Support text and image output.
- [ ] Produce `{name}.html` + `{name}.css` together.
- [ ] Add renderer tests.

### Phase 4 — Elementor Renderer

- [ ] Generate Elementor-compatible template JSON.
- [ ] Map IR container → Elementor Container.
- [ ] Map text → Heading or Text Editor using deterministic rules.
- [ ] Map image → Image widget.
- [ ] Keep Elementor-only details isolated inside renderer code.
- [ ] Validate generated template JSON against real Elementor import behavior.

### Phase 5 — Fidelity

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
- [ ] Figma plugin exporter workflow.

### Later / Optional Outputs

- [ ] Gutenberg renderer.
- [ ] React renderer.
- [ ] Tailwind renderer.
- [ ] Other renderers through the same output-agnostic IR.

## First Prototype Success Test

Input design:

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

The first milestone is successful when both outputs are generated from the same Design IR and visually represent the source frame closely enough to validate the architecture.
