import express, { type Express, type Request, type Response } from "express";
import { BookStore } from "./bookStore";
import { ValidationError, validateCreate, validateUpdate } from "./validation";

export function createApp(dbPath?: string): Express {
  const app = express();
  app.use(express.json());

  const store = new BookStore(dbPath);
  app.locals.store = store;

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    try {
      const input = validateCreate(req.body);
      const book = store.create(input);
      res.status(201).json(book);
    } catch (err) {
      handleError(err, res);
    }
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author;
    const authorFilter =
      typeof author === "string" ? author : undefined;
    const books = store.list(authorFilter);
    res.status(200).json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "Invalid id" });
      return;
    }
    const book = store.getById(id);
    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "Invalid id" });
      return;
    }
    try {
      const input = validateUpdate(req.body);
      const book = store.update(id, input);
      if (!book) {
        res.status(404).json({ error: "Book not found" });
        return;
      }
      res.status(200).json(book);
    } catch (err) {
      handleError(err, res);
    }
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "Invalid id" });
      return;
    }
    const deleted = store.delete(id);
    if (!deleted) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(204).send();
  });

  return app;
}

function parseId(raw: string): number | null {
  const n = Number(raw);
  if (!Number.isInteger(n) || n < 1) return null;
  return n;
}

function handleError(err: unknown, res: Response): void {
  if (err instanceof ValidationError) {
    res.status(err.statusCode).json({ error: err.message });
    return;
  }
  res.status(500).json({ error: "Internal server error" });
}
