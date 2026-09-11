# Morpher Planner

## Locked Decisions

- Project name: **Morpher**.
- Morpher is a **design compiler**, not a Figma → Elementor converter.
- Core architecture stays compiler-style: input adapter → Design IR → compiler → output renderer.
- Design IR and compiler behavior must stay independent from Elementor, WordPress, and any single output target.
- Development rule: **small verified slice → real fixture → trace → render → compare → expand**.
- Figma prototype entry path is local Figma plugin → local listener → `storage/figma-import/`.
- The Figma plugin stays thin: select/export/send/status and fidelity-asset export only. Normalization and compilation stay in Morpher.
- Local listener endpoint: `http://127.0.0.1:8767/figma/import`.
- Re-sending the same Figma name replaces its preserved import snapshot; no numbered source duplicates.
- Source scan priority: `storage/figma-import/` then `storage/input/`.
- `storage/figma-import/` is a preserved source repository, not a queue.
- `morpher` is the bulk-processing CLI; there is no `run` subcommand.
- `morpher --force` replaces existing outputs in place.
- Failed ordinary inputs remain available for retry; successful ordinary inputs move to `processed/` only after required outputs succeed.
- Fidelity HTML may use companion assets, but semantic source data remains canonical in the IR.
- Outlined TEXT fidelity SVGs use `svgOutlineText: true` + `useAbsoluteBounds: true`.
- Do not force outlined text SVGs through a second semantic geometry interpretation.
- SVG-backed graphics own their internal paint; CSS controls external layout geometry.
- The CLI is a frontend to Morpher Core, not the permanent product boundary.
- Elementor rendering, asset packaging, Morpher Native, and WordPress integration remain separable responsibilities.
- Normal WordPress administrators edit **content**, not arbitrary layout/structure by default.
- Backup/version/restore safety is a **core** Morpher Native requirement.
- Restore is non-destructive: restoring an old snapshot creates a new current revision; later history remains available.

## Product Architecture Direction

```text
Figma / supported input
        ↓
Input adapter
        ↓
Design IR
        ↓
Layout / semantic compiler
        ↓
Compiled IR
   ├─ Morpher Native
   ├─ Elementor
   └─ Static HTML/CSS
```

Morpher Native is the intended first-party output/runtime direction. Elementor remains an export/integration target and must not dictate compiler architecture.

The intended editing philosophy is:

> **Developers control the design. Editors control the content. Morpher makes it difficult to destroy either.**

## Morpher 1.0 Vision

Morpher 1.0 should be an application around reusable Morpher Core rather than a CLI-only product. Exact desktop/UI technology remains intentionally unlocked.

```text
                 Morpher Core
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
      CLI        Morpher App    future API
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
   Morpher Native         Elementor export
          ↓
   WordPress plugin
```

### Morph as the compilation unit

A **Morph** represents one complete page/template compilation unit. Section-level fixtures are useful for development but must not become the permanent product boundary.

```text
Project: MUU Hotel
│
├─ Morph: Homepage
│  ├─ complete source/design
│  ├─ compiled/semantic representation
│  ├─ native output
│  ├─ optional Elementor document
│  ├─ one optimized page CSS bundle
│  └─ required assets
├─ Morph: Offers
└─ Morph: Contact
```

New compiler/rendering work must therefore avoid assumptions that only one isolated section exists.

### Per-Morph CSS

The target is one compiled/optimized stylesheet per Morph/page. Elementor Free does not need to be the only style-storage mechanism; generated classes and a page-owned stylesheet may preserve fidelity where Elementor controls are insufficient.

### Semantic structure

Semantic decisions belong above individual renderers so Native HTML and Elementor can consume the same intent where supported. Potential targets include `header`, `nav`, `main`, `section`, `article`, `aside`, `footer`, headings, paragraphs, and links/actions. Inference rules must be introduced through deterministic verified slices rather than broad guessing.

## Stable Identity Contract

Current output already uses deterministic source-ID-based CSS classes. Morpher Native should extend this into a universal DOM identity contract.

For Figma source `45:5221`:

