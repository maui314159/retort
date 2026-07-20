import { createDatabase } from "./db.ts";
import { createBookServer } from "./server.ts";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? "books.db";

const db = createDatabase(dbPath);
const server = createBookServer(db);

server.listen(port, () => {
  console.log(`Book API listening on http://localhost:${port}`);
  console.log(`Using SQLite database: ${dbPath}`);
});

for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => {
    server.close(() => {
      db.close();
      process.exit(0);
    });
  });
}
