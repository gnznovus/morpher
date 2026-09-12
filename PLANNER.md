# Morpher Planner

## Locked Decisions

- Project name: **Morpher**.
- Morpher is a **design compiler**, not a converter tied to one builder or framework.
- Core architecture stays compiler-style: input adapter → Design IR → compiler → output renderer.
- Design IR and compiler behavior stay independent from Elementor, WordPress, and any single output target.
- Development rule: **small verified slice → real fixture → trace → render → compare → expand**.
- The input integration stays thin; normalization and compilation belong to Morpher Core.
- The CLI is a frontend to Morpher Core, not the permanent product boundary.
- Output targets remain separable responsibilities.
- Elementor is the primary WordPress production target.
- Native HTML/CSS remains the semantic, framework-neutral reference/export target.
- Fidelity is the visual reference and responsive-triage target.
- Whole-page understanding includes **Header Section**, **Body**, and **Footer Section**.
- A Header Section is not the same thing as Navigation; Navigation is a component within it.

### Responsive principles

> **If it flows, let it flow. If it’s absolute, make it fluid.**

> **Preserve the source relationship first. Introduce structural responsive transformation when the composition requires it.**

> **Structural and spatial responsive behavior can coexist within the same section.**

Morpher should preserve compositions that already adapt well and apply deeper structural responsive treatment only where the design requires it.

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
┌─────────────────────┬─────────────────────┐
│ Elementor           │ Native HTML/CSS     │
│ WordPress production│ Semantic web output │
└─────────────────────┴─────────────────────┘
```

Renderer-specific behavior must not dictate shared compiler architecture.

## Target Roles

### Fidelity

Fidelity is Morpher's visual reference and responsive-triage target.

It should:

- preserve source relationships;
- provide a trustworthy visual baseline;
- adapt compositions across viewport sizes;
- help determine whether simple responsive adaptation is sufficient;
- expose sections that require structural responsive treatment.

Fidelity does not need to structurally reconstruct every composition.

### Elementor

Elementor is Morpher's primary WordPress production target.

It should:

- preserve visual composition where practical;
- produce editable Elementor content;
- support structural responsive transformations where required;
- keep Elementor-specific representation outside shared compiler logic;
- avoid unnecessary generated structure when simpler composition is sufficient.

### Native HTML/CSS

Native remains a first-class output, but its primary role is semantic and framework-neutral rather than WordPress production.

It should:

- provide meaningful semantic HTML where intent is known;
- serve as a clean HTML/CSS reference;
- support developer/debug workflows;
- provide a foundation for custom applications and framework-oriented development;
- remain independent from WordPress and Elementor.

Potential semantic targets include `header`, `nav`, `main`, `section`, `article`, `aside`, `footer`, headings, paragraphs, links, and actions.

## Whole-Page Structure

A **Morph** represents one complete page/template compilation unit. Section-level fixtures are useful for development but must not become the permanent product boundary.

```text
Page / Morph
├─ Header Section
│  ├─ Navigation Component
│  ├─ Optional components
│  └─ Header Content
├─ Body
│  └─ Sections...
└─ Footer Section
```

Header Sections, Body Sections, and Footer Sections may combine structural responsive behavior with preserved spatial composition.

### Per-Morph output

The target is a coherent optimized output per Morph/page. Output targets may package their styles and assets differently, but shared design understanding belongs above the renderer layer.

## Responsive Compilation

Morpher distinguishes between compositions that can be preserved through simple responsive adaptation and layouts that require structural transformation.

```text
Design composition
        ↓
Responsive evaluation
        ↓
┌─────────────────────┬─────────────────────┐
│ Simple adaptation   │ Structural change   │
│ is sufficient       │ is required         │
└──────────┬──────────┴──────────┬──────────┘
           │                     │
           └──────────┬──────────┘
                      ↓
              Responsive output
