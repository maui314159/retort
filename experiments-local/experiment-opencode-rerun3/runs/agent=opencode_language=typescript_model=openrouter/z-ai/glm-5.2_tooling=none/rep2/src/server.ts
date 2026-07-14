import express from "express";
import { createDb } from "./db.js";
import { createRouter } from "./routes.js";

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const DB_PATH = process.env.DB_PATH ?? ":memory:";

export function createApp() {
  const db = createDb(DB_PATH);
  const app = express();
  app.use(express.json());
  app.use(createRouter(db));
  return { app, db };
}

if (process.env.NODE_ENV !== "test") {
  const { app } = createApp();
  app.listen(PORT, () => {
    console.log(`Book API listening on http://localhost:${PORT}`);
  });
}
