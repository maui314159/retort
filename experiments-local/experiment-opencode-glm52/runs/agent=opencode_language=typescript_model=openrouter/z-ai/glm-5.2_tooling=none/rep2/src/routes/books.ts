import { Router, type Request, type Response } from "express";
import type { Database as DBType } from "better-sqlite3";
import type { Book, NewBook } from "../db";
import { validateBook } from "../validation";

export function createBooksRouter(db: DBType): Router {
  const router = Router();

  const insertStmt = db.prepare<NewBook>(
    `INSERT INTO books (title, author, year, isbn) VALUES (@title, @author, @year, @isbn)`,
  );
  const getByIdStmt = db.prepare<number>(`SELECT * FROM books WHERE id = ?`);
  const deleteStmt = db.prepare<number>(`DELETE FROM books WHERE id = ?`);
  const listAllStmt = db.prepare(`SELECT * FROM books ORDER BY id ASC`);
  const listByAuthorStmt = db.prepare<string>(
    `SELECT * FROM books WHERE author = ? ORDER BY id ASC`,
  );
  const updateStmt = db.prepare<{
    id: number;
    title: string;
    author: string;
    year: number | null;
    isbn: string | null;
  }>(
    `UPDATE books SET title = @title, author = @author, year = @year, isbn = @isbn WHERE id = @id`,
  );

  router.post("/", (req: Request, res: Response) => {
    const validation = validateBook(req.body);
    if (!validation.ok) {
      res.status(400).json({ errors: validation.errors });
      return;
    }
    const v = validation.value;
    const info = insertStmt.run({
      title: v.title,
      author: v.author,
      year: v.year ?? null,
      isbn: v.isbn ?? null,
    });
    const book = getByIdStmt.get(Number(info.lastInsertRowid)) as Book;
    res.status(201).json(book);
  });

  router.get("/", (req: Request, res: Response) => {
    const author = req.query.author;
    let books: Book[];
    if (typeof author === "string" && author.length > 0) {
      books = listByAuthorStmt.all(author) as Book[];
    } else {
      books = listAllStmt.all() as Book[];
    }
    res.json(books);
  });

  router.get("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const book = getByIdStmt.get(id) as Book | undefined;
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.json(book);
  });

  router.put("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const existing = getByIdStmt.get(id) as Book | undefined;
    if (!existing) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    const validation = validateBook(req.body);
    if (!validation.ok) {
      res.status(400).json({ errors: validation.errors });
      return;
    }
    const v = validation.value;
    updateStmt.run({
      id,
      title: v.title,
      author: v.author,
      year: v.year ?? null,
      isbn: v.isbn ?? null,
    });
    const book = getByIdStmt.get(id) as Book;
    res.json(book);
  });

  router.delete("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const existing = getByIdStmt.get(id) as Book | undefined;
    if (!existing) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    deleteStmt.run(id);
    res.status(204).send();
  });

  return router;
}
