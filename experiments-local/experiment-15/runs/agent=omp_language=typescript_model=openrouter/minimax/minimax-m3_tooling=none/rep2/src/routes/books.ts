import { Router, type Request, type Response, type NextFunction } from "express";
import type { BookRepository, Book } from "../db.js";
import { parseCreateBook, parseUpdateBook, type BookInput, type BookUpdate } from "../validation.js";

const ID_PATTERN = /^\d+$/;

function parseId(raw: string): number | null {
  if (!ID_PATTERN.test(raw)) return null;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

function mergeUpdate(existing: Book, update: BookUpdate): BookInput {
  return {
    title: update.title ?? existing.title,
    author: update.author ?? existing.author,
    year: update.year !== undefined ? update.year : existing.year,
    isbn: update.isbn !== undefined ? update.isbn : existing.isbn,
  };
}

export function createBooksRouter(repo: BookRepository): Router {
  const router = Router();

  router.get("/", (req: Request, res: Response) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    const books = repo.list(author);
    res.status(200).json(books);
  });

  router.get("/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id ?? "");
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const book = repo.get(id);
    if (!book) {
      res.status(404).json({ error: `book ${id} not found` });
      return;
    }
    res.status(200).json(book);
  });

  router.post("/", (req: Request, res: Response, next: NextFunction) => {
    try {
      const input = parseCreateBook(req.body);
      const created = repo.create(input);
      res.status(201).json(created);
    } catch (err) {
      next(err);
    }
  });

  router.put("/:id", (req: Request, res: Response, next: NextFunction) => {
    const id = parseId(req.params.id ?? "");
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    try {
      const update = parseUpdateBook(req.body);
      const existing = repo.get(id);
      if (!existing) {
        res.status(404).json({ error: `book ${id} not found` });
        return;
      }
      const merged = mergeUpdate(existing, update);
      const updated = repo.update(id, merged);
      if (!updated) {
        res.status(404).json({ error: `book ${id} not found` });
        return;
      }
      res.status(200).json(updated);
    } catch (err) {
      next(err);
    }
  });

  router.delete("/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id ?? "");
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const removed = repo.remove(id);
    if (!removed) {
      res.status(404).json({ error: `book ${id} not found` });
      return;
    }
    res.status(204).end();
  });

  return router;
}
