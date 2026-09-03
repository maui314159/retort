import { createApp } from "./app.js";

const PORT = Number(process.env.PORT ?? 3000);
const DB_PATH = process.env.DB_PATH ?? "books.db";

const bookApp = createApp({ dbPath: DB_PATH });

const server = bookApp.app.listen(PORT, () => {
  console.log(`Book collection API listening on http://localhost:${PORT}`);
  console.log(`Using database: ${DB_PATH}`);
});

function shutdown(signal: string) {
  console.log(`\nReceived ${signal}, shutting down...`);
  server.close(() => {
    bookApp.close();
    process.exit(0);
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

export { server };
