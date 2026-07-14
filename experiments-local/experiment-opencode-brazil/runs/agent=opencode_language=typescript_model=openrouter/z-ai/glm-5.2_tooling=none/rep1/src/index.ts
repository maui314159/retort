#!/usr/bin/env node
import { runServer } from "./server.js";

const dataDir = process.env.BRAZILIAN_SOCCER_DATA_DIR;
runServer(dataDir).catch((err) => {
  console.error("Failed to start MCP server:", err);
  process.exit(1);
});
