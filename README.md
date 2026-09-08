# Morpher

Morpher is a modular design compiler prototype that transforms Figma and other supported design inputs into clean HTML/CSS and editable Elementor templates.

The project is built around a shared intermediate representation so input formats and output targets can evolve independently without coupling the compiler core to Figma or Elementor.

## Prototype Goals

- Figma-first structural conversion.
- Clean HTML and CSS output.
- Editable Elementor template JSON output.
- Bulk processing through filesystem-based queues.
- Preserved Figma imports for repeatable conversion and debugging.
- Extensible input and output adapter architecture.
- Pixel-perfect visual fidelity as the long-term target.

## Processing Model

```text
Figma / supported input
        ↓
Input adapter
        ↓
Design IR
        ↓
Compiler
        ↓
Compiled design
   ↙            ↘
HTML/CSS     Elementor
```

## Storage Layout

```text
storage/
├─ figma-import/
├─ input/
├─ processed/
└─ output/
   ├─ html/
   └─ elementor/
```

### Source priority

Morpher scans sources in this order:

1. `storage/figma-import/`
2. `storage/input/`

`figma-import/` is preserved as a reusable source repository. Successfully processed files from `input/` are moved to `processed/` and renamed using the `_P` suffix.

Example:

```text
storage/input/homepage.svg
→ storage/processed/homepage_P.svg
```

## Output Naming

For source name `homepage`:

```text
storage/output/html/homepage.html
storage/output/html/homepage.css
storage/output/elementor/homepage_template.json
```

Existing outputs are skipped by default. A future `--force` option will replace existing outputs in place rather than create numbered copies.

## Planned Input Support

Prototype priority:

1. Figma-compatible JSON
2. SVG
3. PNG
4. JPG / JPEG
5. PDF

Figma JSON is intended to be the primary structural input. Visual formats require progressively more reconstruction and inference.

## Architecture Direction

```text
src/
├─ inputs/
│  ├─ base.py
│  ├─ registry.py
│  └─ figma_json.py
├─ storage/
│  ├─ paths.py
│  ├─ scanner.py
│  └─ processor.py
├─ ir/
│  ├─ nodes.py
│  └─ styles.py
├─ compiler/
│  ├─ normalizer.py
│  └─ layout.py
├─ renderers/
│  ├─ html.py
│  ├─ css.py
│  └─ elementor.py
└─ cli.py
```

The IR must remain output-agnostic. Elementor-specific concerns belong only in the Elementor renderer.

## Prototype Success Criteria

A simple Figma frame containing a vertical layout with heading, paragraph, and image should compile into both:

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

with matching layout and styling as closely as practical.

## Status

Prototype foundation in progress.
