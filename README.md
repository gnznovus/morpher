# Morpher

Morpher is a modular **design compiler** that transforms Figma and other supported design inputs into reusable compiled structure with multiple output targets.

The project is built around shared intermediate representations so input formats, layout/semantic compilation, and output targets can evolve independently. Elementor is an output target, not the architecture boundary.

> Design in. Structure out.

## Current Status

Morpher is an **advanced prototype / early product foundation**. The project has moved beyond proving that Figma can be converted, but it is not production-ready yet: fidelity contracts are still being hardened, responsive compilation is still evolving, and Morpher Native / WordPress editing are product architecture rather than implemented features.

Current verified development path:

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
HTML/CSS fidelity renderer
```

Real Figma sections with substantially different compositions have been imported, normalized, rendered, and visually compared. The current fidelity path covers free layout, Auto Layout foundations, raster fills, vectors/icons, dividers, clipping, rotation, multiline text, outlined text assets, and shape strokes used by verified fixtures.

## Product Direction

Morpher is intended to become a compiler with several outputs rather than a Figma → Elementor converter:

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

**Morpher Native** is the preferred long-term first-party output. Elementor remains supported as an export/integration target.

The guiding WordPress editing rule is simple:

> **Developers control the design. Editors control the content. Morpher makes it difficult to destroy either.**

## Morpher Native + WordPress Visual Editor

The planned WordPress plugin is not intended to become a smaller Elementor. Normal administrators usually need safe content editing, not arbitrary layout construction.

The initial visual editor should focus on:

- click/pinpoint selection directly on the rendered page;
- text editing;
- image replacement;
- button/link label and URL editing;
- contact-information editing;
- optional visibility controls;
- live preview before persistence;
- permissions separating normal content controls from developer controls;
- versioned backup and restore as a core safety feature.

Layout editing, arbitrary widgets, drag/drop, snapping, advanced responsive controls, and structural editing are developer-oriented future tools rather than normal admin controls.

### Stable DOM identity

Every Morpher-rendered element should eventually receive a unique deterministic DOM ID in addition to its rendering class and source metadata. For a Figma node `45:5221`:

```html
<h2
  id="morpher-45-5221"
  class="morpher-45-5221"
  data-morpher-source-id="45:5221"
>
  ...
</h2>
```

Responsibilities remain distinct:

- `id="morpher-45-5221"` — direct DOM/JavaScript/editor lookup;
- `class="morpher-45-5221"` — generated CSS targeting;
- `data-morpher-source-id="45:5221"` — original Figma provenance.

DOM IDs must be unique and deterministic. A future Morpher-owned identity may be added for generated nodes that do not originate in Figma; source identity and compiled object identity should not be conflated.

Stable IDs make pinpoint editing, runtime JavaScript behavior, focused diff previews, debugging, and version tracking substantially simpler.

### Content overrides

Normal WordPress edits should not mutate the compiled design template directly. The intended model is:

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

This keeps the design reproducible and allows editor content to survive recompilation when stable identities survive. A reset-to-original operation can clear or disable overrides without rewriting the source design.

### Live and responsive preview

The editor can preview the actual generated page in an iframe and patch the DOM immediately while fields are edited; a full recompile is not required for every keystroke.

Responsive preview should provide Desktop / Tablet / Mobile viewport selectors. Widths come from Morpher's breakpoint/configuration system rather than hardcoded example values, so the preview exercises the same media-query behavior as the generated page.

## Font Registry

Production Morpher Native should favor semantic HTML text when the exact font is available instead of permanently depending on outlined SVG text.

Fonts can be stored under:

```text
storage/fonts/
```

Morpher should use a plug-and-play gather/register flow: normal Morpher command execution scans the font directory, refreshes the registry, resolves the Figma family/face/weight/style metadata to an installed font file, and emits the required `@font-face` declarations.

```text
morpher ...
   ↓
font gatherer
   ↓
scan storage/fonts/
   ↓
refresh registry
   ↓
execute command
```

Dropping in a font should therefore require no Morpher restart; the next command sees it. A future long-lived watch/dev mode can rescan when files change.

Outlined SVG text remains useful for fidelity diagnostics and as a fallback during the transition, while real graphics/logos/decorative typography remain valid SVG assets.

## Versioning, Backup, and Restore

Version safety is a core Morpher Native feature, not an optional polish item. The model is inspired by Git's lifecycle, but it is **not literal Git** and administrators are not expected to execute Git commands.

Conceptual lifecycle:

```text
morpher init
→ create the protected baseline when a design/page is first imported

