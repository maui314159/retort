import express, { type Express, type Request, type Response } from "express";
import type { Database } from "better-sqlite3";
import type { Book } from "./db.js";

interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}

function validateBookInput(
  body: BookInput,
  { partial }: { partial: boolean }
): { errors: string[]; data: { title?: string; author?: string; year?: number | null; isbn?: string | null } } {
  const errors: string[] = [];
  const data: { title?: string; author?: string; year?: number | null; isbn?: string | null } = {};

  const has = (key: keyof BookInput) => body[key] !== undefined;

  if (!partial || has("title")) {
    if (typeof body.title !== "string" || body.title.trim() === "") {
      errors.push("title is required and must be a non-empty string");
    } else {
      data.title = body.title.trim();
    }
  }

  if (!partial || has("author")) {
    if (typeof body.author !== "string" || body.author.trim() === "") {
      errors.push("author is required and must be a non-empty string");
    } else {
      data.author = body.author.trim();
    }
  }

  if (has("year")) {
    if (body.year === null) {
      data.year = null;
    } else if (
      typeof body.year !== "number" ||
      !Number.isInteger(body.year) ||
      (body.year as number) < 0 ||
      (body.year as number) > 9999
    ) {
      errors.push("year must be an integer between 0 and 9999");
    } else {
      data.year = body.year as number;
    }
  }

  if (has("isbn")) {
    if (body.isbn === null) {
      data.isbn = null;
    } else if (typeof body.isbn !== "string") {
      errors.push("isbn must be a string");
    } else {
      data.isbn = body.isbn;
    }
  }

  return { errors, data };
}

function parseId(raw: string): number | null {
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function createApp(db: Database): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const { errors, data } = validateBookInput(req.body ?? {}, { partial: false });
    if (errors.length > 0) {
      res.status(400).json({ error: "Validation failed", details: errors });
      return;
    }
    const stmt = db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const info = stmt.run(data.title!, data.author!, data.year ?? null, data.isbn ?? null);
    const book = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(info.lastInsertRowid) as Book;
    res.status(201).json(book);
  });

  app.get("/books", (req: Request, res: Response) => {
    const { author } = req.query;
    let books: Book[];
    if (author !== undefined) {
      if (typeof author !== "string") {
        res.status(400).json({ error: "author filter must be a string" });
        return;
      }
      books = db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(author) as Book[];
    } else {
      books = db.prepare("SELECT * FROM books ORDER BY id").all() as Book[];
    }
    res.status(200).json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | undefined;
    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | undefined;
    if (!existing) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    const { errors, data } = validateBookInput(req.body ?? {}, { partial: true });
    if (errors.length > 0) {
      res.status(400).json({ error: "Validation failed", details: errors });
      return;
    }
    const updated: Book = {
      id,
      title: data.title ?? existing.title,
      author: data.author ?? existing.author,
      year: data.year !== undefined ? data.year : existing.year,
      isbn: data.isbn !== undefined ? data.isbn : existing.isbn,
    };
    db.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?").run(
      updated.title,
      updated.author,
      updated.year,
      updated.isbn,
      id
    );
    res.status(200).json(updated);
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const info = db.prepare("DELETE FROM books WHERE id = ?").run(id);
    if (info.changes === 0) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(204).send();
  });

  return app;
}
