import express, { type Application, type Request, type Response } from "express";
import type { Database as DatabaseType } from "better-sqlite3";
import {
  createBook,
  deleteBook,
  getBook,
  listBooks,
  updateBook,
  type BookInput,
} from "./db.js";
import { validateBook } from "./validation.js";

export function createApp(db: DatabaseType): Application {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const input: BookInput = {
      title: req.body?.title,
      author: req.body?.author,
      year: req.body?.year,
      isbn: req.body?.isbn,
    };
    const errors = validateBook(input, true);
    if (errors.length > 0) {
      res.status(400).json({ errors });
      return;
    }
    const book = createBook(db, input);
    res.status(201).json(book);
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    const books = listBooks(db, author);
    res.status(200).json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    const book = getBook(db, id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    const input: Partial<BookInput> = {
      title: req.body?.title,
      author: req.body?.author,
      year: req.body?.year,
      isbn: req.body?.isbn,
    };
    const errors = validateBook(input, true);
    if (errors.length > 0) {
      res.status(400).json({ errors });
      return;
    }
    const updated = updateBook(db, id, input);
    if (!updated) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(updated);
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    const ok = deleteBook(db, id);
    if (!ok) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).send();
  });

  return app;
}
