import express, { type Express, type Request, type Response, type NextFunction } from "express";
import { type Db, openDatabase } from "./db.js";
import { BookRepository } from "./books.js";
import { booksRouter } from "./routes/books.js";

export interface AppDeps {
  db?: Db;
}

export function createApp(deps: AppDeps = {}): { app: Express; db: Db } {
  const db = deps.db ?? openDatabase(resolveDbPath());
  const repo = new BookRepository(db);
  const app = express();

  app.use(express.json({ limit: "64kb" }));

  app.get("/health", (_req: Request, res: Response) => {
    let dbOk = true;
    try {
      db.prepare("SELECT 1").get();
    } catch {
      dbOk = false;
    }
    res.status(200).json({
      status: dbOk ? "ok" : "degraded",
      uptime_seconds: Math.round(process.uptime()),
      db: dbOk ? "ok" : "down",
    });
  });

  app.use("/books", booksRouter(repo));

  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: "NotFound", message: "route not found" });
  });

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const message = err instanceof Error ? err.message : "internal error";
    res.status(500).json({ error: "InternalServerError", message });
  });

  return { app, db };
}

function resolveDbPath(): string {
  const fromEnv = process.env.BOOKS_DB_PATH;
  if (fromEnv && fromEnv.length > 0) return fromEnv;
  return process.env.NODE_ENV === "test"
    ? ":memory:"
    : "./data/books.sqlite";
}
