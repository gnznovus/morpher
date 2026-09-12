# Morpher Planner

## Locked Decisions

- Project name: **Morpher**.
- Morpher is a **design compiler**, not a converter tied to one builder or framework.
- Core architecture stays compiler-style: input adapter → Design IR → compiler → output renderer.
- Design IR and compiler behavior stay independent from Elementor, WordPress, and any single output target.
- Development rule: **small verified slice → real fixture → trace → render → compare → expand**.
- Elementor is the primary WordPress production target.
- Fidelity is the visual reference and responsive-triage target.
- Production deployment is a separate responsibility from compilation: `morpher` compiles; `morpher-deploy` deploys generated Elementor output.
- The WordPress importer has one canonical processing path. Manual admin processing remains a fallback/debug path; future automation should call the same importer rather than duplicate it.
- Whole-page understanding includes **Header Section**, **Body**, and **Footer Section**.
- A Header Section is not the same thing as Navigation; Navigation is a component within it.

### Responsive principles

> **If it flows, let it flow. If it’s absolute, make it fluid.**

> **Preserve the source relationship first. Introduce structural responsive transformation when the composition requires it.**

> **Structural and spatial responsive behavior can coexist within the same section.**

## Product Architecture Direction

```text
Figma / supported input
        ↓
Input adapter
        ↓
Design IR
        ↓
Fidelity
visual validation + responsive triage
        ↓
Responsive / semantic compilation
        ↓
Elementor
editable WordPress production output
        ↓
morpher-deploy
        ↓
Morpher WordPress importer
        ↓
Elementor Library
```

Renderer-specific behavior must not dictate shared compiler architecture.

## Elementor Production Milestones

### Production asset pipeline

- [x] Keep text nodes out of Elementor media asset collection.
- [x] Convert eligible vector graphics into transparent WebP production derivatives.
- [x] Preserve raster production assets.
- [x] Keep atomic visual graphics as single editable image widgets where appropriate.
- [x] Use deterministic/cached asset handling through the existing asset subsystem.

### Image frame fidelity

- [x] Preserve source image scale mode in Design IR.
- [x] Compile source `FILL` images with authored frame width and height.
- [x] Apply production cover behavior for `FILL` images.
- [x] Emit both Elementor layout width and Image Style width so the rendered image is constrained to the authored frame.
- [x] Verify the generic fix against multiple real compositions.

### Spatial normalization

- [x] Normalize quarter-turn text geometry before Elementor rendering.
- [x] Normalize rotated divider geometry while preserving intended composition.
- [x] Keep rotated labels editable rather than collapsing them into graphics.
- [x] Retain conservative guards against decorative backing surfaces becoming semantic row content.

### Visual-marker row reconstruction

- [x] Reconstruct contact-style visual rail + multiline text walls into explicit editable rows.
- [x] Support small ellipse markers for amenity/bullet rows.
- [x] Use marker geometry to preserve wrapped continuation lines within one logical item.
- [x] Prevent neighboring marker rails from claiming each other's text columns.
- [x] Use start alignment for reconstructed contact/amenity rows.
- [x] Preserve paragraph spacing metadata used by row reconstruction.
- [ ] Defer exact authored line-wrap matching until repeated fixtures justify a generic width/fidelity improvement.

### Deferred compact control

- [ ] Compact graphic + label / atomic layout grouping still has an Elementor wrapping edge case. Keep parked until higher-value work is complete.

## WordPress Deployment — MVP GREEN

The local deployment MVP is verified end-to-end.

```text
morpher
→ Elementor template + assets
→ morpher-deploy
→ plugin deployments/<slug>/
→ WordPress Morpher admin processing
→ assets copied to uploads/morpher-assets/<slug>/
→ asset references rewritten
→ Elementor Library entry created/updated
→ template available for insertion
```

### CLI

- [x] Separate `morpher-deploy` executable.
- [x] Bare command performs bulk deployment.
- [x] Friendly target resolution supports bare names, optional extension, template suffix variants, and valid Elementor output paths.
- [x] Strictly constrain deployment resolution to Elementor output.
- [x] Deterministic build hash for template + assets.
- [x] Skip unchanged staged/deployed builds by default.
- [x] `--force` intentionally re-stages while preserving normal validation.

### WordPress importer

- [x] Stage template, manifest, and assets into the Morpher plugin deployment directory.
- [x] Copy production assets into WordPress uploads.
- [x] Rewrite staged asset references to WordPress upload URLs.
- [x] Create/update Elementor Library entries with Morpher identity/build metadata.
- [x] Write deployment status including imported/updated/skipped/failed state and Elementor template ID.
- [x] Verify imported templates appear in Elementor Library and assemble with assets/content automatically.
- [x] Fix plugin ownership so font rendering cannot overwrite the deployment-capable plugin runtime.

### WordPress admin

- [x] Morpher admin page.
- [x] Manual **Process staged deployments** action.
- [x] Deployment status table.
- [x] Keep manual processing as fallback/debug path.
- [ ] Add explicit re-deploy workflow for a previously removed Elementor Library entry without requiring the full staging sequence again.
- [ ] Automate the import trigger from `morpher-deploy` while reusing the same canonical importer.
- [ ] Consider REST transport after the local/manual workflow is stable.