```html
<h2
  id="morpher-45-5221"
  class="morpher-45-5221"
  data-morpher-source-id="45:5221"
>
```

Responsibilities:

- DOM `id` → direct JavaScript/editor lookup;
- CSS `class` → rendering selector;
- `data-morpher-source-id` → source/Figma provenance.

### Planned work

- [ ] Emit a deterministic unique `id="morpher-{normalized-source-id}"` on every imported rendered node.
- [ ] Make `data-morpher-source-id` universal rather than text-only.
- [ ] Add renderer invariant/tests rejecting duplicate DOM IDs.
- [ ] Define a Morpher-owned identity for generated nodes that have no Figma source.
- [ ] Keep source identity and Morpher compiled-object identity conceptually separate.

Stable identity will support pinpoint editing, JavaScript behaviors, debugging, content overrides, focused diff previews, and version tracking.

## Font Gatherer / Registry

Production Morpher Native should prefer semantic HTML text when the exact source font is available.

Font source:

```text
storage/fonts/
```

The registry follows a plug-and-play gather/register model:

```text
morpher ...
   ↓
font gatherer
   ↓
scan storage/fonts/
   ↓
refresh registry
   ↓
resolve Figma family/face/weight/style
   ↓
emit @font-face / semantic text
   ↓
execute command
```

Dropping a font into `storage/fonts/` must not require a Morpher restart; the next normal command refreshes discovery. A future long-lived watch/dev mode may rescan on filesystem changes.

Outlined SVG text remains useful for fidelity diagnostics/fallback during transition. SVG remains correct for graphics, logos, and intentionally decorative typography.

### Planned work

- [ ] Add `storage/fonts/` discovery.
- [ ] Read enough font metadata to resolve family/face/weight/style deterministically.
- [ ] Refresh the registry during normal Morpher command execution.
- [ ] Emit `@font-face` declarations for resolved fonts.
- [ ] Add semantic text rendering using resolved fonts.
- [ ] Preserve an outline/fidelity fallback while Native text support matures.

## Morpher Native WordPress Visual Editor

The WordPress plugin is a safe visual **content editor**, not a mini Elementor.

### Admin/editor V1

- [ ] Render the actual Morpher Native page for visual editing.
- [ ] Click/pinpoint an element using deterministic Morpher DOM identity.
- [ ] Edit text.
- [ ] Replace images.
- [ ] Edit button/link labels and URLs.
- [ ] Edit contact information.
- [ ] Consider a safe visibility toggle.
- [ ] Patch preview DOM immediately while editing.
- [ ] Persist edits as content overrides rather than mutating the compiled template.
- [ ] Separate normal admin permissions from developer/advanced controls.
- [ ] Integrate version/backup/restore into the normal editing workflow.

### Content override model

```text
Compiled Morpher Template
        +
WordPress Content Overrides
        ↓
Final Page
```

Example:

```json
{
  "45:5221": {
    "text": "JOIN OUR NEWSLETTER"
  }
}
```

- [ ] Define override schema keyed by stable Morpher/source identity.
- [ ] Apply overrides without mutating compiled source output.
- [ ] Preserve compatible overrides across recompilation when stable identity survives.
- [ ] Provide a safe reset-to-original-design operation.

### Responsive preview

Editor viewport selector:

```text
[ Desktop ] [ Tablet ] [ Mobile ]
```

Preview widths must come from Morpher breakpoint/configuration data, not hardcoded sample widths. The preview canvas should exercise the real generated media queries.

- [ ] Desktop preview.
- [ ] Tablet preview.
- [ ] Mobile preview.
- [ ] Bind preview widths to compiler breakpoint configuration.
- [ ] Reserve breakpoint-specific style editing for developer/advanced tooling.

### Developer tooling — later

These are useful for us/developers but are deliberately not normal admin V1 scope:

- [ ] advanced responsive edits;
- [ ] advanced CSS;
- [ ] structural controls;
- [ ] widget insertion;
- [ ] drag/drop and snapping;
- [ ] richer components such as carousel/navigation/side-menu tooling.

