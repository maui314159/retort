import { Router, type Request, type Response } from "express";
import { getDb, type Book, type NewBook } from "../db";
import { validateBook } from "../validation";

export const booksRouter = Router();

booksRouter.get("/", (req: Request, res: Response) => {
  const db = getDb();
  const author = req.query.author;
  let rows: Book[];
  if (typeof author === "string" && author.trim() !== "") {
    rows = db
      .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
      .all(author) as Book[];
  } else {
    rows = db.prepare("SELECT * FROM books ORDER BY id").all() as Book[];
  }
  res.json(rows);
});

booksRouter.get("/:id", (req: Request, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    res.status(400).json({ error: "id must be an integer" });
    return;
  }
  const db = getDb();
  const row = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
    | Book
    | undefined;
  if (!row) {
    res.status(404).json({ error: "book not found" });
    return;
  }
  res.json(row);
});

booksRouter.post("/", (req: Request, res: Response) => {
  const result = validateBook(req.body);
  if (!result.ok) {
    res.status(400).json({ errors: result.errors });
    return;
  }
  const db = getDb();
  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const info = stmt.run(
    result.value.title,
    result.value.author,
    result.value.year,
    result.value.isbn
  );
  const created = db
    .prepare("SELECT * FROM books WHERE id = ?")
    .get(info.lastInsertRowid) as Book;
  res.status(201).json(created);
});

booksRouter.put("/:id", (req: Request, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    res.status(400).json({ error: "id must be an integer" });
    return;
  }
  const result = validateBook(req.body);
  if (!result.ok) {
    res.status(400).json({ errors: result.errors });
    return;
  }
  const db = getDb();
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
    | Book
    | undefined;
  if (!existing) {
    res.status(404).json({ error: "book not found" });
    return;
  }
  const update: NewBook = result.value;
  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(update.title, update.author, update.year, update.isbn, id);
  const updated = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book;
  res.json(updated);
});

booksRouter.delete("/:id", (req: Request, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    res.status(400).json({ error: "id must be an integer" });
    return;
  }
  const db = getDb();
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
    | Book
    | undefined;
  if (!existing) {
    res.status(404).json({ error: "book not found" });
    return;
  }
  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  res.status(204).send();
});
