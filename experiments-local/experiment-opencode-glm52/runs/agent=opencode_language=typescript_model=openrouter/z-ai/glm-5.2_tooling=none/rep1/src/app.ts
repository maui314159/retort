import express, { type Application, type NextFunction, type Request, type Response } from "express";
import type { Database as DB } from "better-sqlite3";
import {
  createBook,
  deleteBook,
  getBook,
  listBooks,
  updateBook,
} from "./db.js";
import { normalizeBookInput, validateBook } from "./validation.js";

export function createApp(db: DB): Application {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req, res) => {
    const errors = validateBook(req.body);
    if (errors.length > 0) {
      res.status(400).json({ errors });
      return;
    }
    const book = createBook(db, normalizeBookInput(req.body));
    res.status(201).json(book);
  });

  app.get("/books", (req, res) => {
    const author = req.query.author;
    const authorFilter =
      typeof author === "string" ? author : undefined;
    res.status(200).json(listBooks(db, authorFilter));
  });

  app.get("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const book = getBook(db, id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const errors = validateBook(req.body);
    if (errors.length > 0) {
      res.status(400).json({ errors });
      return;
    }
    const updated = updateBook(db, id, normalizeBookInput(req.body));
    if (!updated) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(updated);
  });

  app.delete("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const ok = deleteBook(db, id);
    if (!ok) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).send();
  });

  app.use((err: Error & { type?: string }, _req: Request, res: Response, _next: NextFunction) => {
    if (err.type === "entity.parse.failed") {
      res.status(400).json({ error: "invalid JSON body" });
      return;
    }
    res.status(500).json({ error: "internal server error" });
  });

  return app;
}
