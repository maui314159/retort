import express from "express";
import { openDatabase } from "./db.js";
import { createBooksRouter, createBooksService } from "./books.js";
import type { Database as DB } from "better-sqlite3";
import { fileURLToPath } from "node:url";
import path from "node:path";

export function isMainModule(): boolean {
  if (!process.argv[1]) return false;
  try {
    return fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
  } catch {
    return false;
  }
}

export interface AppOptions {
  dbPath?: string;
  onClose?: () => void;
}

export function createApp(options: AppOptions = {}) {
  const dbPath = options.dbPath ?? process.env.DB_PATH ?? "books.db";
  const db: DB = openDatabase(dbPath);
  const service = createBooksService(db);
  const app = express();
  app.use(express.json());
  app.use(createBooksRouter(service));
  // 404 handler for unknown routes
  app.use((req, res) => {
    res.status(404).json({ error: `route not found: ${req.method} ${req.url}` });
  });
  // error handler
  app.use(
    (
      err: unknown,
      _req: express.Request,
      res: express.Response,
      _next: express.NextFunction,
    ) => {
      if (
        err instanceof SyntaxError &&
        "status" in err &&
        (err as { status?: number }).status === 400 &&
        "body" in err
      ) {
        res.status(400).json({ error: "invalid JSON body" });
        return;
      }
      res.status(500).json({ error: "internal server error" });
    },
  );

  const close = () => {
    db.close();
    options.onClose?.();
  };

  return { app, close, db, service };
}

if (isMainModule()) {
  const port = Number(process.env.PORT ?? 3000);
  const { app, close } = createApp();
  const server = app.listen(port, () => {
    console.log(`books-api listening on http://localhost:${port}`);
  });
  const shutdown = () => {
    server.close(() => {
      close();
      process.exit(0);
    });
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}
