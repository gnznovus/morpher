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

function isNoVisibleLayersExportError(error) {
  const message = error instanceof Error ? error.message : String(error);
  return message.includes("may not have any visible layers");
}

function collectImageRefs(node, refs = new Set()) {
  if ("fills" in node && Array.isArray(node.fills)) {
    for (const fill of node.fills) {
      if (fill && fill.type === "IMAGE" && fill.imageHash) refs.add(fill.imageHash);
    }
  }
  if ("children" in node) {
    for (const child of node.children) collectImageRefs(child, refs);
  }
  return refs;
}

function isVectorComposite(node) {
  if (node.type === "VECTOR" || !("children" in node)) return false;
  const children = node.children.filter((child) => child.visible !== false);
  if (children.length === 0) return false;
  if (children.every((child) => child.type === "VECTOR")) return true;

  const vectors = children.filter((child) => child.type === "VECTOR");
  const texts = children.filter((child) => child.type === "TEXT");
  if (vectors.length < 4 || vectors.length / children.length < 0.8) return false;
  if (vectors.length + texts.length !== children.length || texts.length > 2) return false;
  const annotation = texts.map((child) => (child.characters || "").trim()).join("");
  return annotation.length <= 8;
}

function collectVectorAssets(node, assets = []) {
  if (node.type === "VECTOR" || isVectorComposite(node)) {
    assets.push(node);
    return assets;
  }
  if ("children" in node) {
    for (const child of node.children) collectVectorAssets(child, assets);
  }
  return assets;
}

function collectTextAssets(node, assets = []) {
  // Text inside an atomic vector composition is already captured by the
  // composition SVG; exporting it again would create an orphan child asset.
  if (isVectorComposite(node)) return assets;
  if (node.type === "TEXT") assets.push(node);
  if ("children" in node) {
    for (const child of node.children) collectTextAssets(child, assets);
  }
  return assets;
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
  let skipped = 0;
  for (const vector of collectVectorAssets(node)) {
    try {
      const bytes = await vector.exportAsync({ format: "SVG", useAbsoluteBounds: true });
      assets.push({ sourceId: vector.id, data: bytesToBase64(bytes) });
    } catch (error) {
      if (isNoVisibleLayersExportError(error)) {
        skipped += 1;
        continue;
      }
      throw error;
    }
  }
  return { assets, skipped };
}

async function exportTextAssets(node) {
  const assets = [];
  let skipped = 0;
  for (const text of collectTextAssets(node)) {
    try {
      const bytes = await text.exportAsync({
        format: "SVG",
        svgOutlineText: true,
        useAbsoluteBounds: true,
      });
      assets.push({ sourceId: text.id, data: bytesToBase64(bytes) });
    } catch (error) {
      if (isNoVisibleLayersExportError(error)) {
        skipped += 1;
        continue;
      }
      throw error;
    }
  }
  return { assets, skipped };
}

figma.ui.onmessage = async (message) => {
  if (message.type !== "send-to-morpher") return;
  try {
    const node = selectedNode();
    figma.ui.postMessage({ type: "status", state: "sending", text: `Exporting ${node.name}...` });
    const payload = await node.exportAsync({ format: "JSON_REST_V1" });
    const assets = await exportImageAssets(node);
    const vectorExport = await exportVectorAssets(node);
    const textExport = await exportTextAssets(node);
    const vectorAssets = vectorExport.assets;
    const textAssets = textExport.assets;
    const response = await fetch(MORPHER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: node.name, nodeId: node.id, payload, assets, vectorAssets, textAssets }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Morpher returned HTTP ${response.status}`);

    const skippedNotes = [];
    if (vectorExport.skipped) skippedNotes.push(`${vectorExport.skipped} non-rendering vectors skipped`);
    if (textExport.skipped) skippedNotes.push(`${textExport.skipped} non-rendering text outlines skipped`);
    const skippedNote = skippedNotes.length ? `, ${skippedNotes.join(", ")}` : "";

    figma.ui.postMessage({
      type: "status",
      state: "success",
      text: `Saved as ${result.filename} (${result.assetsSaved || 0} images, ${result.vectorsSaved || 0} vectors, ${result.textsSaved || 0} outlined texts${skippedNote})`,
    });
  } catch (error) {
    figma.ui.postMessage({
      type: "status",
      state: "error",
      text: error instanceof Error ? error.message : String(error),
    });
  }
};
