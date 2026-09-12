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

function isExplicitlyHidden(node) {
  return node.visible === false || (typeof node.opacity === "number" && node.opacity <= 0);
}

function nonRenderingReason(node) {
  if (typeof node.width === "number" && node.width <= 0) return "zero width";
  if (typeof node.height === "number" && node.height <= 0) return "zero height";
  if ("absoluteRenderBounds" in node && node.absoluteRenderBounds === null) return "no render bounds";
  if (node.type === "TEXT" && !(node.characters || "").trim()) return "empty text";
  return null;
}

function createSkipStats() {
  return { total: 0, reasons: {} };
}

function recordSkip(stats, reason) {
  stats.total += 1;
  stats.reasons[reason] = (stats.reasons[reason] || 0) + 1;
}

function mergeSkipStats(target, source) {
  target.total += source.total;
  for (const [reason, count] of Object.entries(source.reasons)) {
    target.reasons[reason] = (target.reasons[reason] || 0) + count;
  }
  return target;
}

function formatSkipStats(label, stats) {
  if (!stats.total) return null;
  const details = Object.entries(stats.reasons)
    .map(([reason, count]) => `${count} ${reason}`)
    .join(", ");
  return `${stats.total} ${label} skipped${details ? ` (${details})` : ""}`;
}

function rounded(value) {
  return typeof value === "number" ? Math.round(value * 100) / 100 : null;
}

function duplicateFingerprint(node) {
  const children = "children" in node
    ? node.children.filter((child) => !isExplicitlyHidden(child)).map(duplicateFingerprint)
    : [];
  return JSON.stringify({
    type: node.type,
    width: rounded(node.width),
    height: rounded(node.height),
    text: node.type === "TEXT" ? node.characters || "" : null,
    children,
  });
}

function isDuplicateCandidate(node) {
  return !isExplicitlyHidden(node) && "children" in node && node.children.length > 0;
}

function findDuplicateWarnings(root) {
  const warnings = [];

  function visit(parent, hiddenAncestor = false) {
    const hidden = hiddenAncestor || isExplicitlyHidden(parent);
    if (hidden || !("children" in parent)) return;

    const groups = new Map();
    for (const child of parent.children) {
      if (!isDuplicateCandidate(child)) continue;
      const key = JSON.stringify({
        x: rounded(child.x),
        y: rounded(child.y),
        width: rounded(child.width),
        height: rounded(child.height),
        fingerprint: duplicateFingerprint(child),
      });
      const matches = groups.get(key) || [];
      matches.push(child);
      groups.set(key, matches);
    }

    for (const matches of groups.values()) {
      if (matches.length < 2) continue;
      const original = matches[0];
      for (const duplicate of matches.slice(1)) {
        warnings.push(
          `Possible duplicate layer: "${duplicate.name}" (${duplicate.id}) matches "${original.name}" (${original.id}) at the same position and size. Both were preserved.`
        );
      }
    }

    for (const child of parent.children) visit(child, hidden);
  }

  visit(root);
  return warnings;
}

function collectImageRefs(node, refs = new Set(), hiddenAncestor = false) {
  const hidden = hiddenAncestor || isExplicitlyHidden(node);
  if (!hidden && "fills" in node && Array.isArray(node.fills)) {
    for (const fill of node.fills) {
      if (fill && fill.visible !== false && fill.type === "IMAGE" && fill.imageHash) refs.add(fill.imageHash);
    }
  }
  if ("children" in node) {
    for (const child of node.children) collectImageRefs(child, refs, hidden);
  }
  return refs;
}

function isVectorComposite(node) {
  if (node.type === "VECTOR" || !("children" in node)) return false;
  const children = node.children.filter((child) => !isExplicitlyHidden(child));
  if (children.length === 0) return false;
  if (children.every((child) => child.type === "VECTOR")) return true;

  const vectors = children.filter((child) => child.type === "VECTOR");
  const texts = children.filter((child) => child.type === "TEXT");
  if (vectors.length < 4 || vectors.length / children.length < 0.8) return false;
  if (vectors.length + texts.length !== children.length || texts.length > 2) return false;
  const annotation = texts.map((child) => (child.characters || "").trim()).join("");
  return annotation.length <= 8;
}

