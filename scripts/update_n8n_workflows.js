const fs = require("fs");

const directory = process.argv[2];
const student = process.env.STUDENT_NAME;
const securityKey = process.env.SECURITY_API_KEY;
const adminKey = process.env.ADMIN_API_KEY;
const discordWebhookUrl = process.env.DISCORD_WEBHOOK_URL;
const slackWebhookUrl = process.env.SLACK_WEBHOOK_URL;
const telegramBotToken = process.env.TELEGRAM_BOT_TOKEN;
const telegramChatId = process.env.TELEGRAM_CHAT_ID;
if (!directory || !student || !securityKey || !adminKey) {
  throw new Error("directory and STUDENT_NAME/SECURITY_API_KEY/ADMIN_API_KEY are required");
}

const files = fs.readdirSync(directory);
const workflows = files.map((file) => ({
  file,
  workflow: JSON.parse(fs.readFileSync(`${directory}/${file}`, "utf8")),
}));
const primary = workflows.find(({ workflow }) => workflow.id === "xmRPw40G5rzskSwx")
  ?.workflow;
if (!primary) throw new Error("primary notification workflow was not found");

function notificationUrl(prefix) {
  const node = primary.nodes.find((item) => item.name === prefix);
  if (!node?.parameters?.url) throw new Error(`${prefix} URL was not found`);
  return node.parameters.url;
}

const notificationUrls = {
  디스코드: discordWebhookUrl || notificationUrl("디스코드"),
  슬랙: slackWebhookUrl || notificationUrl("슬랙"),
  텔레그램: telegramBotToken
    ? `https://api.telegram.org/bot${telegramBotToken}/sendMessage`
    : notificationUrl("텔레그램"),
};

function replaceConfiguration(value) {
  if (typeof value === "string") {
    return value
      .replace(/\blsy\b/g, student)
      .replace(/http:\/\/localhost:5000/g, "http://host.docker.internal:5000");
  }
  if (Array.isArray(value)) return value.map(replaceConfiguration);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, replaceConfiguration(item)]),
    );
  }
  return value;
}

function setHeader(node, name, value) {
  node.parameters.sendHeaders = true;
  node.parameters.headerParameters ||= { parameters: [] };
  node.parameters.headerParameters.parameters ||= [];
  let header = node.parameters.headerParameters.parameters.find(
    (item) => item.name.toLowerCase() === name.toLowerCase(),
  );
  if (!header) {
    header = { name, value };
    node.parameters.headerParameters.parameters.push(header);
  }
  header.value = value;
}