morpher add
→ track the current state of changed/untracked elements

morpher commit
→ record the tracked changes with a human change message

morpher push
→ create a new full page version under the same page backup root
```

A page backup may conceptually contain:

```text
backup/page-123/
├─ baseline/
├─ v042/
├─ v043/
└─ ...
```

Rules:

- baseline/init is permanently protected;
- normal full versions use rolling retention;
- selected versions may be **Mark as Main** and are protected from automatic cleanup while marked;
- Main versions have a hard small limit (target roughly 2–3, exact limit not yet locked);
- if Main slots are full, the UI must require the user to choose which existing Main version to unmark/replace rather than silently changing protection;
- backups include/restorably reference assets, not only text/CSS;
- versions should record author, timestamp, change message, and a useful change summary;
- autosave/recovery is separate from proper committed versions.

### Restore preview

Restore is non-destructive: selecting an old version should produce a new current revision based on that snapshot rather than erasing later history.

Before restoring, the editor should show a rendered comparison:

- desktop/tablet: two-column **Current vs Restore Candidate** preview, with synchronized scrolling where practical;
- mobile: one full preview at a time with **A ↔ swipe ↔ B** interaction;
- below the visual preview: preserve the conventional `- / +` diff summary for developers and experienced editors.

Changed entries in the diff summary should be clickable. A lightweight AJAX modal can open a focused A/B rendered comparison for the selected element, using deterministic Morpher DOM IDs to locate the corresponding element in both revisions. This gives normal admins a visual explanation while retaining a precise technical diff underneath.

## Fidelity Strategy

Morpher currently preserves both semantic and fidelity representations of Figma text:

```text
Figma TEXT
├─ semantic representation
│  ├─ characters
│  └─ typography metadata
└─ fidelity representation
   └─ outlined SVG exported by Figma
```

Outlined text is exported with `svgOutlineText: true` and `useAbsoluteBounds: true`. The fidelity renderer can use the SVG companion while semantic data remains canonical for future native/Elementor output.

SVG-backed assets remain authoritative for their internal fill, stroke, opacity, and vector geometry. CSS controls external layout geometry only.

## Verified Figma Reconstruction

Current verified behavior includes:

- Figma `JSON_REST_V1` import through the local plugin/listener;
- preserved Figma source IDs for deterministic asset mapping and debugging;
- free-layout reconstruction using Figma geometry;
- Auto Layout direction, gap, padding, alignment, and fixed/hug/fill foundations;
- raster image fills and opacity;
- SVG vector/composite asset transport;
- outlined text fidelity assets with semantic source retained;
- multiline and leading-whitespace geometry preservation;
- dividers and shape strokes;
- frame clipping;
- quarter-turn reconstruction;
- deterministic HTML/CSS classes;
- rich inspect traces;
- bulk processing and force replacement.

## Commands

```text
morpher-listen
morpher-inspect storage/figma-import/Some-Frame.json
morpher-render storage/figma-import/Some-Frame.json
morpher
morpher --force
```

`morpher` is the bulk-processing CLI itself; there is no `run` subcommand.

## Storage

```text
storage/
├─ figma-import/
├─ input/
├─ processed/
├─ fonts/          # planned font registry source
├─ log/
└─ output/
   ├─ html/
   └─ elementor/
```

Source scan priority is `figma-import/` then `input/`. Preserved Figma imports are repeatable source snapshots rather than a queue. Successfully processed ordinary inputs move to `processed/`; failed inputs remain available for retry. Existing outputs are skipped by default and `--force` replaces them in place.

## Immediate Engineering Direction

Product architecture is intentionally being recorded now without interrupting the current compiler work. The near-term sequence is:

1. finish remaining fidelity contracts, including the Newsletter decorative-vector geometry/export mismatch;
2. continue the responsive layout compiler;
3. add the font gatherer/registry;
4. move production Native text toward semantic HTML using registered fonts;
5. establish the Morpher Native renderer;
6. build the WordPress visual content editor, content overrides, viewport preview, and version/restore system;
7. add developer-oriented structural/widget/snapping tools later.

The current fidelity path should remain a stable diagnostic/reference path while these layers are added.