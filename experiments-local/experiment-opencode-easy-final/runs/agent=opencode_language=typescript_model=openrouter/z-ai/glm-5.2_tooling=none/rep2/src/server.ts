import express, { type Application, type Request, type Response } from "express";
import { openDatabase, type Book } from "./db.js";
import { createRouter } from "./books.js";

export interface AppOptions {
  dbPath?: string;
}

export function createApp(opts: AppOptions = {}): Application {
  const db = openDatabase(opts.dbPath ?? process.env.DB_PATH ?? ":memory:");
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.use("/books", createRouter(db));

  // 404 handler
  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: "Not found" });
  });

  // Error handler
  app.use((err: Error, _req: Request, res: Response) => {
    if (err instanceof SyntaxError && "body" in err) {
      return res.status(400).json({ error: "Invalid JSON" });
    }
    console.error(err);
    return res.status(500).json({ error: "Internal server error" });
  });

  return app;
}

export { openDatabase, type Book };

export function run(): void {
  const app = createApp({ dbPath: process.env.DB_PATH ?? "./books.db" });
  const port = Number(process.env.PORT ?? 3000);
  app.listen(port, () => {
    console.log(`Books API listening on http://localhost:${port}`);
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  run();
}
