const MORPHER_URL = "http://localhost:8767/figma/import";
const MORPHER_ERROR_LOG_URL = "http://localhost:8767/figma/error-log";

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

function describeNode(node) {
  if (!node) return null;
  const description = {
    id: node.id,
    name: node.name,
    type: node.type,
  };
  if ("visible" in node) description.visible = node.visible;
  if ("width" in node) description.width = node.width;
  if ("height" in node) description.height = node.height;
  if ("children" in node) description.childCount = node.children.length;
  return description;
}

function serializeError(error) {
  if (!error || typeof error !== "object") {
    return { value: String(error) };
  }

  const details = {};
  for (const key of Object.getOwnPropertyNames(error)) {
    try {
      const value = error[key];
      if (value === null || value === undefined || ["string", "number", "boolean"].includes(typeof value)) {
        details[key] = value;
      } else {
        details[key] = String(value);
      }
    } catch (_) {
      details[key] = "<unreadable>";
    }
  }

  return {
    constructor: error.constructor && error.constructor.name ? error.constructor.name : null,
    ...details,
    message: typeof error.message === "string" ? error.message : String(error),
    stack: typeof error.stack === "string" ? error.stack : null,
  };
}

function buildErrorLog(node, stage, error) {
  const lines = [
    "MORPHER FIGMA EXPORT ERROR",
    `CREATED: ${new Date().toISOString()}`,
    `STAGE: ${stage}`,
    `EDITOR: ${figma.editorType}`,
    `PAGE: ${figma.currentPage.name} (${figma.currentPage.id})`,
    "",
    "=== SELECTED NODE ===",
    JSON.stringify(describeNode(node), null, 2),
    "",
    "=== ERROR ===",
    JSON.stringify(serializeError(error), null, 2),
  ];

  if (error && typeof error === "object" && error.exportDiagnostic) {
    lines.push(
      "",
      "=== JSON_REST_V1 DIAGNOSTIC ===",
      JSON.stringify(error.exportDiagnostic, null, 2)
    );
  }

  return lines.join("\n");
}

async function persistErrorLog(node, stage, error) {
  try {
    const response = await fetch(MORPHER_ERROR_LOG_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ log: buildErrorLog(node, stage, error) }),
    });
    if (!response.ok) {
      console.error("Could not persist Morpher exporter error log:", await response.text());
    }
  } catch (logError) {
    console.error("Could not persist Morpher exporter error log:", logError);
  }
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
  const probes = [];

  if ("children" in node) {
    for (const child of node.children) {
      try {
        await child.exportAsync({ format: "JSON_REST_V1" });
        probes.push({ node: describeNode(child), ok: true });
      } catch (error) {
        probes.push({ node: describeNode(child), ok: false, error: serializeError(error) });
      }
    }
  }

  const failingChildren = probes.filter((probe) => !probe.ok);
  let summary;
  if (!("children" in node) || node.children.length === 0) {
    summary = `Figma JSON_REST_V1 export failed for ${node.type} "${node.name}" (${node.id}).`;
  } else if (failingChildren.length === 0) {
    summary = `Figma JSON_REST_V1 root-only failure for ${node.type} "${node.name}" (${node.id}); all ${probes.length} direct children export successfully.`;
  } else {
    summary = `Figma JSON_REST_V1 export failed for ${node.type} "${node.name}" (${node.id}); ${failingChildren.length}/${probes.length} direct children also fail.`;
  }

  const wrapped = new Error(summary);
  wrapped.exportDiagnostic = {
    root: describeNode(node),
    rootError: serializeError(rootError),
    directChildProbes: probes,
  };
  throw wrapped;
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

  let node = null;
  let stage = "selection";

  try {
    node = selectedNode();
    figma.ui.postMessage({ type: "status", state: "sending", text: `Exporting ${node.name}...` });

    stage = "json-rest-v1";
    const payload = await exportJsonRest(node);

    stage = "image-assets";
    const assets = await exportImageAssets(node);

    stage = "vector-assets";
    const vectorAssets = await exportVectorAssets(node);

    stage = "text-assets";
    const textAssets = await exportTextAssets(node);

    stage = "text-layouts";
    const textLayouts = await exportTextLayouts(node);

    stage = "send-to-morpher";
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
    await persistErrorLog(node, stage, error);
    figma.ui.postMessage({
      type: "status",
      state: "error",
      text: error instanceof Error ? error.message : String(error),
    });
  }
};
