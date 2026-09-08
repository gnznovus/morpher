# Morpher Planner

## Locked Decisions

- Project name: **Morpher**.
- Core architecture is compiler-style: input adapter → Design IR → compiler → output renderer.
- The Design IR must stay independent from Elementor and any specific output target.
- Development rule: **small verified slice → real fixture → trace → render → compare → expand**.
- Figma prototype entry path is **local Figma plugin → local Morpher listener → `storage/figma-import/`**.
- The Figma plugin stays thin: select/export/send/status and fidelity-asset export only. Normalization and compilation stay in Morpher.
- Local listener endpoint: `http://127.0.0.1:8767/figma/import`.
- Re-sending the same Figma name replaces that import snapshot in place and reports that it was replaced; no numbered duplicates.
- Default source scan priority:
  1. `storage/figma-import/`
  2. `storage/input/`
- `storage/figma-import/` is a preserved source repository, not a queue.
- Successfully processed files from `storage/input/` move to `storage/processed/` with `_P` added before the extension.
- Output naming:
  - `storage/output/html/{name}.html`
  - `storage/output/html/{name}.css`
  - `storage/output/elementor/{name}_template.json`
- Existing output is skipped by default.
- Bulk-processing CLI is `morpher`; there is no `run` subcommand.
- `morpher --force` replaces existing outputs in place; it must not create numbered duplicates.
- Source files should only move to `processed/` after all required outputs succeed.
- Failed inputs stay in `input/` for retry.
- No ZIP/RAR input packaging for the prototype.
- Primary Figma structural input is JSON.
- Figma REST support is optional/later; preserved imports should minimize repeated API calls.
- Fidelity HTML may use companion assets, but semantic source data remains canonical in the IR.
- Figma TEXT keeps semantic characters/typography while fidelity HTML may use a companion outlined SVG keyed by the same source ID.
- Outlined text export uses `svgOutlineText: true` and `useAbsoluteBounds: true` so the full Figma text-node canvas, including meaningful empty geometry, is preserved.
- **Do not wrap outlined text SVGs and force-fit them into a second semantic geometry box.** The direct SVG element is the verified fidelity path.
- SVG-backed icons own their internal fill/stroke/opacity. CSS must not repaint vector fill as an element background.

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
- [x] Add `--force` replacement policy.
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
- [x] Send real Figma frames to Morpher end-to-end.
- [x] Transport raster image assets referenced by image fills.
- [x] Transport SVG vector assets keyed by Figma source ID.
- [x] Transport outlined TEXT fidelity SVGs keyed by Figma source ID.
- [x] Preserve full TEXT node bounds during outlined SVG export.

### Phase 3 — Figma JSON + Design IR

- [x] Add `FigmaJsonAdapter`.
- [x] Define output-agnostic Design IR nodes.
- [x] Preserve original Figma node IDs for debugging and asset mapping.
- [x] Normalize frame/group/text/image/shape/line/vector data used by verified fixtures.
- [x] Support basic Auto Layout:
  - [x] horizontal / vertical direction
  - [x] gap
  - [x] padding
  - [x] alignment foundations
  - [x] fixed / hug / fill sizing
- [x] Support current basic styling:
  - [x] solid backgrounds
  - [x] typography metadata
  - [x] basic stroke data for dividers
  - [x] border radius metadata
  - [x] opacity
  - [x] image-fill opacity
  - [x] clipping metadata
  - [x] quarter-turn rotation metadata
- [x] Detect vector-only FRAME/GROUP composites for single-asset SVG export.
- [x] Warn on unsupported node types instead of silently dropping them.
- [x] Add fixture-style tests based on fields observed in real plugin output.
- [ ] Expand regression fixtures for additional unsupported/edge-case Figma structures without publishing private design payloads unintentionally.

### Phase 4 — HTML/CSS Fidelity Renderer