## Backup / Version / Restore System

This is a core safety layer. Semantics are inspired by Git but are **not literal Git** and must not require admins to understand or execute Git.

Conceptual lifecycle:

```text
morpher init
→ create protected baseline when design/page is first imported

morpher add
→ track current state of modified/untracked elements

morpher commit
→ record tracked changes with a custom change message

morpher push
→ create a new full page version under the same backup root
```

The exact CLI/UI mapping may evolve; the lifecycle semantics are what matter.

Conceptual storage:

```text
backup/page-123/
├─ baseline/
├─ v042/
├─ v043/
└─ ...
```

### Retention rules

- `baseline/init` is protected forever.
- Normal full versions use rolling retention; exact threshold is not locked yet.
- A version may be **Mark as Main** and is protected from automatic cleanup while marked.
- Main versions have a hard small limit, likely 2–3; exact number remains unlocked.
- If Main slots are full, the UI must force an explicit choice of which existing Main version to unmark/replace. Never silently unprotect one.
- Version snapshots must include or restorably reference changed assets as well as content/style state.
- Record author, timestamp, custom commit/change summary, and useful diff metadata.
- Autosave/recovery remains separate from proper committed versions.

### Restore behavior

Restore must preserve history:

```text
select old version
      ↓
preview
      ↓
restore
      ↓
create NEW current revision from selected snapshot
```

No destructive rewind.

### Restore preview UX

Desktop/tablet:

```text
┌─────────────────────┬─────────────────────┐
│ CURRENT             │ RESTORE CANDIDATE   │
│ rendered page       │ rendered page       │
└─────────────────────┴─────────────────────┘
```

Use synchronized scrolling where practical.

Mobile:

```text
CURRENT
   ↔ swipe ↔
RESTORE CANDIDATE
```

One full preview at a time is preferred over squeezed columns.

Below the rendered preview, preserve the conventional technical diff summary:

```diff
- old value
+ new value
```

This gives normal admins visual comparison while keeping precise information for developers/experienced editors.

Changed diff entries should be clickable. A lightweight AJAX modal/popup can open a focused A/B rendered comparison for that element. Deterministic DOM IDs let both revision previews jump directly to the same element.

### Planned work

- [ ] Define baseline/version snapshot model.
- [ ] Define asset snapshot/reference behavior.
- [ ] Define rolling retention policy and threshold.
- [ ] Implement protected baseline.
- [ ] Implement Mark as Main with hard slot limit and explicit replacement UX.
- [ ] Record author/timestamp/change message/diff metadata.
- [ ] Add full rendered A/B restore preview.
- [ ] Add synchronized desktop/tablet comparison scrolling.
- [ ] Add mobile swipe A/B comparison.
- [ ] Preserve `- / +` summary below preview.
- [ ] Make changed summary entries clickable.
- [ ] Add focused AJAX A/B element modal.
- [ ] Implement non-destructive restore as a new revision.

## Current Prototype Scope

### Foundation / transport / IR

- [x] Python package/project and storage foundation.
- [x] Adapter registry and source scanner.
- [x] Deterministic processing/output naming and force replacement.
- [x] Local Figma plugin + listener.
- [x] `JSON_REST_V1` import.
- [x] Raster, vector, and outlined-text fidelity asset transport.
- [x] Output-agnostic Design IR with preserved Figma source IDs.
- [x] Free-layout and basic Auto Layout metadata.
- [x] Basic style, clipping, rotation, image, stroke, and typography metadata used by verified fixtures.
- [x] Hidden Figma subtrees pruned from IR.

### HTML/CSS fidelity renderer

- [x] Standalone HTML + companion CSS.
- [x] Deterministic source-ID classes.
- [x] Free-layout absolute reconstruction.
- [x] Flexbox foundations for Auto Layout.
- [x] Raster fills and opacity.
- [x] SVG icons/vectors and composite vector assets.
- [x] Outlined TEXT fidelity assets with semantic text retained.
- [x] Multiline/leading-whitespace handling.
- [x] Frame clipping.
- [x] Quarter-turn geometry handling.
- [x] Divider rendering.
- [x] Shape stroke rendering.
- [x] Inspect traces and regression tests for verified behavior.

