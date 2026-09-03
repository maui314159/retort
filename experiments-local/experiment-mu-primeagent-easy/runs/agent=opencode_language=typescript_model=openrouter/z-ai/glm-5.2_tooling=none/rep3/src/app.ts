import express, { Request, Response, NextFunction } from "express";
import { BookStore, ValidationError, BookInput } from "./store";

export interface AppOptions {
  dbPath?: string;
}

export function createApp(options: AppOptions = {}) {
  const store = new BookStore(options.dbPath ?? ":memory:");
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response, next: NextFunction) => {
    try {
      const book = store.create(req.body as BookInput);
      res.status(201).json(book);
    } catch (err) {
      next(err);
    }
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    res.json(store.all(author));
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    const book = store.get(id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.json(book);
  });

  app.put("/books/:id", (req: Request, res: Response, next: NextFunction) => {
    const id = Number(req.params.id);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    try {
      const book = store.update(id, req.body as BookInput);
      if (!book) {
        res.status(404).json({ error: "book not found" });
        return;
      }
      res.json(book);
    } catch (err) {
      next(err);
    }
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    if (store.delete(id)) {
      res.status(204).send();
      return;
    }
    res.status(404).json({ error: "book not found" });
  });

  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof ValidationError) {
      res.status(err.status).json({ error: err.message });
      return;
    }
    res.status(400).json({ error: "invalid request body" });
  });

  return { app, store };
}
