import { createApp } from "./app.js";
import { openDatabase, createRepository } from "./db.js";

const PORT = Number(process.env.PORT ?? 3000);
const DB_PATH = process.env.DB_PATH ?? "books.db";

const db = openDatabase(DB_PATH);
const repo = createRepository(db);
const app = createApp({ repository: repo });

const server = app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`book-collection-api listening on http://localhost:${PORT} (db: ${DB_PATH})`);
});

function shutdown(signal: string) {
  // eslint-disable-next-line no-console
  console.log(`received ${signal}, shutting down`);
  server.close(() => {
    repo.close();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 5000).unref();
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