- [x] Generate standalone HTML from Design IR.
- [x] Generate companion CSS.
- [x] Use deterministic source-ID-based class names.
- [x] Support nested containers.
- [x] Support text, image, shape, divider, and icon output used by verified fixtures.
- [x] Reconstruct free-layout children with absolute geometry relative to their parent.
- [x] Render Auto Layout using flexbox foundations.
- [x] Copy/import raster and SVG assets into source-specific HTML asset directories.
- [x] Render image fills with `object-fit: cover` and preserved image opacity.
- [x] Render SVG icons with `object-fit: contain`.
- [x] Keep SVG internal fill/stroke authoritative; do not emit vector fill as CSS background.
- [x] Render outlined TEXT SVG fidelity assets when available.
- [x] Preserve semantic text as fallback and future output data.
- [x] Preserve explicit multiline text behavior.
- [x] Preserve leading-whitespace fidelity through absolute-bound text SVG export.
- [x] Reconstruct frame clipping with `overflow: hidden`.
- [x] Reconstruct quarter-turn free-layout rotation while avoiding divider double-rotation.
- [x] Produce `{name}.html` + `{name}.css` together.
- [x] Add renderer regression tests for text-outline and SVG-icon behavior.
- [x] Verify the renderer against multiple substantially different real Figma sections and additional random-frame testing.

### Phase 5 — Inspection + Bulk Workflow

- [x] Add rich `morpher-inspect` trace output.
- [x] Keep inspect trace ownership separate from normal render output.
- [x] Add `morpher-render` for direct rendering of a source.
- [x] Add `morpher` bulk processing CLI.
- [x] Add `morpher --force` replacement flow.
- [x] Verify bulk processing across multiple preserved Figma imports.

### Phase 6 — Elementor Renderer

- [ ] Generate Elementor-compatible template JSON.
- [ ] Map IR container → Elementor Container.
- [ ] Map semantic text → Heading or Text Editor using deterministic rules.
- [ ] Map image → Image widget.
- [ ] Map preserved typography without depending on fidelity SVG text.
- [ ] Keep Elementor-only details isolated inside renderer code.
- [ ] Validate generated template JSON against real Elementor import behavior.

### Phase 7 — Fidelity Expansion / Compiler

- [ ] Add shadows.
- [ ] Add gradients.
- [ ] Expand stroke/border support beyond current divider behavior.
- [ ] Expand transforms beyond verified quarter turns.
- [ ] Add screenshot-based visual comparison.
- [ ] Add mismatch reporting.
- [ ] Add semantic layout inference above the raw fidelity reconstruction layer.
- [ ] Add responsive compilation.
- [ ] Add deterministic warnings for known fragile source patterns where useful.

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

## Verified Prototype Checkpoint

Current transport and fidelity path:

```text
Figma selected frame
  ↓ JSON_REST_V1 + raster/vector/text fidelity assets
Morpher plugin
  ↓ localhost POST
Morpher listener
  ↓
storage/figma-import/{frame-name}.json + assets
  ↓
FigmaJsonAdapter
  ↓
Design IR
  ↓
HTML/CSS fidelity renderer
```

Verified real-world reconstruction now covers multiple different page sections rather than one development fixture. The tested set includes free-layout compositions, images, opacity, clipping, dividers, raw and composite vectors, icons, multiline text, custom-font text through outlined SVG fidelity assets, and source designs containing leading-whitespace layout tricks.

Two important fidelity bugs are closed:

1. **Outlined text bounds** — normal outlined SVG export could crop empty text geometry such as leading whitespace. Exporting with `useAbsoluteBounds: true` preserves the original Figma text-node canvas without changing the verified direct-SVG renderer.
2. **Vector fill backgrounds** — Figma vector fill metadata was being emitted as a CSS background on SVG-backed `<img>` elements, producing solid rectangles over arrows/icons. SVG icons now retain authority over their internal paint while CSS controls external geometry only.

The current checkpoint demonstrates a strong Figma → fidelity HTML path across the verified fixture set. It does **not** imply universal support for every Figma node, effect, transform, responsive behavior, or design pattern.

## Next Slice

Keep the verified fidelity path stable. Expand only through small real fixtures that expose a missing Figma feature, then trace → render → compare before generalizing the rule.

Near-term candidates:

1. Add/strengthen regression fixtures for newly solved text-bound and vector-fill cases.
2. Choose the next unsupported Figma styling/transform feature from real evidence rather than speculation.
3. Begin the semantic/responsive compiler layer once raw reconstruction coverage is sufficient.
4. Start the Elementor renderer from preserved semantic IR, not from fidelity SVG output.
