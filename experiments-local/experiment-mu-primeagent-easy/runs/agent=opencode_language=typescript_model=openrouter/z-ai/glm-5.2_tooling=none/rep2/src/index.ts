import { createApp } from "./app.js";
import { BookStore } from "./db.js";

const dbPath = process.env.DB_PATH ?? "books.db";
const store = new BookStore(dbPath);
const app = createApp({ store });

const port = process.env.PORT ? Number(process.env.PORT) : 3000;

const server = app.listen(port, () => {
  console.log(`Book collection API listening on http://localhost:${port}`);
});

const shutdown = () => {
  server.close(() => {
    store.close();
    process.exit(0);
  });
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
