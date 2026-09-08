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
- The CLI is a frontend to Morpher Core, not the permanent product boundary. Core compiler behavior must remain reusable by a future application/UI.
- Elementor rendering, asset packaging, and WordPress deployment/integration must remain separable responsibilities so later automation does not require rewriting the compiler.

## Morpher 1.0 Vision

> **Important:** This section records the intended Morpher 1.0 product direction so today's foundations do not block it. These items are **not the current implementation scope** unless they also appear in the active prototype phases below.

The intended 1.0 direction is a Morpher application rather than a CLI-only tool. The exact desktop/UI technology is intentionally **not locked yet**; candidates such as Tk/ttk or another suitable application framework can be evaluated when the UI requirements are clearer.

Conceptual architecture:

```text
                 Morpher Core
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
      CLI        Morpher App    future API
                     │
                     ↓
             WordPress connection
                     │
                     ↓
          Morpher WordPress Bridge
                     │
              WordPress / Elementor
```

### Morpher App

Planned responsibilities include:

- Provide a real application/UI around Morpher Core.
- Orchestrate compilation, projects, generated artifacts, CSS, and assets without moving compiler logic into the UI.
- Perform heavier processing/optimization in Python where appropriate rather than moving compiler/optimizer responsibilities into the WordPress plugin.
- Connect to WordPress through the Morpher WordPress Bridge when automated deployment/integration is implemented.

### Morph as the 1.0 Compilation Unit

The intended 1.0 product should be able to morph an **entire page design in one operation**, rather than requiring the user to convert the page section by section.

Current section-by-section Figma imports are development fixtures used to prove individual capabilities safely. They must not define the permanent product boundary.

Conceptually:

```text
Project: MUU Hotel
│
├─ Morph: Homepage
│  ├─ entire Homepage design/source
│  ├─ compiled/semantic representation
│  ├─ Elementor document
│  ├─ one optimized Homepage CSS bundle
│  └─ required optimized assets
│
├─ Morph: Offers
│  └─ ...
│
└─ Morph: Contact
   └─ ...
```

A **Morph** is intended to represent one complete page/template compilation unit. Sections remain structural children and useful development fixtures, while the Morph owns the complete generated page/template artifacts.

Foundation constraint: new compiler, Elementor, CSS, and asset work should avoid assumptions that only one isolated section exists. It should remain possible for a Morph root to contain and compile many sections together.

### Per-Morph CSS

The 1.0 direction is **one compiled/optimized stylesheet per Morph/page**, not one stylesheet per tiny section and not necessarily one site-wide shared stylesheet.

Conceptually:

```text
Homepage Morph
      ↓
all page/section style rules
      ↓
Morpher App / Python CSS optimization
      ↓
homepage.css
```

The Morpher App may later normalize and optimize duplicate/repeated CSS declarations across sections/elements within that Morph and produce one final page-owned stylesheet. The exact optimization algorithm and user-facing controls are intentionally deferred.

Elementor Free does not need to be treated as the only style storage mechanism. Morpher-generated Elementor elements can carry stable classes, while the Morph stylesheet supplies fidelity styling that is unsuitable or unavailable through Elementor Free controls. Native Elementor settings can still be used where they improve editability.

Human-facing generated classes should eventually be more descriptive than raw `morpher-{source-id}` debug classes. A candidate convention is:

```text
{name}-{id}
```

for example `offers-arrow-left-45-5253`. The exact naming/sanitization rules are not locked yet. Source IDs, Elementor internal IDs, and human-facing CSS identities should remain conceptually separate so one identifier does not have to serve every purpose.

### Semantic Structure

The 1.0 compiler should support semantic output rather than treating every structural container as a generic `div` forever. Semantic decisions should live above individual output renderers so HTML and Elementor can consume the same intent where supported.

Potential semantic targets include `header`, `nav`, `main`, `section`, `article`, `aside`, `footer`, appropriate heading levels, paragraphs, and links/actions. Exact inference rules are deferred and should be introduced through verified deterministic slices rather than guessed globally.

