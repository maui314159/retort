import { createApp } from "./app.js";
import { openDatabase } from "./db.js";

const dbPath = process.env.DB_PATH ?? "./data/books.sqlite";
const port = Number(process.env.PORT ?? 3000);

const db = openDatabase(dbPath);
const app = createApp(db);

const server = app.listen(port, () => {
  console.log(`Books API listening on http://localhost:${port}`);
});

function shutdown() {
  console.log("Shutting down...");
  server.close(() => {
    db.close();
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
