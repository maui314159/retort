/**
 * Brazilian Soccer MCP Server — stdio smoke test
 * ----------------------------------------------
 * Context block:
 *   End-to-end check (not a unit test): spawns the built MCP server, performs
 *   the JSON-RPC handshake (initialize + initialized notification), lists
 *   tools, and invokes one real query (search_matches for Flamengo in 2023)
 *   against the live Kaggle data. Asserts the protocol responds with tool
 *   results containing real match data. Run with: node smoke.mjs
 */

import { spawn } from "node:child_process";
import { once } from "node:events";

const proc = spawn("node", ["dist/index.js"], { stdio: ["pipe", "pipe", "inherit"] });

let buf = "";
const pending = new Map();
let nextId = 1;

proc.stdout.on("data", (chunk) => {
  buf += chunk.toString();
  let idx;
  while ((idx = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, idx).trim();
    buf = buf.slice(idx + 1);
    if (!line) continue;
    const msg = JSON.parse(line);
    if (msg.id !== undefined && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  }
});

function send(method, params, isNotification = false) {
  const id = isNotification ? undefined : nextId++;
  const msg = { jsonrpc: "2.0", method, params };
  if (id !== undefined) msg.id = id;
  proc.stdin.write(JSON.stringify(msg) + "\n");
  if (isNotification) return Promise.resolve();
  return new Promise((resolve) => pending.set(id, resolve));
}

// 1. Initialize handshake.
const init = await send("initialize", {
  protocolVersion: "2024-11-05",
  capabilities: {},
  clientInfo: { name: "smoke", version: "0.0.0" },
});
console.log("initialize result keys:", Object.keys(init.result ?? {}));
send("notifications/initialized", {}, true);

// 2. List tools.
const list = await send("tools/list", {});
const toolNames = list.result.tools.map((t) => t.name);
console.log("tools:", toolNames.join(", "));
if (toolNames.length !== 9) throw new Error(`expected 9 tools, got ${toolNames.length}`);

// 3. Call a real query against live data.
const call = await send("tools/call", {
  name: "search_matches",
  arguments: { team: "Flamengo", season: 2023, limit: 3 },
});
const text = call.result.content[0].text;
const matches = JSON.parse(text);
console.log("search_matches returned:", matches.length, "matches");
console.log("first match:", JSON.stringify(matches[0]));
if (!Array.isArray(matches) || matches.length === 0) throw new Error("no matches returned");

// 4. A player query.
const players = await send("tools/call", {
  name: "search_players",
  arguments: { nationality: "Brazil", sortBy: "overall", limit: 3 },
});
const ptext = JSON.parse(players.result.content[0].text);
console.log("top Brazilian players:", ptext.map((p) => `${p.name} (${p.overall})`).join(", "));
if (ptext.length === 0) throw new Error("no players returned");

proc.kill();
console.log("\nSMOKE TEST PASSED");
