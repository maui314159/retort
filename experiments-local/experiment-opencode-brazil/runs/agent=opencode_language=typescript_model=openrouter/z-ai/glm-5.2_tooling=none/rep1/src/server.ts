import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./tools.js";

export const runServer = async (dataDir?: string): Promise<void> => {
  const server = createServer(dataDir);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  const cleanup = async () => {
    try {
      await server.close();
    } catch {}
    process.exit(0);
  };
  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);
};
