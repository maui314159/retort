import express from "express";
import type Database from "better-sqlite3";
import { openDatabase } from "./db.js";
import { buildBooksRouter } from "./routes/books.js";
import { buildHealthRouter } from "./routes/health.js";

export interface AppConfig {
  dbPath: string;
  port: number;
}

export function createApp(config: AppConfig): { app: express.Express; db: Database.Database } {
  const db = openDatabase(config.dbPath);
  const app = express();
  app.use(express.json());

  app.use("/health", buildHealthRouter());
  app.use("/books", buildBooksRouter(db));

  app.use((req, res) => {
    res.status(404).json({ error: "not_found", path: req.path });
  });

  return { app, db };
}

export function startServer(config: AppConfig): { close: () => void; port: number; db: Database.Database } {
  const { app, db } = createApp(config);
  const server = app.listen(config.port);
  return {
    close: () => {
      server.close();
      db.close();
    },
    port: config.port,
    db,
  };
}

export const DEFAULT_DB_PATH = process.env.DB_PATH ?? "books.db";
export const DEFAULT_PORT = Number(process.env.PORT ?? 3000);

if (import.meta.url === `file://${process.argv[1]}`) {
  const server = startServer({ dbPath: DEFAULT_DB_PATH, port: DEFAULT_PORT });
  console.log(`Books API listening on port ${server.port} (db: ${DEFAULT_DB_PATH})`);
  process.on("SIGINT", () => {
    server.close();
    process.exit(0);
  });
  process.on("SIGTERM", () => {
    server.close();
    process.exit(0);
  });
}
