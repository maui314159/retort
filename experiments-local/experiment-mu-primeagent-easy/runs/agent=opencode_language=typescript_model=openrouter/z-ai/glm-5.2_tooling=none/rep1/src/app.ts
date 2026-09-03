import express, { type Application, type NextFunction, type Request, type Response } from "express";
import { createBookDb, type BookDb } from "./db.js";
import type { BookInput } from "./types.js";

export interface AppOptions {
  dbPath?: string;
  db?: BookDb;
}

export interface BookApp {
  app: Application;
  db: BookDb;
  close(): void;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isValidYear(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value !== "number" || !Number.isFinite(value)) return false;
  return Number.isInteger(value);
}

function validateBookInput(body: unknown): { ok: true; value: BookInput } | { ok: false; message: string } {
  if (body === null || body === undefined || typeof body !== "object") {
    return { ok: false, message: "Request body must be a JSON object." };
  }
  const obj = body as Record<string, unknown>;

  if (!isNonEmptyString(obj.title)) {
    return { ok: false, message: "Field 'title' is required and must be a non-empty string." };
  }
  if (!isNonEmptyString(obj.author)) {
    return { ok: false, message: "Field 'author' is required and must be a non-empty string." };
  }
  if (obj.year !== undefined && obj.year !== null && !isValidYear(obj.year)) {
    return { ok: false, message: "Field 'year' must be an integer or null." };
  }
  if (obj.isbn !== undefined && obj.isbn !== null && typeof obj.isbn !== "string") {
    return { ok: false, message: "Field 'isbn' must be a string or null." };
  }

  const value: BookInput = {
    title: (obj.title as string).trim(),
    author: (obj.author as string).trim(),
    year: obj.year === undefined ? null : (obj.year as number | null),
    isbn: obj.isbn === undefined ? null : (obj.isbn as string | null),
  };
  return { ok: true, value };
}

export function createApp(options: AppOptions = {}): BookApp {
  const db = options.db ?? createBookDb(options.dbPath ?? ":memory:");
  const app: Application = express();

  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    const books = db.listBooks(author);
    res.status(200).json({ data: books });
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: "invalid_id", message: "Book id must be a positive integer." });
      return;
    }
    const book = db.getBook(id);
    if (!book) {
      res.status(404).json({ error: "not_found", message: `No book found with id ${id}.` });
      return;
    }
    res.status(200).json({ data: book });
  });

  app.post("/books", (req: Request, res: Response) => {
    const result = validateBookInput(req.body);
    if (!result.ok) {
      res.status(400).json({ error: "validation_error", message: result.message });
      return;
    }
    const book = db.createBook(result.value);
    res.status(201).json({ data: book });
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: "invalid_id", message: "Book id must be a positive integer." });
      return;
    }
    const result = validateBookInput(req.body);
    if (!result.ok) {
      res.status(400).json({ error: "validation_error", message: result.message });
      return;
    }
    const existing = db.getBook(id);
    if (!existing) {
      res.status(404).json({ error: "not_found", message: `No book found with id ${id}.` });
      return;
    }
    const book = db.updateBook(id, result.value);
    res.status(200).json({ data: book });
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: "invalid_id", message: "Book id must be a positive integer." });
      return;
    }
    const deleted = db.deleteBook(id);
    if (!deleted) {
      res.status(404).json({ error: "not_found", message: `No book found with id ${id}.` });
      return;
    }
    res.status(204).send();
  });

  app.use((req: Request, res: Response) => {
    res.status(404).json({ error: "not_found", message: `Route ${req.method} ${req.path} not found.` });
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError || (err && /JSON/i.test(err.message))) {
      res.status(400).json({ error: "invalid_json", message: "Request body must be valid JSON." });
      return;
    }
    res.status(500).json({ error: "internal_error", message: "An unexpected error occurred." });
  });

  return {
    app,
    db,
    close() {
      db.close();
    },
  };
}
