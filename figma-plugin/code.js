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

function normalizedText(value) {
  return (value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function visibleBounds(node) {
  const bounds = "absoluteRenderBounds" in node && node.absoluteRenderBounds
    ? node.absoluteRenderBounds
    : ("absoluteBoundingBox" in node ? node.absoluteBoundingBox : null);
  if (!bounds || bounds.width <= 0 || bounds.height <= 0) return null;
  return {
    x1: bounds.x,
    y1: bounds.y,
    x2: bounds.x + bounds.width,
    y2: bounds.y + bounds.height,
    width: bounds.width,
    height: bounds.height,
    area: bounds.width * bounds.height,
  };
}

function overlapRatio(a, b) {
  const width = Math.max(0, Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1));
  const height = Math.max(0, Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1));
  const smallerArea = Math.min(a.area, b.area);
  return smallerArea > 0 ? (width * height) / smallerArea : 0;
}

function setSimilarity(first, second) {
  if (!first.size && !second.size) return 1;
  if (!first.size || !second.size) return 0;
  let shared = 0;
  for (const value of first) if (second.has(value)) shared += 1;
  const union = first.size + second.size - shared;
  return union > 0 ? shared / union : 0;
}

function countSimilarity(first, second) {
  const larger = Math.max(first, second);
  if (!larger) return 1;
  return Math.min(first, second) / larger;
}

function regionFingerprint(node) {
  const texts = new Set();
  let visuals = 0;
  let containers = 0;

  function visit(current, hiddenAncestor = false) {
    const hidden = hiddenAncestor || isExplicitlyHidden(current);
    if (hidden) return;
    if (current.type === "TEXT") {
      const text = normalizedText(current.characters);
      if (text) texts.add(text);
    }
    if (["VECTOR", "BOOLEAN_OPERATION", "STAR", "ELLIPSE", "POLYGON", "LINE"].includes(current.type)) {
      visuals += 1;
    }
    if ("fills" in current && Array.isArray(current.fills) && current.fills.some((fill) => fill && fill.visible !== false && fill.type === "IMAGE")) {
      visuals += 1;
    }
    if ("children" in current) {
      containers += 1;
      for (const child of current.children) visit(child, hidden);
    }
  }

  visit(node);
  return { texts, visuals, containers };
}

function hasVisiblePaint(paints) {
  return Array.isArray(paints) && paints.some(
    (paint) => paint && paint.visible !== false && (typeof paint.opacity !== "number" || paint.opacity > 0)
  );
}

function isTransparentWrapper(node) {
  if (!("children" in node)) return false;
  const children = node.children.filter((child) => !isExplicitlyHidden(child));
  if (children.length !== 1 || !("children" in children[0])) return false;
  const hasFill = "fills" in node && hasVisiblePaint(node.fills);
  const hasStroke = "strokes" in node && hasVisiblePaint(node.strokes);
  return !hasFill && !hasStroke;
}

function collectRegionCandidates(root) {
  const rootBounds = visibleBounds(root);
  const minimumArea = rootBounds ? rootBounds.area * 0.05 : 0;
  const candidates = [];

  function visit(node, path = [], hiddenAncestor = false, isRoot = false) {
    const hidden = hiddenAncestor || isExplicitlyHidden(node);
    if (hidden) return;
    if ("children" in node && node.children.length > 0) {
      const nodePath = isRoot ? [] : [...path, node.name];
      const bounds = visibleBounds(node);
      if (!isRoot && !isTransparentWrapper(node) && bounds && bounds.area >= minimumArea) {
        candidates.push({
          node,
          path: nodePath,
          bounds,
          fingerprint: regionFingerprint(node),
        });
      }
      for (const child of node.children) visit(child, nodePath, hidden, false);
    }
  }

  visit(root, [], false, true);
  return candidates;
}

function formatStructurePath(candidate) {
  return candidate.path.filter(Boolean).join(" > ") || candidate.node.name;
}

function similarOverlappingPair(first, second) {
  const overlap = overlapRatio(first.bounds, second.bounds);
  if (overlap < 0.9) return false;

  const areaRatio = Math.min(first.bounds.area, second.bounds.area) / Math.max(first.bounds.area, second.bounds.area);
  if (areaRatio < 0.8) return false;

  const textSimilarity = setSimilarity(first.fingerprint.texts, second.fingerprint.texts);
  const visualSimilarity = countSimilarity(first.fingerprint.visuals, second.fingerprint.visuals);
  const containerSimilarity = countSimilarity(first.fingerprint.containers, second.fingerprint.containers);
  const sameName = normalizedText(first.node.name) === normalizedText(second.node.name);

  if (textSimilarity < 0.75 || visualSimilarity < 0.7 || containerSimilarity < 0.7) return false;
  if (!sameName && textSimilarity < 0.9) return false;
  return true;
}

function collectCandidateClusters(candidates) {
  const adjacency = candidates.map(() => new Set());

  for (let index = 0; index < candidates.length; index += 1) {
    for (let otherIndex = index + 1; otherIndex < candidates.length; otherIndex += 1) {
      if (!similarOverlappingPair(candidates[index], candidates[otherIndex])) continue;
      adjacency[index].add(otherIndex);
      adjacency[otherIndex].add(index);
    }
  }

  const visited = new Set();
  const clusters = [];
  for (let index = 0; index < candidates.length; index += 1) {
    if (visited.has(index) || adjacency[index].size === 0) continue;
    const pending = [index];
    const cluster = [];
    visited.add(index);

    while (pending.length) {
      const current = pending.pop();
      cluster.push(candidates[current]);
      for (const neighbor of adjacency[current]) {
        if (visited.has(neighbor)) continue;
        visited.add(neighbor);
        pending.push(neighbor);
      }
    }

    cluster.sort((first, second) => first.path.length - second.path.length);
    clusters.push(cluster);
  }

  return clusters;
}

function formatStackedDuplicateWarning(cluster) {
  const paths = cluster.map((candidate) => `- ${formatStructurePath(candidate)}`).join("\n");
  const count = cluster.length;
  return `Possible stacked duplicate content: ${count} similar structures occupy the same visible region:\n${paths}\nThese structures contain highly similar content and appear stacked in the same area. Check these layer paths for accidental duplication. Morpher preserved all ${count}.`;
}

function findOverlappingStructureWarnings(root) {
  const candidates = collectRegionCandidates(root);
  return collectCandidateClusters(candidates).map(formatStackedDuplicateWarning);
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
  warnings.push(...findOverlappingStructureWarnings(root));
  return warnings;
}

function warningTopic(warning) {
  if (warning.startsWith("Possible stacked duplicate content:")) {
    return "Possible stacked duplicate content detected.";
  }
  if (warning.startsWith("Possible duplicate layer:")) {
    return "Possible duplicate layer detected.";
  }
  return "Design warning detected.";
}

function formatWarningNote(warnings) {
  if (!warnings.length) return "";
  const topics = warnings.map(
    (warning, index) => `⚠ [${index + 1}] ${warningTopic(warning)}`
  );
  return `\n${topics.join("\n")}\nSee figma-plugin/log/warning.txt for full details.`;
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
    const warningNote = formatWarningNote(warnings);

    figma.ui.postMessage({
      type: "status",
      state: warnings.length ? "warning" : "success",
      text: `Saved as ${result.filename} (${result.assetsSaved || 0} images, ${result.vectorsSaved || 0} vectors, ${result.textsSaved || 0} outlined texts${skippedNote}).${warningNote}`,
    });
  } catch (error) {
    figma.ui.postMessage({ type: "status", state: "error", text: error instanceof Error ? error.message : String(error) });
  }
};
