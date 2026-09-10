const MORPHER_URL = "http://localhost:8767/figma/import";

figma.showUI(__html__, { width: 320, height: 180 });

function selectedNode() {
  const selection = figma.currentPage.selection;
  if (selection.length !== 1) {
    throw new Error("Select exactly one Figma node before sending to Morpher.");
  }
  return selection[0];
}

function bytesToBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, Math.min(index + chunkSize, bytes.length));
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

function collectImageRefs(node, refs = new Set()) {
  if ("fills" in node && Array.isArray(node.fills)) {
    for (const fill of node.fills) {
      if (fill && fill.type === "IMAGE" && fill.imageHash) {
        refs.add(fill.imageHash);
      }
    }
  }

  if ("children" in node) {
    for (const child of node.children) {
      collectImageRefs(child, refs);
    }
  }

  return refs;
}

function isVectorComposite(node) {
  return (
    node.type !== "VECTOR" &&
    "children" in node &&
    node.children.length > 0 &&
    node.children.every((child) => child.type === "VECTOR")
  );
}

function collectVectorAssets(node, assets = []) {
  if (node.type === "VECTOR" || isVectorComposite(node)) {
    assets.push(node);
    return assets;
  }

  if ("children" in node) {
    for (const child of node.children) {
      collectVectorAssets(child, assets);
    }
  }

  return assets;
}

function collectTextAssets(node, assets = []) {
  if (node.type === "TEXT") {
    assets.push(node);
  }

  if ("children" in node) {
    for (const child of node.children) {
      collectTextAssets(child, assets);
    }
  }

  return assets;
}

