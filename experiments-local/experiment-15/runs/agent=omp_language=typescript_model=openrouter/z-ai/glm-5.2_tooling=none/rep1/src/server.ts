import express, { type Request, type Response } from "express";
import type { Database as SqliteDb } from "better-sqlite3";
import { createDb } from "./db.js";
import { createBooksRouter } from "./books.js";

export function createApp(db: SqliteDb) {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "ok" });
  });

  app.use("/books", createBooksRouter(db));

  // 404 handler for unmatched routes
  app.use((req: Request, res: Response) => {
    res.status(404).json({ error: "not_found", message: `route ${req.method} ${req.path} not found` });
  });

  // Error handler for malformed JSON etc.
  app.use(
    (
      err: unknown,
      _req: Request,
      res: Response,
      _next: () => void,
    ) => {
      if (err instanceof SyntaxError && "body" in err && typeof (err as { body?: unknown }).body === "string") {
        res.status(400).json({ error: "invalid_json", message: "request body is not valid JSON" });
        return;
      }
      res.status(500).json({ error: "internal_error", message: "unexpected server error" });
    },
  );

  return app;
}

const DB_PATH = process.env.DB_PATH ?? "books.db";

function main(): void {
  const db = createDb(DB_PATH);
  const app = createApp(db);
  const port = Number(process.env.PORT ?? 3000);
  app.listen(port, () => {
    console.log(`Book collection API listening on http://localhost:${port}`);
    console.log(`SQLite database: ${DB_PATH}`);
  });
}

// Run only when executed directly, not when imported by tests.
const isMain = (() => {
  try {
    return process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href;
  } catch {
    return false;
  }
})();

if (isMain) {
  main();
}
