import { BookStore } from "./db";
import { createApp } from "./app";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? "books.db";

const store = new BookStore(dbPath);
const app = createApp(store);

const server = app.listen(port, () => {
  console.log(`Book Collection API listening on http://localhost:${port}`);
});

function shutdown(): void {
  server.close(() => {
    store.close();
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