function collectVectorAssets(node, result = { assets: [], skipped: createSkipStats() }, hiddenAncestor = false) {
  const hidden = hiddenAncestor || isExplicitlyHidden(node);
  if (node.type === "VECTOR" || isVectorComposite(node)) {
    if (hidden) recordSkip(result.skipped, "hidden");
    else {
      const reason = nonRenderingReason(node);
      if (reason) recordSkip(result.skipped, reason);
      else result.assets.push(node);
    }
    return result;
  }
  if ("children" in node) {
    for (const child of node.children) collectVectorAssets(child, result, hidden);
  }
  return result;
}

function collectTextAssets(node, result = { assets: [], skipped: createSkipStats() }, hiddenAncestor = false) {
  const hidden = hiddenAncestor || isExplicitlyHidden(node);
  if (isVectorComposite(node)) return result;
  if (node.type === "TEXT") {
    if (hidden) recordSkip(result.skipped, "hidden");
    else {
      const reason = nonRenderingReason(node);
      if (reason) recordSkip(result.skipped, reason);
      else result.assets.push(node);
    }
    return result;
  }
  if ("children" in node) {
    for (const child of node.children) collectTextAssets(child, result, hidden);
  }
  return result;
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
  const collected = collectVectorAssets(node);
  const assets = [];
  const runtimeSkipped = createSkipStats();
  for (const vector of collected.assets) {
    try {
      const bytes = await vector.exportAsync({ format: "SVG", useAbsoluteBounds: true });
      assets.push({ sourceId: vector.id, data: bytesToBase64(bytes) });
    } catch (error) {
      if (isNoVisibleLayersExportError(error)) {
        recordSkip(runtimeSkipped, "Figma rejected");
        continue;
      }
      throw error;
    }
  }
  return { assets, skipped: mergeSkipStats(collected.skipped, runtimeSkipped) };
}

async function exportTextAssets(node) {
  const collected = collectTextAssets(node);
  const assets = [];
  const runtimeSkipped = createSkipStats();
  for (const text of collected.assets) {
    try {
      const bytes = await text.exportAsync({ format: "SVG", svgOutlineText: true, useAbsoluteBounds: true });
      assets.push({ sourceId: text.id, data: bytesToBase64(bytes) });
    } catch (error) {
      if (isNoVisibleLayersExportError(error)) {
        recordSkip(runtimeSkipped, "Figma rejected");
        continue;
      }
      throw error;
    }
  }
  return { assets, skipped: mergeSkipStats(collected.skipped, runtimeSkipped) };
}

figma.ui.onmessage = async (message) => {
  if (message.type !== "send-to-morpher") return;
  try {
    const node = selectedNode();
    figma.ui.postMessage({ type: "status", state: "sending", text: `Exporting ${node.name}...` });
    const warnings = findDuplicateWarnings(node);
    const payload = await node.exportAsync({ format: "JSON_REST_V1" });
    const assets = await exportImageAssets(node);
    const vectorExport = await exportVectorAssets(node);
    const textExport = await exportTextAssets(node);
    const vectorAssets = vectorExport.assets;
    const textAssets = textExport.assets;
    const response = await fetch(MORPHER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: node.name, nodeId: node.id, payload, assets, vectorAssets, textAssets, warnings }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Morpher returned HTTP ${response.status}`);

    const skippedNotes = [
      formatSkipStats("non-rendering vectors", vectorExport.skipped),
      formatSkipStats("non-rendering text outlines", textExport.skipped),
    ].filter(Boolean);
    const skippedNote = skippedNotes.length ? `, ${skippedNotes.join(", ")}` : "";
    const warningNote = warnings.length
      ? ` ⚠ ${warnings.length} design warning${warnings.length === 1 ? "" : "s"}; see figma-plugin/log/warning.txt.`
      : "";

    figma.ui.postMessage({
      type: "status",
      state: warnings.length ? "warning" : "success",
      text: `Saved as ${result.filename} (${result.assetsSaved || 0} images, ${result.vectorsSaved || 0} vectors, ${result.textsSaved || 0} outlined texts${skippedNote}).${warningNote}`,
    });
  } catch (error) {
    figma.ui.postMessage({ type: "status", state: "error", text: error instanceof Error ? error.message : String(error) });
  }
};
