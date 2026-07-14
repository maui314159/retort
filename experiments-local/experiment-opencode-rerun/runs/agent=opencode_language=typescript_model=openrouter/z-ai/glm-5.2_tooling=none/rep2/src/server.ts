import { createApp } from "./app.js";
import { openDatabase } from "./db.js";

const port = Number(process.env.PORT) || 3000;
const dbPath = process.env.DB_PATH || "./books.db";

const db = openDatabase(dbPath);
const app = createApp(db);

const server = app.listen(port, () => {
  console.log(`Book collection API listening on port ${port}`);
});

function shutdown() {
  server.close(() => {
    db.close();
    process.exit(0);
  });
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
