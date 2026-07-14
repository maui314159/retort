import { createBookStore } from "./db.ts";
import { createServer } from "./server.ts";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? "books.db";

const store = createBookStore(dbPath);
const server = createServer({ port, store });

console.log(`📚 Book collection API listening on http://localhost:${server.port}`);

process.on("SIGINT", () => {
  console.log("\nShutting down...");
  store.close();
  server.stop();
  process.exit(0);
});

process.on("SIGTERM", () => {
  store.close();
  server.stop();
  process.exit(0);
});
