const sqlite3 = require("sqlite3").verbose();
const { parse } = require("flatted");

const workflowId = process.argv[2];
const nodeNames = process.argv.slice(3);
if (!workflowId) throw new Error("workflow id is required");

const database = new sqlite3.Database(
  "/home/node/.n8n/database.sqlite",
  sqlite3.OPEN_READONLY,
);
database.get(
  `SELECT e.id, e.status, d.data
     FROM execution_entity e
     JOIN execution_data d ON d.executionId = e.id
    WHERE e.workflowId = ?
    ORDER BY e.id DESC
    LIMIT 1`,
  [workflowId],
  (error, row) => {
    if (error) throw error;
    if (!row) throw new Error("no execution found");
    const runData = parse(row.data).resultData.runData;
    console.log({ executionId: row.id, status: row.status });
    for (const name of nodeNames) {
      console.log(
        name,
        JSON.stringify((runData[name] || []).map((run) => ({
          status: run.executionStatus,
          error: run.error?.message || null,
          output: (run.data?.main || []).map((branch) =>
            (branch || []).slice(0, 3).map((item) => item.json),
          ),
        })), null, 2),
      );
    }
    database.close();
  },
);
