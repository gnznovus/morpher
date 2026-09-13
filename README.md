# Morpher

Morpher is a modular **design compiler** that transforms Figma and other supported design inputs into editable production output while preserving the source design as closely as possible.

The project is built around shared intermediate representations so input formats, responsive interpretation, validation, and output targets can evolve independently. Elementor is the primary WordPress production target, not the architecture boundary.

> Design in. Structure out.

## Current Status

Morpher is an **advanced prototype / early product foundation**. The project now compiles real design input into editable Elementor templates and includes a working local WordPress deployment path. The current core-hardening phase is adding first-class Design IR validation and shared diagnostics before expanding target-specific behavior further.

The primary development and product path is:

```text
Design input
    ↓
Input adapter
    ↓
Design IR
    ↓
IR validation
    ↓
Fidelity
    ↓
Responsive evaluation
    ↓
Elementor
    ↓
WordPress deployment
```

Fidelity establishes the visual reference and helps determine the responsive treatment required before Morpher produces editable Elementor output.

## Product Direction

For WordPress, Morpher follows a **Fidelity → Elementor** approach. Elementor output can then be staged and imported into WordPress through the Morpher deployment integration.

```text
Figma / supported input
        ↓
Input adapter
        ↓
Design IR
        ↓
IR validation + diagnostics
        ↓
Fidelity
visual validation + responsive triage
        ↓
Responsive strategy
        ↓
Elementor
editable WordPress production output
        ↓
Morpher deployment
```

Morpher is responsible for understanding the design, preserving its visual relationships, validating shared structural invariants, and determining where stronger responsive structure is required. Elementor provides the editable WordPress destination.

Native remains available as a secondary, framework-neutral semantic/reference output rather than the primary WordPress path.

## Design IR Validation

Design IR is the shared contract between input adapters and Morpher's compiler/rendering layers. Morpher validates that contract independently from any specific production target.

Validation diagnostics use three severities:

- **error** — the IR violates an invariant Morpher depends on and unsafe compilation should stop;
- **warning** — the structure is suspicious or incomplete but still compilable;
- **info** — a normal normalization/compiler decision that is useful to report without implying a problem.

The initial validator covers renderer-independent invariants such as invalid numeric geometry, impossible opacity values, tree cycles, malformed sizing state, unsupported nodes, missing content/asset references, and duplicate source identity. Target-specific assumptions remain outside this shared layer.

## Responsive Layout Strategy

Morpher preserves relationships expressed by the source design whenever possible.

> **If it flows, let it flow. If it’s absolute, make it fluid.**

Morpher supports both structural and spatial responsive relationships. Structural content can reflow, stack, or change arrangement across breakpoints, while spatial compositions can preserve their intended visual relationships as available space changes.

These approaches can coexist within the same section. Morpher introduces structural responsive transformations when the composition requires them rather than reconstructing every spatial relationship by default.

### Simple and structural responsiveness

Some compositions remain usable through simple responsive adaptation. Others require structural changes such as columns becoming stacked regions or content changing arrangement at a breakpoint.

Morpher treats these as different requirements:

```text
Design composition
        ↓
Responsive evaluation
        ↓
┌─────────────────────┬─────────────────────┐
│ Simple adaptation   │ Structural change   │
│ preserves intent    │ required            │
└──────────┬──────────┴──────────┬──────────┘
           │                     │
           └──────────┬──────────┘
                      ↓
              Responsive output
```

This keeps simple compositions simple while still allowing full responsive behavior where the design actually needs it.

### Hybrid sections

A section does not need to use only one responsive strategy. Structural regions and spatial composition can coexist.

For example, a content region and media region may change from side-by-side to stacked on a smaller viewport while visual elements associated with the media retain their intended composition.

## Fidelity

Fidelity is Morpher's **visual reference and responsive-triage target**. It preserves source relationships while adapting the composition across viewport sizes and provides the baseline used to judge production output.

## Elementor

Elementor is Morpher's **primary WordPress production target**.

