# Morpher

Morpher is a modular **design compiler** that transforms Figma and other supported design inputs into reusable compiled structure with multiple output targets.

The project is built around shared intermediate representations so input formats, layout/semantic compilation, and output targets can evolve independently. Elementor is an output target, not the architecture boundary.

> Design in. Structure out.

## Current Status

Morpher is an **advanced prototype / early product foundation**. The project has moved beyond proving that design input can be converted, but it is not production-ready yet. Fidelity contracts, responsive behavior, semantic output, and production integrations are still being hardened.

Current development path:

```text
Design input
    ↓
Input adapter
    ↓
Design IR
    ↓
Fidelity / responsive interpretation
    ↓
Output targets
```

## Product Direction

Morpher is a design compiler with multiple output targets rather than a converter tied to one builder or framework.

```text
Figma / supported input
        ↓
Input adapter
        ↓
Design IR
        ↓
Responsive / semantic compilation
        ↓
Compiled output
   ├─ Elementor
   └─ Native HTML/CSS
```

The primary WordPress production path is **Elementor**. It provides an editable WordPress destination while Morpher remains responsible for understanding and preserving the design.

**Native HTML/CSS** remains a framework-neutral semantic reference and export target. It is especially useful as a foundation for custom web development and framework-based applications.

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

This allows Morpher to preserve visual intent without sacrificing real responsive structure.

## Fidelity

Fidelity is Morpher's **visual reference and responsive-triage target**.

It preserves source relationships while adapting the composition across viewport sizes. Its purpose is to provide a trustworthy visual baseline and reveal whether a section already behaves acceptably with simple responsive adaptation or requires structural responsive treatment.

```text
Design IR
    ↓
Fidelity
    ↓
Visual validation
    +
Responsive triage
```

Fidelity does not need to turn every composition into breakpoint-driven structural layout. It preserves what already works and helps identify what needs deeper responsive compilation.

## Elementor

Elementor is Morpher's **primary WordPress production target**.

Morpher prioritizes preserving the original visual composition while producing editable Elementor content. Sections that adapt well can retain their spatial character, while sections requiring structural responsive behavior can be transformed appropriately for different breakpoints.

```text
Design IR
    ↓
Fidelity / responsive evaluation
    ↓
Elementor
    ↓
Editable WordPress output
```

Elementor-specific behavior must remain isolated from shared compiler logic. The Design IR and responsive interpretation should not depend on Elementor's internal representation.

## Native HTML/CSS

Native provides a **semantic, framework-neutral HTML/CSS representation** of the design.

Its role is:

- semantic reference output;
- raw HTML/CSS export;
- developer and debugging target;
- foundation for custom web applications;
- foundation for framework-oriented development such as React and similar technologies.

Native should favor meaningful web structure where the compiler has sufficient semantic information, including elements such as `header`, `nav`, `main`, `section`, `article`, and `footer`.

Native is not required to compete with Elementor as the primary WordPress destination. Its value is portability and semantic structure outside a page-builder-specific environment.

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

Header Sections, Body Sections, and Footer Sections can all combine structural responsive behavior with preserved spatial composition while keeping their content editable in production targets.

## Semantic Identity

Rendered elements should have deterministic identity so output targets, developer tooling, editing systems, diagnostics, and future versioning can refer to the same logical content reliably.

Source provenance and Morpher-owned compiled identity should remain conceptually separate. Generated nodes that do not originate directly from an input source may require their own deterministic Morpher identity.

## Font Registry

Morpher can resolve semantic text against locally available font families and variants so production-oriented output can use real browser text when the required font is available.

Fonts are discovered from:

```text
storage/fonts/
```

The registry preserves available font sources and resolves the appropriate face deterministically. Successful resolution remains silent in generated output; unavailable fonts produce a diagnostic warning.

This allows semantic output to retain editable text while Fidelity can continue using the representation best suited to visual validation.

## Output Architecture

The target roles are intentionally distinct:

```text
                    Design IR
                        │
                        ▼
                    Fidelity
              visual validation
               responsive triage
                        │
                        ▼
              Responsive Strategy
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
        Elementor                Native
    WordPress production    Semantic web output
```

### Fidelity

Visual/source truth, responsive preview, and responsive triage.

### Elementor

Primary WordPress production target with editable content and responsive output.

### Native

Semantic, framework-neutral reference/export target for developers and custom applications.

## Core Principles

> **If it flows, let it flow. If it’s absolute, make it fluid.**

> **Preserve the source relationship first. Introduce structural responsive transformation when the composition requires it.**

> **Structural and spatial responsive behavior can coexist within the same section.**

> **Fidelity validates the design and helps determine responsive requirements.**

> **Elementor is the primary WordPress production target, not the compiler architecture boundary.**

> **Native remains a semantic and framework-neutral reference/export target.**

## Commands

```text
morpher-listen
morpher-inspect storage/figma-import/Some-Frame.json
morpher-render storage/figma-import/Some-Frame.json
morpher
morpher --force
```

`morpher` is the bulk-processing CLI itself; there is no `run` subcommand.

`morpher-render` supports Fidelity and Native HTML targets independently or together.

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

Near-term work focuses on strengthening the shared responsive architecture and production targets:

1. harden Fidelity as the visual reference and responsive-triage path;
2. classify and preserve source layout relationships reliably;
3. promote sections to structural responsive behavior where required;
4. compile editable Elementor output as the primary WordPress production path;
5. continue Native as semantic/framework-neutral reference and export output;
6. expand whole-page understanding across Header Section, Body, and Footer Section;
7. continue deterministic identity, typography, assets, and output validation.

Morpher should remain conservative about design interpretation: preserve what already works, transform what genuinely requires responsive structure, and keep renderer-specific concerns outside the shared compiler.