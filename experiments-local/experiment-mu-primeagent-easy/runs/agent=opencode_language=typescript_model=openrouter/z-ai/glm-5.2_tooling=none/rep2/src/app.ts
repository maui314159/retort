import express, { Request, Response, NextFunction } from "express";
import type { BookStore } from "./db.js";
import { validateBook } from "./validation.js";

export interface AppDeps {
  store: BookStore;
}

function parseId(raw: string): number | null {
  const n = Number(raw);
  return Number.isInteger(n) ? n : null;
}

export function createApp(deps: AppDeps) {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.get("/books", (req: Request, res: Response) => {
    const author =
      typeof req.query.author === "string" ? req.query.author : undefined;
    const books = deps.store.listAll(author);
    res.status(200).json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const book = deps.store.getById(id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.post("/books", (req: Request, res: Response) => {
    const result = validateBook(req.body);
    if (!result.valid) {
      res.status(400).json({ error: result.errors.join("; ") });
      return;
    }
    const book = deps.store.create(result.value);
    res.status(201).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const result = validateBook(req.body);
    if (!result.valid) {
      res.status(400).json({ error: result.errors.join("; ") });
      return;
    }
    const book = deps.store.update(id, result.value);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const deleted = deps.store.delete(id);
    if (!deleted) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).send();
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (
      err instanceof SyntaxError &&
      "status" in err &&
      (err as { status: number }).status === 400 &&
      "body" in err
    ) {
      res.status(400).json({ error: "Invalid JSON body" });
      return;
    }
    res.status(500).json({ error: "Internal server error" });
  });

  return app;
}