Morpher prioritizes preserving the original visual composition while producing editable Elementor content. Verified compiler behavior includes production image-frame cropping for source fill images, rotated text/divider normalization, vector-derived production assets, exact-font integration, and reconstruction of repeated visual-marker/text rows such as contact information and amenity lists.

Renderer-specific behavior remains isolated from shared compiler architecture.

## WordPress Deployment

Morpher includes a local-first deployment workflow for generated Elementor templates.

```text
morpher
    ↓
generated Elementor template + assets
    ↓
morpher-deploy
    ↓
staged Morpher deployment
    ↓
Morpher WordPress plugin
    ↓
Elementor Library
```

The WordPress plugin copies staged assets into WordPress uploads, rewrites generated asset references, and creates or updates the Elementor Library entry. A Morpher admin page provides a manual **Process staged deployments** action and deployment status table. The manual action is intentionally retained as a fallback/debug path while automatic triggering remains future work.

Repeated deployment of the same build is skipped by default. `--force` permits intentional re-staging while preserving normal validation.

## Font Registry

Morpher can resolve semantic text against locally available font families and variants so production-oriented output can use the requested font when available.

Fonts are discovered from:

```text
storage/fonts/
```

The WordPress font integration packages resolved faces separately from deployment runtime ownership. Missing fonts produce diagnostics; successful resolution remains silent.

## Page Structure

Morpher should understand whole pages as semantic regions rather than treating every imported frame as an isolated visual block.

```text
Page
├─ Header Section
│  ├─ Navigation Component
│  ├─ Optional components
│  └─ Header Content
├─ Body
│  └─ Sections...
└─ Footer Section
```

A **Header Section is not the same thing as Navigation**. Navigation is one possible component within a Header Section.

## Core Principles

> **If it flows, let it flow. If it’s absolute, make it fluid.**

> **Preserve the source relationship first. Introduce structural responsive transformation when the composition requires it.**

> **Structural and spatial responsive behavior can coexist within the same section.**

> **Validate shared IR invariants before target-specific compilation.**

> **Fidelity validates the design and helps determine responsive requirements.**

> **Fidelity → Elementor is Morpher's primary WordPress production path.**

## Commands

```text
morpher-listen
morpher-inspect storage/figma-import/Some-Frame.json
morpher-render storage/figma-import/Some-Frame.json
morpher
morpher --force
morpher Some-Frame
morpher Some-Frame.json
morpher-deploy
morpher-deploy Some-Frame
morpher-deploy Some-Frame --force
```

`morpher` supports bulk processing when no target is supplied and friendly target resolution when a source name/path is supplied. Target resolution stays within Morpher's source roots and prioritizes `figma-import/` before `input/`.

`morpher-deploy` supports bulk deployment or a friendly template target with optional extension/template suffix/path variants. Deployment targets are constrained to the Elementor output root.

## Storage

```text
storage/
├─ figma-import/
├─ input/
├─ processed/
├─ fonts/
├─ log/
└─ output/
   ├─ html/
   │  ├─ fidelity/
   │  └─ native/
   └─ elementor/
```

Source scan priority is `figma-import/` then `input/`. Preserved imports are repeatable source snapshots rather than a queue. Successfully processed ordinary inputs move to `processed/`; failed inputs remain available for retry. Existing outputs are skipped by default and `--force` replaces them in place.

## Engineering Direction

Near-term work is focused on Morpher's shared compiler core:

1. establish first-class Design IR invariant validation;
2. integrate structured validation diagnostics into Morpher reporting and CLI behavior;
3. harden responsive classification and hybrid structural/spatial sections against validated IR;
4. improve whole-page understanding across Header Section, Body, and Footer Section;
5. strengthen framework-neutral semantic validation;
6. return to deployment/runtime hardening after the core validation layer is stable.

Morpher should remain conservative about design interpretation: preserve what already works, transform what genuinely requires responsive structure, and keep renderer-specific concerns outside the shared compiler.