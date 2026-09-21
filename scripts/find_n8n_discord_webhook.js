const fs = require("fs");

const directory = process.argv[2];
const desiredName = process.argv[3];
if (!directory || !desiredName) {
  throw new Error("workflow directory and Discord webhook name are required");
}

const urls = new Set();
for (const file of fs.readdirSync(directory)) {
  const workflow = JSON.parse(fs.readFileSync(`${directory}/${file}`, "utf8"));
  for (const node of workflow.nodes || []) {
    if (
      node.type === "n8n-nodes-base.httpRequest" &&
      node.name.startsWith("디스코드") &&
      node.parameters?.url
    ) {
      urls.add(node.parameters.url);
    }
  }
}

(async () => {
  for (const url of urls) {
    try {
      const response = await fetch(url);
      const metadata = await response.json();
      if (response.ok && metadata.name === desiredName) {
        process.stdout.write(url);
        return;
      }
    } catch {}
  }
  throw new Error(`active Discord webhook named ${desiredName} was not found`);
})().catch((error) => {
  console.error(error.message);
  process.exit(2);
});