## CLI Ergonomics

- [x] `morpher` supports bulk processing with no target.
- [x] `morpher` accepts friendly source targets such as bare names and optional `.json` extension.
- [x] Resolve friendly targets inside `figma-import/` and `input/` only.
- [x] Preserve source priority: `figma-import/` before `input/`.
- [x] Reject traversal/arbitrary external paths.
- [x] `morpher-deploy` provides matching friendly-target ergonomics for Elementor output.

## Font Registry / WordPress Font Bridge

- [x] Font source discovery foundation.
- [x] Font metadata parsing and deterministic registry/grouping.
- [x] Cache-aware resolution.
- [x] Design IR font intent bridge.
- [x] Production font packaging foundation.
- [x] Missing-font diagnostics propagated to generated output/CLI.
- [x] Font renderer ownership separated from the main WordPress plugin runtime.
- [ ] Continue hardening packaging and edge cases against real font collections.

## Responsive Compilation

Current verified section work includes Discovery and Destination, with Offers substantially validated apart from deferred margin polish. Happenings remains active responsive-structure work.

Important current principle from Happenings investigation:

> Backing-surface geometry may define a visual region without participating as semantic collision/flow content.

- [x] Discovery responsive section validation.
- [x] Destination responsive section validation.
- [x] Offers responsive section validation, excluding deferred margin polish.
- [ ] Resume Happenings structural reconstruction using backing-surface-as-region behavior.
- [ ] Harden responsive classification against diverse real fixtures.
- [ ] Preserve source relationships when simple adaptation is sufficient.
- [ ] Promote layouts to structural responsive behavior where required.
- [ ] Support hybrid sections without unnecessary reconstruction.

## Current Prototype Scope

### Foundation / transport / IR

- [x] Python package/project and storage foundation.
- [x] Adapter registry and source scanner.
- [x] Deterministic processing/output naming and force replacement.
- [x] Local design-input transport foundation.
- [x] Design JSON import foundation.
- [x] Raster and vector asset transport.
- [x] Output-agnostic Design IR with preserved source identity.
- [x] Free-layout and Auto Layout foundations.
- [x] Style, clipping, rotation, image scale mode, stroke, ellipse, paragraph spacing, and typography metadata used by verified fixtures.
- [x] Hidden source subtrees pruned from IR.

### Fidelity

- [x] Visual-reference renderer foundation.
- [x] Deterministic source-based identity/classes.
- [x] Free-layout and Auto Layout foundations.
- [x] Raster/vector rendering, clipping, rotation, multiline text, dividers, and shape strokes.
- [ ] Harden fluid responsive Fidelity as the normal visual-reference behavior.
- [ ] Expand responsive triage across diverse section types.

### Elementor

- [x] Elementor renderer foundation.
- [x] Editable production image widgets with verified authored `FILL` frames.
- [x] WebP production vector asset path.
- [x] Exact-font WordPress bridge foundation.
- [x] Contact/amenity marker-row reconstruction.
- [x] Local WordPress deployment MVP verified end-to-end.
- [ ] Continue validating generated output against real Elementor behavior.
- [ ] Reduce unnecessary structural reconstruction.
- [ ] Automate deployment triggering after staging.

### Semantic / framework-neutral output

- [x] Independent renderer foundation.
- [x] Typography/font packaging foundation.
- [ ] Expand semantic element selection and validation.
- [ ] Keep this target independent from WordPress/Elementor concerns.

## Immediate Sequence

1. **Rest / checkpoint after deployment + image + amenities milestone.**
2. **Resume Happenings responsive structure** with backing surfaces defining regions without contaminating semantic flow.
3. **Add re-deploy behavior** to the Morpher WordPress admin workflow.
4. **Automate `morpher-deploy` import triggering** while keeping the manual button as fallback.
5. **Continue real-design Elementor validation** and only generalize fidelity issues when repeated evidence supports it.
6. **Expand whole-page understanding** across Header Section, Body, and Footer Section.
7. **Harden identity, fonts, assets, and output validation** across targets.

## Later / Optional

- [ ] Additional input adapters.
- [ ] Morpher application/UI.
- [ ] Whole-page Morph compilation as normal workflow.
- [ ] Per-Morph output optimization/bundling.
- [ ] Gutenberg renderer.
- [ ] Framework-oriented renderers/integrations.

## Prototype Maturity

Morpher should currently be described as an **advanced prototype / early product foundation**.

The project can transport, normalize, inspect, compile, package, stage, and deploy real design input through meaningful parts of the production workflow. The local WordPress/Elementor deployment path is now empirically proven, including automatic asset relocation and complete template assembly after insertion.

It is not production-ready yet because responsive compilation, whole-page understanding, automated deployment transport, and broader production-target hardening remain active work.

The guiding compiler behavior remains conservative:

> **Preserve what already works. Transform what genuinely requires responsive structure.**