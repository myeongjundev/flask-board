const fs = require("fs");
const crypto = require("crypto");

const directory = process.argv[2];
const files = fs.readdirSync(directory);
const workflows = files.map((file) =>
  JSON.parse(fs.readFileSync(`${directory}/${file}`, "utf8")),
);
const primary = workflows.find((workflow) => workflow.id === "xmRPw40G5rzskSwx");
const desiredDiscord = primary.nodes.find((node) => node.name === "디스코드")
  ?.parameters?.url;
const hash = (value) =>
  crypto.createHash("sha256").update(value || "").digest("hex").slice(0, 12);

function findStaleValues(value, path, output) {
  if (typeof value === "string") {
    if (/lsy|localhost:5000|C:\\Users\\user\\Desktop|SKT aleph|board-project/i.test(value)) {
      output.push({
        path,
        value: value.replace(/https?:\/\/[^\s"}]+/g, "<redacted-url>"),
      });
    }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => findStaleValues(item, `${path}[${index}]`, output));
    return;
  }
  if (value && typeof value === "object") {
    Object.entries(value).forEach(([key, item]) =>
      findStaleValues(item, `${path}.${key}`, output),
    );
  }
}

console.log({ desiredDiscordHash: hash(desiredDiscord) });
for (const workflow of workflows) {
  const hits = [];
  findStaleValues(workflow, "$", hits);
  console.log("\nWORKFLOW", workflow.id, workflow.name);
  console.log("hits", hits);
  for (const node of workflow.nodes) {
    if (node.type !== "n8n-nodes-base.httpRequest") continue;
    const url = node.parameters?.url || "";
    let safeUrl = url ? "expression" : "none";
    try {
      const parsed = new URL(url);
      safeUrl = `${parsed.protocol}//${parsed.hostname}${parsed.pathname.replace(
        /\/[^/]{16,}/g,
        "/<redacted>",
      )}`;
    } catch {}
    console.log({
      node: node.name,
      url: safeUrl,
      urlHash: hash(url),
      isDesiredDiscord: node.name.startsWith("디스코드")
        ? hash(url) === hash(desiredDiscord)
        : undefined,
      headers: (node.parameters?.headerParameters?.parameters || []).map((header) => ({
        name: header.name,
        valueHash: hash(header.value),
        length: (header.value || "").length,
      })),
    });
  }
}