### Morpher WordPress Bridge

Morpher 1.0 is intended to include a custom WordPress plugin acting as the controlled bridge between the Morpher application and WordPress/Elementor.

The bridge is expected to eventually support operations such as:

- authenticated Morpher ↔ WordPress communication;
- WordPress Media Library / asset integration;
- Elementor template/page integration;
- receiving/registering Morpher-generated per-Morph CSS and ensuring it is loaded where required;
- site information and operations required by Morpher workflows.

The WordPress plugin should remain relatively thin where practical: WordPress/Elementor-specific installation, registration, storage, loading, and communication belong there, while compilation and heavier CSS/asset optimization can remain in the Python Morpher App/Core.

Exact endpoints, authentication, permissions, package format, CSS registration strategy, and Elementor integration mechanisms are **not designed yet**. The bridge must be explicit and controlled rather than Morpher directly coupling the compiler to WordPress filesystem/database internals.

Internal codename: **definitely-not-a-backdoor**. 😹

Additional Morpher 1.0 ideas will be appended here as they are remembered and defined.

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

Current prototype workflow is deliberately semi-manual. Morpher generates an Elementor template plus a human-friendly asset package; a human imports the template, uploads packaged media to WordPress, and manually binds the appropriate Media Library item in Elementor image/background controls. WordPress REST/bridge automation is deferred until the renderer itself is proven.

Start-small verification order:

1. Container → Heading.
2. Container → Heading + Text.
3. Container → Heading + Text + Image with manual Media Library binding.
4. Expand nested containers, layout, styling, and harder fidelity only after the smaller slices import and remain editable.

- [ ] Add reproducible local Docker Compose WordPress testbed with Elementor Free for real import testing.
- [ ] Create/export a tiny real Elementor template as a golden structural reference.
- [ ] Generate Elementor-compatible template JSON from Design IR rather than scraping generated HTML.
- [ ] Map IR container → Elementor Container.
- [ ] Map semantic text → Heading or Text Editor using deterministic rules.
- [ ] Map image → Image widget with manual media binding in the current prototype.
- [ ] Package required Elementor assets alongside the generated template using useful deterministic names.
- [ ] Avoid fake WordPress URLs, local output paths, and hard-coded WordPress attachment IDs in portable generated templates.
- [ ] Map preserved typography without depending on fidelity SVG text.
- [ ] Keep Elementor-only details isolated inside renderer code.
- [ ] Validate generated template JSON against real Elementor import behavior and confirm imported elements remain editable.

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

### Later / Optional Outputs / Integration

- [ ] Morpher application/UI.
- [ ] Whole-page Morph compilation as the normal product workflow.
- [ ] Per-Morph CSS optimization/bundling in Python.
- [ ] Semantic structure compilation shared by HTML and Elementor outputs.
- [ ] Morpher WordPress Bridge plugin (`definitely-not-a-backdoor`).
- [ ] Automated WordPress Media Library integration through the bridge/WordPress APIs.
- [ ] Per-Morph CSS registration/enqueue through the bridge.
- [ ] Automated Elementor template/page deployment through the bridge where appropriate.
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

Enter the Elementor phase without disturbing the verified Figma → HTML fidelity path.

Immediate sequence:

1. Add the minimal Docker Compose WordPress + Elementor Free testbed.
2. Manually create/export a tiny Elementor Container → Heading template and preserve it as the first golden reference.
3. Implement the smallest Elementor renderer slice from Design IR and prove its generated JSON imports successfully and remains editable.
4. Add semantic text, then image widgets and packaged assets with manual WordPress Media Library binding.
5. Expand one verified Elementor feature at a time using the same small-fixture → import → inspect → compare loop.

WordPress REST/bridge automation and the broader Morpher 1.0 App/Morph workflow are intentionally deferred. The current goal is to prove portable Elementor artifacts first while keeping the foundations compatible with the documented 1.0 direction.
