/**
 * brazilian-soccer-mcp — MCP server smoke test
 *
 * Context block
 * ============
 * See src/types.ts for the top-level project context block.
 *
 * Boots the real stdio MCP server as a subprocess, performs the MCP
 * initialization handshake, lists tools, and invokes `last_match_between`
 * to confirm the server end-to-end (not just the engine) works.
 */

import { describe, it, expect } from "vitest";
import { spawn } from "node:child_process";
import { join } from "node:path";

let id = 0;
function rpc(method: string, params: unknown): string {
  return JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }) + "\n";
}

async function callServer(): Promise<{
  init: unknown;
  tools: { name: string }[];
  result: unknown;
}> {
  const serverPath = join(process.cwd(), "dist", "index.js");
  return new Promise((resolve, reject) => {
    const child = spawn("node", [serverPath], { stdio: ["pipe", "pipe", "inherit"] });
    let buf = "";
    const messages: Record<string, unknown>[] = [];
    child.stdout.on("data", (chunk) => {
      buf += chunk.toString();
      let idx;
      while ((idx = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, idx);
        buf = buf.slice(idx + 1);
        if (!line.trim()) continue;
        try {
          messages.push(JSON.parse(line));
        } catch {
          // ignore
        }
      }
    });
    child.on("error", reject);

    // Send init + initialized notification.
    child.stdin.write(
      rpc("initialize", {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "smoke-test", version: "1.0.0" },
      }),
    );
    child.stdin.write(
      JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n",
    );
    child.stdin.write(rpc("tools/list", {}));

    const toolCallId = id + 1;
    child.stdin.write(
      rpc("tools/call", {
        name: "last_match_between",
        arguments: { team_a: "Flamengo", team_b: "Fluminense" },
      }),
    );

    setTimeout(() => {
      child.kill();
      const initResp = messages.find((m) => m.id === 1);
      const toolsResp = messages.find((m) => m.id === 2) as
        | { result?: { tools?: { name: string }[] } }
        | undefined;
      const callResp = messages.find((m) => m.id === toolCallId);
      resolve({
        init: initResp,
        tools: toolsResp?.result?.tools ?? [],
        result: callResp,
      });
    }, 4000);
  });
}

describe("Feature: MCP server over stdio", () => {
  it("Scenario: server initializes, lists tools, and answers a tool call", async () => {
    const r = await callServer();
    expect(r.init).toBeTruthy();
    expect(r.tools.length).toBeGreaterThanOrEqual(11);
    expect(r.tools.some((t) => t.name === "last_match_between")).toBe(true);
    expect(r.result).toBeTruthy();
    const content = (r.result as { result?: { content?: { text?: string }[] } })
      ?.result?.content?.[0]?.text;
    expect(typeof content).toBe("string");
    expect(content!.toLowerCase()).toContain("flamengo");
  }, 15000);
});