for (const entry of workflows) {
  entry.workflow = replaceConfiguration(entry.workflow);

  if (entry.workflow.id === "fl7ouxwqMiENm56O") {
    const webhook = entry.workflow.nodes.find((node) => node.name === "Webhook");
    const decision = entry.workflow.nodes.find((node) => node.name === "판정 (회수)");
    const allowMessage = entry.workflow.nodes.find((node) => node.name === "메세지 허용");
    const denyMessage = entry.workflow.nodes.find((node) => node.name === "메세지 거부");
    if (!webhook || !decision || !allowMessage || !denyMessage) {
      throw new Error("vulnerability scan workflow nodes were not found");
    }
    webhook.parameters.path = "vuln-scan";
    decision.parameters.jsCode = `const DENY_LEVEL = 10;
const DEFAULT_STUDENT = ${JSON.stringify(student)};
const SENSITIVE_PORTS = new Set([3306, 9000, 12201]);

const clean = (value) => {
  const text = (value ?? "").toString().trim();
  return (!text || text.startsWith("\${")) ? null : text;
};

const out = [];
for (const item of $input.all()) {
  const input = item.json ?? {};
  const body = input.body ?? input;

  if (clean(body.host) && Array.isArray(body.open)) {
    const ports = body.open.map(Number).filter(Number.isInteger);
    const exposed = ports.filter((port) => SENSITIVE_PORTS.has(port));
    const decision = exposed.length ? "deny" : "allow";
    out.push({ json: {
      student: DEFAULT_STUDENT,
      src_ip: clean(body.host),
      fail_count: 0,
      decision,
      severity: exposed.length ? "High" : "Low",
      reason: exposed.length
        ? \`열린 포트: \${ports.join(", ")} · MySQL/SIEM 노출(\${exposed.join(", ")}) — 바인딩·인증 점검 필요\`
        : \`열린 포트: \${ports.join(", ") || "없음"} · 민감 서비스 외부 노출 없음\`,
      source: "vulnerability-scan",
      generated_at: new Date().toISOString(),
    }});
    continue;
  }

  const student = clean(body.student) ?? DEFAULT_STUDENT;
  const list = Array.isArray(body.alerts) ? body.alerts
    : Array.isArray(body.events) ? body.events : [body];
  for (const event of list) {
    if (!event || typeof event !== "object") continue;
    const username = clean(event.user ?? event.username);
    const srcIp = clean(event.src_ip ?? event.ip) ?? "0.0.0.0";
    const who = clean(event.student) ?? student;
    if (username) {
      const rule = clean(event.rule) ?? "priv-unauthorized-admin";
      out.push({ json: {
        username, student: who, src_ip: srcIp, severity: "High",
        reason: \`과잉권한 자동회수: \${rule} (부여자 \${clean(event.granted_by) ?? "?"})\`,
        source: "privilege-guard", generated_at: new Date().toISOString(),
      }});
      continue;
    }
    if (!("level" in event) && !("ip" in event) && !("fail_count" in event)) continue;
    const level = Number(event.level) || 0;
    const eventDecision = level >= DENY_LEVEL ? "deny" : "allow";
    out.push({ json: {
      student: who, src_ip: srcIp, level,
      rule: clean(event.rule) ?? "", fail_count: Number(event.fail_count ?? 0),
      severity: level >= 10 ? "High" : level >= 7 ? "Medium" : "Low",
      decision: eventDecision,
      reason: \`level \${level} (rule \${clean(event.rule) ?? "-"}) -> \${eventDecision}\`,
      source: "login_alert_lab", generated_at: new Date().toISOString(),
    }});
  }
}
return out;`;
    allowMessage.parameters.assignments.assignments[0].value =
      "={{ $json.source === 'vulnerability-scan' ? '✅ [취약점 점검:양호] ' + $json.src_ip + ' · ' + $json.reason + ' (학생 ' + $json.student + ')' : '✅ [허용] ' + $json.src_ip + ' · ' + $json.student }}";
    denyMessage.parameters.assignments.assignments[0].value =
      "={{ $json.source === 'vulnerability-scan' ? '🔎🚨 [취약점 점검:주의] ' + $json.src_ip + '\\n' + $json.reason + ' (학생 ' + $json.student + ')' : '🚫 [거부] ' + $json.src_ip + ' · ' + $json.reason + ' · ' + $json.severity + ' · ' + $json.student }}";
  }

  for (const node of entry.workflow.nodes) {
    if (node.type === "n8n-nodes-base.if") {
      for (const condition of node.parameters?.conditions?.conditions || []) {
        if (
          condition.leftValue === "={{ $json.decision }}" &&
          typeof condition.rightValue === "string" &&
          condition.rightValue.trim() === "deny"
        ) {
          condition.rightValue = "deny";
        }
      }
    }

    if (node.type !== "n8n-nodes-base.httpRequest") continue;

    for (const [prefix, url] of Object.entries(notificationUrls)) {
      if (node.name.startsWith(prefix)) {
        node.parameters.url = url;
        node.onError = "continueRegularOutput";
        if (prefix === "텔레그램" && telegramChatId) {
          const body = node.parameters.jsonBody || "";
          node.parameters.jsonBody = body.replace(
            /("chat_id"\s*:\s*)(-?\d+|"[^"]*")/,
            `$1${JSON.stringify(telegramChatId)}`,
          );
        }
      }
    }

    const url = node.parameters?.url || "";
    if (url.includes("/api/security/events")) {
      node.parameters.url = "http://host.docker.internal:5000/api/security/events";
      setHeader(node, "X-API-Key", securityKey);
    } else if (url.includes("/api/admin/")) {
      node.parameters.url = url.replace(
        /^http:\/\/[^/]+/,
        "http://host.docker.internal:5000",
      );
      setHeader(node, "X-API-Key", adminKey);
    }
  }
  fs.writeFileSync(
    `${directory}/${entry.file}`,
    JSON.stringify(entry.workflow),
  );
  console.log(`updated ${entry.workflow.id} | ${entry.workflow.name}`);
}
