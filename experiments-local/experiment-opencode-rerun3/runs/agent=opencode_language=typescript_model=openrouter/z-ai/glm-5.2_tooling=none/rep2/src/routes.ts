import { Router, type Request, type Response } from "express";
import type Database from "better-sqlite3";
import {
  createBook,
  deleteBook,
  getBook,
  listBooks,
  updateBook,
  validateBook,
} from "./db.js";

export function createRouter(db: Database.Database): Router {
  const router = Router();

  router.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  router.get("/books", (req: Request, res: Response) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    const books = listBooks(db, author);
    res.status(200).json(books);
  });

  router.get("/books/:id", (req: Request, res: Response) => {
    const book = getBook(db, req.params.id);
    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(book);
  });

  router.post("/books", (req: Request, res: Response) => {
    const errors = validateBook(req.body ?? {});
    if (errors.length > 0) {
      res.status(400).json({ errors });
      return;
    }
    const book = createBook(db, req.body);
    res.status(201).json(book);
  });

  router.put("/books/:id", (req: Request, res: Response) => {
    const existing = getBook(db, req.params.id);
    if (!existing) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    const errors = validateBook(req.body ?? {});
    if (errors.length > 0) {
      res.status(400).json({ errors });
      return;
    }
    const book = updateBook(db, req.params.id, req.body);
    res.status(200).json(book);
  });

  router.delete("/books/:id", (req: Request, res: Response) => {
    const ok = deleteBook(db, req.params.id);
    if (!ok) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(204).send();
  });

  return router;
}