async function diagnoseJsonExportFailure(node, rootError) {
  const rootMessage = rootError instanceof Error ? rootError.message : String(rootError);
  if (!("children" in node) || node.children.length === 0) {
    throw new Error(
      `Figma JSON_REST_V1 export failed for ${node.type} "${node.name}" (${node.id}): ${rootMessage}`
    );
  }

  const failingChildren = [];
  let successfulChildren = 0;

  for (const child of node.children) {
    try {
      await child.exportAsync({ format: "JSON_REST_V1" });
      successfulChildren += 1;
    } catch (error) {
      failingChildren.push({
        id: child.id,
        name: child.name,
        type: child.type,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  if (failingChildren.length === 0) {
    throw new Error(
      `Figma JSON_REST_V1 root-only failure: ${node.type} "${node.name}" (${node.id}) failed, but all ${successfulChildren} direct children export successfully. Root error: ${rootMessage}`
    );
  }

  const details = failingChildren
    .slice(0, 5)
    .map((child) => `${child.type} "${child.name}" (${child.id}): ${child.error}`)
    .join(" | ");
  const extra = failingChildren.length > 5 ? ` | +${failingChildren.length - 5} more` : "";

  throw new Error(
    `Figma JSON_REST_V1 export failed for ${node.type} "${node.name}" (${node.id}). ${failingChildren.length}/${node.children.length} direct children also fail: ${details}${extra}. Root error: ${rootMessage}`
  );
}

async function exportJsonRest(node) {
  try {
    return await node.exportAsync({ format: "JSON_REST_V1" });
  } catch (error) {
    return diagnoseJsonExportFailure(node, error);
  }
}

async function loadTextFonts(text) {
  const fonts = text.getRangeAllFontNames(0, text.characters.length);
  const unique = new Map();
  for (const font of fonts) {
    unique.set(`${font.family}\u0000${font.style}`, font);
  }
  await Promise.all([...unique.values()].map((font) => figma.loadFontAsync(font)));
}

function wordRanges(value) {
  const ranges = [];
  const pattern = /\S+/g;
  let match;
  while ((match = pattern.exec(value)) !== null) {
    ranges.push({ start: match.index, end: match.index + match[0].length });
  }
  return ranges;
}

async function measurePrefixHeight(text, end) {
  const probe = text.clone();
  try {
    figma.currentPage.appendChild(probe);
    probe.x = -100000;
    probe.y = -100000;
    probe.resize(text.width, Math.max(1, text.height));
    probe.textAutoResize = "HEIGHT";
    if (end < probe.characters.length) {
      probe.deleteCharacters(end, probe.characters.length);
    }
    return probe.height;
  } finally {
    probe.remove();
  }
}

async function probeRenderedLines(text) {
  const characters = text.characters;
  if (!characters) return [];

  const wrapStyle = typeof text.textWrapStyle === "string" ? text.textWrapStyle : "MIXED";
  if (wrapStyle !== "AUTO") {
    return null;
  }

  await loadTextFonts(text);
  const words = wordRanges(characters);
  if (!words.length) return [characters];

  const lines = [];
  let lineStart = words[0].start;
  let previousWord = words[0];
  let previousHeight = await measurePrefixHeight(text, previousWord.end);

  for (let index = 1; index < words.length; index += 1) {
    const word = words[index];
    const height = await measurePrefixHeight(text, word.end);
    if (height > previousHeight + 0.5) {
      const line = characters.slice(lineStart, previousWord.end).trim();
      if (line) lines.push(line);
      lineStart = word.start;
    }
    previousHeight = height;
    previousWord = word;
  }

  const finalLine = characters.slice(lineStart, previousWord.end).trim();
  if (finalLine) lines.push(finalLine);
  return lines;
}

async function exportTextLayout(text) {
  try {
    const renderedLines = await probeRenderedLines(text);
    return {
      sourceId: text.id,
      characters: text.characters,
      width: text.width,
      height: text.height,
      textAutoResize: text.textAutoResize,
      textWrapStyle: typeof text.textWrapStyle === "string" ? text.textWrapStyle : "MIXED",
      renderedLines,
      probeStatus: renderedLines ? "measured" : "unsupported-wrap-style",
    };
  } catch (error) {
    return {
      sourceId: text.id,
      characters: text.characters,
      width: text.width,
      height: text.height,
      renderedLines: null,
      probeStatus: "error",
      probeError: error instanceof Error ? error.message : String(error),
    };
  }
}

async function exportImageAssets(node) {
  const assets = [];
  for (const imageRef of collectImageRefs(node)) {
    const image = figma.getImageByHash(imageRef);
    if (!image) continue;
    const bytes = await image.getBytesAsync();
    assets.push({ imageRef, data: bytesToBase64(bytes) });
  }
  return assets;
}

async function exportVectorAssets(node) {
  const assets = [];
  for (const vector of collectVectorAssets(node)) {
    const bytes = await vector.exportAsync({ format: "SVG" });
    assets.push({ sourceId: vector.id, data: bytesToBase64(bytes) });
  }
  return assets;
}

async function exportTextAssets(node) {
  const assets = [];
  for (const text of collectTextAssets(node)) {
    // Keep Figma's complete text-node canvas instead of cropping the SVG to
    // visible glyph paths. This preserves intentional empty geometry such as
    // leading spaces while still outlining the glyphs for font fidelity.
    const bytes = await text.exportAsync({
      format: "SVG",
      svgOutlineText: true,
      useAbsoluteBounds: true,
    });
    assets.push({ sourceId: text.id, data: bytesToBase64(bytes) });
  }
  return assets;
}

async function exportTextLayouts(node) {
  const layouts = [];
  for (const text of collectTextAssets(node)) {
    layouts.push(await exportTextLayout(text));
  }
  return layouts;
}

figma.ui.onmessage = async (message) => {
  if (message.type !== "send-to-morpher") return;

  try {
    const node = selectedNode();
    figma.ui.postMessage({ type: "status", state: "sending", text: `Exporting ${node.name}...` });

    const payload = await exportJsonRest(node);
    const assets = await exportImageAssets(node);
    const vectorAssets = await exportVectorAssets(node);
    const textAssets = await exportTextAssets(node);
    const textLayouts = await exportTextLayouts(node);
    const response = await fetch(MORPHER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: node.name,
        nodeId: node.id,
        payload,
        assets,
        vectorAssets,
        textAssets,
        textLayouts,
      }),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `Morpher returned HTTP ${response.status}`);
    }

    figma.ui.postMessage({
      type: "status",
      state: "success",
      text: `Saved as ${result.filename} (${result.assetsSaved || 0} images, ${result.vectorsSaved || 0} vectors, ${result.textsSaved || 0} outlined texts)`,
    });
  } catch (error) {
    figma.ui.postMessage({
      type: "status",
      state: "error",
      text: error instanceof Error ? error.message : String(error),
    });
  }
};
