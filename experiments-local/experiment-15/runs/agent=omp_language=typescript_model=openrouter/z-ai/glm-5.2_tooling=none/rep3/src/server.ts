import { serve } from "@hono/node-server";
import { closeDatabase, openDatabase } from "./db.js";
import { createApp } from "./app.js";

const PORT = Number(process.env.PORT ?? 3000);
const DB_PATH = process.env.DB_PATH ?? "books.db";

const db = openDatabase(DB_PATH);
const app = createApp(db);

const server = serve({ fetch: app.fetch, port: PORT }, (info) => {
  console.log(`book-api listening on http://localhost:${info.port}`);
});

function shutdown(signal: string): void {
  console.log(`received ${signal}, shutting down`);
  server.close();
  closeDatabase(db);
  process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
