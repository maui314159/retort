import { Router, type Request, type Response } from "express";
import type { Database as DBType } from "better-sqlite3";
import {
  createBook,
  listBooks,
  getBook,
  updateBook,
  deleteBook,
  type NewBook,
  type UpdateBook,
} from "./db.js";

function validateBook(input: Partial<NewBook>): string | null {
  if (input.title === undefined || input.title === null || String(input.title).trim() === "") {
    return "title is required";
  }
  if (input.author === undefined || input.author === null || String(input.author).trim() === "") {
    return "author is required";
  }
  if (input.year !== undefined && input.year !== null) {
    const y = Number(input.year);
    if (!Number.isInteger(y) || y < 0 || y > 9999) {
      return "year must be a valid integer between 0 and 9999";
    }
  }
  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== "string" || input.isbn.length > 32) {
      return "isbn must be a string of at most 32 characters";
    }
  }
  return null;
}

function parseBookInput(body: unknown): NewBook {
  const b = (body ?? {}) as Record<string, unknown>;
  return {
    title: typeof b.title === "string" ? b.title.trim() : (b.title as string),
    author: typeof b.author === "string" ? b.author.trim() : (b.author as string),
    year: b.year === undefined || b.year === null ? null : Number(b.year),
    isbn: b.isbn === undefined || b.isbn === null ? null : String(b.isbn),
  };
}

export function createRouter(db: DBType): Router {
  const router = Router();

  router.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  router.post("/books", (req: Request, res: Response) => {
    const input = parseBookInput(req.body);
    const error = validateBook(input);
    if (error) {
      res.status(400).json({ error });
      return;
    }
    const book = createBook(db, input);
    res.status(201).json(book);
  });

  router.get("/books", (req: Request, res: Response) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    res.status(200).json(listBooks(db, author));
  });

  router.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const book = getBook(db, id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  router.put("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const existing = getBook(db, id);
    if (!existing) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    const input: UpdateBook = parseBookInput(req.body);
    const error = validateBook({
      title: input.title ?? existing.title,
      author: input.author ?? existing.author,
      year: input.year,
      isbn: input.isbn,
    });
    if (error) {
      res.status(400).json({ error });
      return;
    }
    const book = updateBook(db, id, input);
    res.status(200).json(book);
  });

  router.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const deleted = deleteBook(db, id);
    if (!deleted) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).send();
  });

  return router;
}
