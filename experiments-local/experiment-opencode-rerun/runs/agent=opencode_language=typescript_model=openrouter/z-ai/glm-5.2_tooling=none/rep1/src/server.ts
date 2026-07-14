import { createApp } from "./app.js";
import { createDb } from "./db.js";

const port = Number(process.env.PORT ?? 3000);
const dbPath = process.env.DB_PATH ?? ":memory:";

const db = createDb(dbPath);
const app = createApp(db);

const server = app.listen(port, () => {
  console.log(`Book collection API listening on http://localhost:${port}`);
});

function shutdown() {
  server.close(() => {
    db.close();
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
