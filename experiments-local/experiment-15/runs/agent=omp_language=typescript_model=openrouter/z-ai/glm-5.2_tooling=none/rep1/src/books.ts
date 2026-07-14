import { Router, type Request, type Response } from "express";
import type { Database as SqliteDb } from "better-sqlite3";
import { validateCreate, validateUpdate, type ValidationError } from "./validation.js";

export interface BookDto {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function rowToDto(row: {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}): BookDto {
  return { id: row.id, title: row.title, author: row.author, year: row.year, isbn: row.isbn };
}

function sendValidationErrors(res: Response, errors: ValidationError[]): void {
  res.status(400).json({ error: "validation_failed", details: errors });
}

export function createBooksRouter(db: SqliteDb): Router {
  const router = Router();

  const insertStmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
  );
  const getByIdStmt = db.prepare("SELECT * FROM books WHERE id = ?");
  const deleteStmt = db.prepare("DELETE FROM books WHERE id = ?");

  // POST /books — create
  router.post("/", (req: Request, res: Response) => {
    const result = validateCreate(req.body ?? {});
    if (!result.ok) {
      sendValidationErrors(res, result.errors);
      return;
    }
    const { title, author, year, isbn } = result.book;
    const info = insertStmt.run(title, author, year, isbn);
    const book = getByIdStmt.get(info.lastInsertRowid);
    res.status(201).json(rowToDto(book as Parameters<typeof rowToDto>[0]));
  });

  // GET /books — list, optional ?author= filter
  router.get("/", (req: Request, res: Response) => {
    const author = req.query.author;
    let rows: Parameters<typeof rowToDto>[0][];
    if (typeof author === "string" && author.trim().length > 0) {
      rows = db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(author.trim()) as Parameters<typeof rowToDto>[0][];
    } else {
      rows = db.prepare("SELECT * FROM books ORDER BY id").all() as Parameters<typeof rowToDto>[0][];
    }
    res.json(rows.map(rowToDto));
  });

  // GET /books/{id}
  router.get("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "invalid_id", message: "id must be an integer" });
      return;
    }
    const row = getByIdStmt.get(id) as Parameters<typeof rowToDto>[0] | undefined;
    if (!row) {
      res.status(404).json({ error: "not_found", message: `book ${id} not found` });
      return;
    }
    res.json(rowToDto(row));
  });

  // PUT /books/{id} — update
  router.put("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "invalid_id", message: "id must be an integer" });
      return;
    }
    const existing = getByIdStmt.get(id) as Parameters<typeof rowToDto>[0] | undefined;
    if (!existing) {
      res.status(404).json({ error: "not_found", message: `book ${id} not found` });
      return;
    }
    const result = validateUpdate(req.body ?? {});
    if (!result.ok) {
      sendValidationErrors(res, result.errors);
      return;
    }
    const merged: BookDto = {
      id: existing.id,
      title: result.book.title ?? existing.title,
      author: result.book.author ?? existing.author,
      year: result.book.year ?? existing.year,
      isbn: result.book.isbn ?? existing.isbn,
    };
    db.prepare(
      "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
    ).run(merged.title, merged.author, merged.year, merged.isbn, id);
    res.json(merged);
  });

  // DELETE /books/{id}
  router.delete("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "invalid_id", message: "id must be an integer" });
      return;
    }
    const info = deleteStmt.run(id);
    if (info.changes === 0) {
      res.status(404).json({ error: "not_found", message: `book ${id} not found` });
      return;
    }
    res.status(204).send();
  });

  return router;
}
