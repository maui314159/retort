import { Router, Request, Response } from "express";
import { currentDb } from "../db";
import { bookSchema, bookUpdateSchema } from "../validation";

const router = Router();

// GET /books — list all books, optionally filtered by ?author=
router.get("/", (req: Request, res: Response) => {
  const db = currentDb();
  const { author } = req.query;

  let books;
  if (author && typeof author === "string" && author.trim().length > 0) {
    books = db
      .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
      .all(author);
  } else {
    books = db.prepare("SELECT * FROM books ORDER BY id").all();
  }

  res.status(200).json(books);
});

// GET /books/:id — get a single book by ID
router.get("/:id", (req: Request, res: Response) => {
  const db = currentDb();
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: "Invalid book id" });
  }

  const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id);

  if (!book) {
    return res.status(404).json({ error: "Book not found" });
  }

  return res.status(200).json(book);
});

// POST /books — create a new book
router.post("/", (req: Request, res: Response) => {
  const db = currentDb();
  const result = bookSchema.safeParse(req.body);

  if (!result.success) {
    return res.status(400).json({
      error: "Validation failed",
      details: result.error.flatten().fieldErrors,
    });
  }

  const { title, author, year, isbn } = result.data;

  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const info = stmt.run(title, author, year ?? null, isbn ?? null);

  const createdBook = db
    .prepare("SELECT * FROM books WHERE id = ?")
    .get(info.lastInsertRowid);

  return res.status(201).json(createdBook);
});

// PUT /books/:id — update a book
router.put("/:id", (req: Request, res: Response) => {
  const db = currentDb();
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: "Invalid book id" });
  }

  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);

  if (!existing) {
    return res.status(404).json({ error: "Book not found" });
  }

  const result = bookUpdateSchema.safeParse(req.body);

  if (!result.success) {
    return res.status(400).json({
      error: "Validation failed",
      details: result.error.flatten().fieldErrors,
    });
  }

  const { title, author, year, isbn } = result.data;

  // Merge with existing values so partial updates work correctly
  const merged = {
    title: title ?? (existing as any).title,
    author: author ?? (existing as any).author,
    year: year !== undefined ? year : (existing as any).year,
    isbn: isbn !== undefined ? isbn : (existing as any).isbn,
  };

  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(merged.title, merged.author, merged.year, merged.isbn, id);

  const updatedBook = db.prepare("SELECT * FROM books WHERE id = ?").get(id);

  return res.status(200).json(updatedBook);
});

// DELETE /books/:id — delete a book
router.delete("/:id", (req: Request, res: Response) => {
  const db = currentDb();
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: "Invalid book id" });
  }

  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);

  if (!existing) {
    return res.status(404).json({ error: "Book not found" });
  }

  db.prepare("DELETE FROM books WHERE id = ?").run(id);

  return res.status(204).send();
});

export default router;