```

A section may use both structural and spatial responsive behavior. For example, major content regions can change arrangement at a breakpoint while visual elements inside those regions retain their intended composition.

### Planned work

- [ ] Harden responsive classification against diverse real fixtures.
- [ ] Preserve source relationships when simple adaptation is sufficient.
- [ ] Promote layouts to structural responsive behavior where required.
- [ ] Support hybrid sections without unnecessary reconstruction.
- [ ] Keep responsive interpretation target-neutral until renderer-specific serialization.

## Stable Identity Contract

Rendered elements should have deterministic identity so renderers, diagnostics, editing systems, and developer tooling can refer to the same logical content reliably.

Source provenance and Morpher-owned compiled identity remain conceptually separate.

### Planned work

- [ ] Emit deterministic unique DOM identity where applicable.
- [ ] Preserve source provenance independently from rendering selectors.
- [ ] Add renderer invariants/tests rejecting duplicate identities.
- [ ] Define deterministic Morpher identity for generated nodes without direct source identity.

## Font Registry

The font registry supports semantic text output using locally available font families and variants.

Font source:

```text
storage/fonts/
```

The registry should preserve available font sources and resolve requested faces deterministically. Successful resolution remains silent in generated output; unavailable fonts produce a diagnostic warning.

### Current direction

- [x] Font source discovery foundation.
- [x] Font metadata parsing foundation.
- [x] Deterministic registry/grouping foundation.
- [x] Cache-aware resolution foundation.
- [x] Design IR font intent bridge.
- [x] Native font CSS/packaging foundation.
- [ ] Continue hardening packaging and edge cases against real font collections.

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
- [x] Style, clipping, rotation, image, stroke, and typography metadata used by verified fixtures.
- [x] Hidden source subtrees pruned from IR.

### Fidelity

- [x] Standalone HTML + companion CSS.
- [x] Deterministic source-based classes.
- [x] Free-layout reconstruction foundation.
- [x] Auto Layout foundations.
- [x] Raster and vector rendering.
- [x] Text fidelity representation with semantic source retained.
- [x] Multiline text handling.
- [x] Frame clipping.
- [x] Rotation handling.
- [x] Divider and shape-stroke rendering.
- [x] Inspect traces and regression coverage for verified behavior.
- [ ] Harden fluid responsive Fidelity as the normal visual-reference behavior.
- [ ] Expand responsive triage across diverse section types.

### Responsive compiler / Elementor

Responsive compilation is active work. Elementor consumes shared responsive understanding rather than driving compiler architecture.

- [x] Responsive compiler foundations.
- [x] Region/flow grouping foundations.
- [x] Generated-wrapper pruning foundation.
- [x] Elementor renderer foundation.
- [ ] Align responsive compilation with preserve-first classification.
- [ ] Preserve editable Elementor mappings where practical.
- [ ] Reduce unnecessary structural reconstruction.
- [ ] Continue validating generated output against real Elementor behavior.

### Native HTML/CSS

- [x] Native HTML renderer foundation.
- [x] Native typography/font CSS foundation.
- [x] Independent Native output directory and CLI target.
- [ ] Expand semantic element selection.
- [ ] Keep Native framework-neutral.
- [ ] Use Native as a reference/export foundation for custom and framework-based applications.

## Immediate Sequence

1. **Harden fluid Fidelity** as the visual reference and responsive-triage path.
2. **Align responsive compilation** with preserve-first layout classification.
3. **Compile Elementor** as the primary editable WordPress production path.
4. **Validate hybrid sections** that combine structural responsive behavior with preserved spatial composition.
5. **Expand whole-page understanding** across Header Section, Body, and Footer Section.
6. **Continue Native semantics** as the framework-neutral reference/export target.
7. **Harden identity, fonts, assets, and output validation** across targets.

## Later / Optional Inputs

- [ ] SVG adapter.
- [ ] PNG adapter.
- [ ] JPG/JPEG adapter.
- [ ] PDF adapter.
- [ ] Additional design-source adapters.

## Later / Optional Outputs / Integration

- [ ] Morpher application/UI.
- [ ] Whole-page Morph compilation as normal workflow.
- [ ] Per-Morph CSS optimization/bundling.
- [ ] Optional Elementor deployment/integration automation.
- [ ] Gutenberg renderer.
- [ ] React-oriented renderer or integration.
- [ ] Tailwind renderer.
- [ ] Other renderers through the same output-agnostic IR.

## Prototype Maturity

Morpher should currently be described as an **advanced prototype / early product foundation**.

The project can transport, normalize, inspect, render, and compile real design input through meaningful parts of the pipeline. It is not production-ready yet because responsive compilation, whole-page semantic understanding, and production-target hardening are still active work.

The guiding compiler behavior is conservative:

> **Preserve what already works. Transform what genuinely requires responsive structure.**