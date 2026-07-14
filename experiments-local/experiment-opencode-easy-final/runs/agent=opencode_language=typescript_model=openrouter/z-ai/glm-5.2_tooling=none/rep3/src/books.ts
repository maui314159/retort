import { Router, type Request, type Response } from "express";
import { getDb, type BookRow } from "./db.js";
import {
  createBookSchema,
  updateBookSchema,
  formatZodError,
} from "./validation.js";

export const booksRouter = Router();

booksRouter.post("/", (req: Request, res: Response) => {
  const parsed = createBookSchema.safeParse(req.body);
  if (!parsed.success) {
    const fmt = formatZodError(parsed.error);
    res.status(400).json(fmt);
    return;
  }
  const db = getDb();
  const now = new Date().toISOString();
  const stmt = db.prepare(
    `INSERT INTO books (title, author, year, isbn, created_at, updated_at)
     VALUES (@title, @author, @year, @isbn, @now, @now)`
  );
  const info = stmt.run({
    title: parsed.data.title,
    author: parsed.data.author,
    year: parsed.data.year ?? null,
    isbn: parsed.data.isbn ?? null,
    now,
  });
  const book = db
    .prepare<[number], BookRow>("SELECT * FROM books WHERE id = ?")
    .get(info.lastInsertRowid as number) as BookRow;
  res.status(201).json(book);
});

booksRouter.get("/", (req: Request, res: Response) => {
  const db = getDb();
  const author = req.query.author as string | undefined;
  let rows: BookRow[];
  if (author && author.length > 0) {
    rows = db
      .prepare("SELECT * FROM books WHERE author = ? ORDER BY id ASC")
      .all(author) as BookRow[];
  } else {
    rows = db.prepare("SELECT * FROM books ORDER BY id ASC").all() as BookRow[];
  }
  res.status(200).json(rows);
});

booksRouter.get("/:id", (req: Request, res: Response) => {
  const id = Number.parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ message: "Invalid id" });
    return;
  }
  const db = getDb();
  const row = db
    .prepare<[number], BookRow>("SELECT * FROM books WHERE id = ?")
    .get(id) as BookRow | undefined;
  if (!row) {
    res.status(404).json({ message: "Book not found" });
    return;
  }
  res.status(200).json(row);
});

booksRouter.put("/:id", (req: Request, res: Response) => {
  const id = Number.parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ message: "Invalid id" });
    return;
  }
  const parsed = updateBookSchema.safeParse(req.body);
  if (!parsed.success) {
    const fmt = formatZodError(parsed.error);
    res.status(400).json(fmt);
    return;
  }
  const db = getDb();
  const existing = db
    .prepare<[number], BookRow>("SELECT * FROM books WHERE id = ?")
    .get(id) as BookRow | undefined;
  if (!existing) {
    res.status(404).json({ message: "Book not found" });
    return;
  }
  const next = {
    title: parsed.data.title ?? existing.title,
    author: parsed.data.author ?? existing.author,
    year: parsed.data.year ?? existing.year,
    isbn: parsed.data.isbn ?? existing.isbn,
  };
  const now = new Date().toISOString();
  db.prepare(
    `UPDATE books SET title = @title, author = @author, year = @year,
        isbn = @isbn, updated_at = @now WHERE id = @id`
  ).run({ ...next, now, id });
  const updated = db
    .prepare<[number], BookRow>("SELECT * FROM books WHERE id = ?")
    .get(id) as BookRow;
  res.status(200).json(updated);
});

booksRouter.delete("/:id", (req: Request, res: Response) => {
  const id = Number.parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ message: "Invalid id" });
    return;
  }
  const db = getDb();
  const existing = db
    .prepare<[number], BookRow>("SELECT * FROM books WHERE id = ?")
    .get(id) as BookRow | undefined;
  if (!existing) {
    res.status(404).json({ message: "Book not found" });
    return;
  }
  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.status(204).send();
});
