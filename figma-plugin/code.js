const MORPHER_URL = "http://127.0.0.1:8767/figma/import";

figma.showUI(__html__, { width: 320, height: 180 });

function selectedNode() {
  const selection = figma.currentPage.selection;
  if (selection.length !== 1) {
    throw new Error("Select exactly one Figma node before sending to Morpher.");
  }
  return selection[0];
}

figma.ui.onmessage = async (message) => {
  if (message.type !== "send-to-morpher") return;

  try {
    const node = selectedNode();
    figma.ui.postMessage({ type: "status", state: "sending", text: `Exporting ${node.name}...` });

    const payload = await node.exportAsync({ format: "JSON_REST_V1" });
    const response = await fetch(MORPHER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: node.name,
        nodeId: node.id,
        payload,
      }),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || `Morpher returned HTTP ${response.status}`);
    }

    figma.ui.postMessage({
      type: "status",
      state: "success",
      text: `Saved as ${result.filename}`,
    });
  } catch (error) {
    figma.ui.postMessage({
      type: "status",
      state: "error",
      text: error instanceof Error ? error.message : String(error),
    });
  }
};