### Responsive compiler / Elementor

Responsive compilation is active work. Elementor is supported as an output target and its renderer should consume compiled layout rather than drive compiler architecture.

Current responsive pipeline conceptually includes layout compilation, spatial relationship resolution, flow-group stabilization, ownership/overlay resolution, and generated-wrapper pruning before renderer-specific output.

- [x] Responsive compiler foundations.
- [x] Region/flow grouping foundations used by current fixtures.
- [x] Generated-wrapper pruning foundation.
- [x] Elementor renderer foundation exists on the active development path.
- [ ] Continue real-fixture responsive compiler hardening.
- [ ] Preserve semantic/editable Elementor mappings where practical.
- [ ] Keep Elementor-only behavior isolated from shared compiler logic.
- [ ] Continue validating generated output against real Elementor behavior.

## Known Fidelity Work

### Newsletter decorative vector `45:5219`

Current diagnosis:

- Figma node bounding box is roughly `986 × 1129`.
- Visible render bounds are roughly `987 × 398`.
- IR/CSS correctly carries the Figma absolute bounding geometry.
- Current plain vector SVG export likely crops its SVG canvas to visible artwork.
- The renderer then places that cropped SVG into the much taller IR box using `object-fit: contain`, producing the wrong vertical placement.

This is an exporter/renderer geometry-contract mismatch, not evidence that IR should switch to `absoluteRenderBounds`.

Next experiment/fix:

```js
vector.exportAsync({
  format: "SVG",
  useAbsoluteBounds: true
})
```

Goal: SVG canvas == Figma `absoluteBoundingBox` == IR geometry.

- [ ] Test `useAbsoluteBounds: true` on raw vector export.
- [ ] Re-render Newsletter and visually verify `45:5219`.
- [ ] Add regression coverage once verified.
- [ ] Do not patch IR to render bounds unless evidence disproves the exporter contract.

## Immediate Sequence

Do not let the new product architecture interrupt the active compiler verification order.

1. **Finish fidelity contracts** — first Newsletter decorative vector `45:5219`.
2. **Continue responsive compiler** hardening against real fixtures.
3. **Font gatherer/registry** under `storage/fonts/`.
4. **Semantic HTML text** using registered exact fonts, with fidelity fallback retained.
5. **Morpher Native renderer** and whole-page Morph output.
6. **WordPress Visual Editor** with pinpoint editing and content overrides.
7. **Version/backup/restore** integrated as core editor safety, including rendered A/B preview and technical diff.
8. **Developer tools later** — structural editing, widgets, snapping, advanced responsive/CSS controls.

## Later / Optional Inputs

- [ ] SVG adapter.
- [ ] PNG adapter.
- [ ] JPG/JPEG adapter.
- [ ] PDF adapter.
- [ ] Figma REST adapter.
- [ ] Published Figma plugin workflow.

## Later / Optional Outputs / Integration

- [ ] Morpher application/UI.
- [ ] Whole-page Morph compilation as normal workflow.
- [ ] Per-Morph CSS optimization/bundling.
- [ ] Morpher Native output/runtime.
- [ ] Morpher WordPress Visual Editor / bridge.
- [ ] Automated Media Library integration.
- [ ] Optional Elementor deployment/integration automation.
- [ ] Gutenberg renderer.
- [ ] React renderer.
- [ ] Tailwind renderer.
- [ ] Other renderers through the same output-agnostic IR.

## Prototype Maturity

Morpher should currently be described as an **advanced prototype / early product foundation**.

It is beyond the initial feasibility question: real Figma designs can be transported, normalized, inspected, rendered, and compiled through meaningful parts of the pipeline. It is not yet alpha/production-ready because important fidelity contracts are still being discovered, responsive compilation is incomplete, and Morpher Native / font registry / WordPress editing are not implemented yet.

The fidelity HTML path remains the diagnostic/reference path and should not be destabilized while the Native/editor architecture is introduced.