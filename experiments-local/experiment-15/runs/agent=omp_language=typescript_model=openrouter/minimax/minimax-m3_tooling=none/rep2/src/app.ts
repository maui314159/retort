import express, { type Express, type NextFunction, type Request, type Response } from "express";
import type { BookRepository } from "./db.js";
import { createBooksRouter } from "./routes/books.js";
import { createHealthRouter } from "./routes/health.js";
import { ValidationError } from "./validation.js";

export interface AppDeps {
  repository: BookRepository;
}

export function createApp(deps: AppDeps): Express {
  const app = express();
  app.use(express.json({ limit: "64kb" }));

  app.use("/health", createHealthRouter());
  app.use("/books", createBooksRouter(deps.repository));

  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: "not found" });
  });

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError && "body" in err) {
      res.status(400).json({ error: "invalid JSON body" });
      return;
    }
    if (err instanceof ValidationError) {
      res.status(400).json({ error: err.message, details: err.details });
      return;
    }
    const message = err instanceof Error ? err.message : "internal server error";
    res.status(500).json({ error: message });
  });

  return app;
}
