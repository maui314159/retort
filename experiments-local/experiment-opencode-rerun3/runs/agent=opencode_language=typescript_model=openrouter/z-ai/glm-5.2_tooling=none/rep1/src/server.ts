import { createApp } from "./app.js";
import { openDb, closeDb } from "./db.js";

const port = Number(process.env.PORT ?? 3000);
const dbFile = process.env.DB_FILE ?? "data/books.sqlite";

const db = openDb(dbFile);
const app = createApp(db);

const server = app.listen(port, () => {
  console.log(`Books API listening on http://localhost:${port}`);
});

function shutdown(): void {
  server.close(() => {
    closeDb(db);
    process.exit(0);
  });
  // Force exit after 5s if close hangs
  setTimeout(() => process.exit(0), 5000).unref();
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
