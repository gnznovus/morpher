# Morpher

Morpher is a modular design compiler prototype that transforms Figma and other supported design inputs into clean HTML/CSS and, later, editable Elementor templates.

The project is built around a shared intermediate representation so input formats and output targets can evolve independently without coupling the compiler core to Figma or Elementor.

> Design in. Structure out.

## Current Prototype

The current verified path is:

```text
Figma selected frame
        ↓ JSON_REST_V1 + assets
Local Morpher Figma plugin
        ↓ localhost POST
Morpher listener
        ↓
storage/figma-import/
        ↓
Figma JSON adapter
        ↓
Design IR
        ↓
HTML/CSS renderer
```

Real Figma sections with substantially different compositions have been imported, normalized, rendered, and visually compared. The current HTML fidelity path has been verified with free-layout sections, Auto Layout fixtures, raster image fills, composite SVG icons, raw vectors, dividers, rotated elements, clipping, multiline text, and outlined text assets.

This is a prototype checkpoint, not a claim that every Figma feature is supported.

## Fidelity Strategy

Morpher preserves two useful representations of Figma text:

```text
Figma TEXT
├─ semantic representation
│  ├─ characters
│  └─ typography metadata
│
└─ fidelity representation
   └─ outlined SVG exported by Figma
```

The semantic text remains available in the Design IR for future semantic HTML and Elementor output. The current fidelity HTML renderer uses the outlined SVG companion when available so browser font availability does not change the visual result.

Outlined text is exported with `svgOutlineText: true` and `useAbsoluteBounds: true`. Preserving the full Figma text-node bounds is important for source designs that use empty text geometry such as leading whitespace.

SVG-backed icon assets remain authoritative for their own fill, stroke, opacity, and internal vector geometry. CSS controls their external layout geometry only; Morpher does not repaint an SVG vector fill as a rectangular CSS background.

## Verified Figma Reconstruction

Current verified behavior includes:

- Figma `JSON_REST_V1` import through the local plugin/listener.
- Preserved Figma source IDs for deterministic asset mapping and debugging.
- Free-layout reconstruction using absolute Figma geometry.
- Auto Layout direction, gap, padding, alignment, and fixed/hug/fill sizing foundations.
- Raster image-fill asset transport and `object-fit: cover` rendering.
- Image-fill opacity preservation.
- SVG vector asset transport.
- Composite vector-only frame/group export as a single SVG asset.
- Raw vector rendering without CSS background-fill corruption.
- Outlined text fidelity assets with original text retained semantically.
- Explicit multiline text and leading-whitespace geometry preservation.
- Horizontal and vertical dividers.
- Frame clipping through `overflow: hidden`.
- Quarter-turn reconstruction for rotated free-layout elements.
- Deterministic HTML/CSS class names based on Figma source IDs.
- Rich inspect traces for debugging normalized Design IR.
- Bulk processing and force-replacement of existing outputs.

## Processing Commands

Run the local Figma import listener:

```text
morpher-listen
```

Inspect a preserved Figma import:

```text
morpher-inspect storage/figma-import/Some-Frame.json
```

Render one import:

```text
morpher-render storage/figma-import/Some-Frame.json
```

Bulk process discovered sources:

```text
morpher run
```

Replace existing output checkpoints in place:

```text
morpher run --force
```

## Storage Layout

```text
storage/
├─ figma-import/
├─ input/
├─ processed/
├─ log/
└─ output/
   ├─ html/
   └─ elementor/
```

### Source priority

Morpher scans sources in this order:

1. `storage/figma-import/`
2. `storage/input/`

`figma-import/` is a preserved source repository, not a processing queue. Re-sending the same named Figma frame replaces its import snapshot in place while keeping it available for repeatable conversion and debugging.

Successfully processed files from `input/` move to `processed/` with `_P` added before the extension. A source moves only after all required outputs succeed; failed inputs remain available for retry.

Existing outputs are skipped by default. `--force` replaces them in place rather than creating numbered copies.

## Output Naming

For source name `homepage`:

```text
storage/output/html/homepage.html
storage/output/html/homepage.css
storage/output/elementor/homepage_template.json
```

The HTML/CSS path is active. Elementor remains a planned output renderer.

## Architecture Direction

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
   ↙            ↘
HTML/CSS     Elementor
renderer     renderer
        ↓
 future visual validator
```

The Design IR must remain output-agnostic. Elementor-specific concerns belong only in the Elementor renderer.

Current source organization follows the same separation of concerns across input adapters, IR, compiler, renderers, storage, listener, tracing, and CLI layers.

## Planned Input Support

Prototype priority beyond the current Figma JSON path:

1. SVG
2. PNG
3. JPG / JPEG
4. PDF
5. Optional Figma REST adapter

Figma JSON remains the primary structural input. Visual-only formats require progressively more reconstruction and inference.

## Next Direction

The current Figma → fidelity HTML slice is strong enough to expand deliberately rather than adding broad behavior speculatively. Next work should focus on additional unsupported Figma features and regression fixtures, then semantic/responsive compilation and the Elementor renderer while preserving the verified fidelity path.
