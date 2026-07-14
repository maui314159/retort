import { createApp } from "./app";

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const DB_PATH = process.env.DB_PATH || "./books.db";

const app = createApp(DB_PATH);

const server = app.listen(PORT, () => {
  console.log(`Books API listening on http://localhost:${PORT}`);
});

function shutdown() {
  server.close(() => {
    const store = app.locals.store;
    if (store && typeof store.close === "function") {
      store.close();
    }
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
