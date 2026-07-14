import { Router, type Request, type Response } from "express";
import type { Database as DBType } from "better-sqlite3";
import { bookCreateSchema, bookUpdateSchema } from "./validation.js";
import type { Book } from "./db.js";

export function createRouter(db: DBType): Router {
  const router = Router();

  const insertStmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const selectAllStmt = db.prepare("SELECT * FROM books ORDER BY id");
  const selectByAuthorStmt = db.prepare(
    "SELECT * FROM books WHERE author = ? ORDER BY id"
  );
  const selectByIdStmt = db.prepare("SELECT * FROM books WHERE id = ?");
  const updateStmt = db.prepare(
    `UPDATE books SET
       title = COALESCE(@title, title),
       author = COALESCE(@author, author),
       year = COALESCE(@year, year),
       isbn = COALESCE(@isbn, isbn)
     WHERE id = @id`
  );
  const deleteStmt = db.prepare("DELETE FROM books WHERE id = ?");

  // POST /books
  router.post("/", (req: Request, res: Response) => {
    const parsed = bookCreateSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        error: "Validation failed",
        details: parsed.error.flatten().fieldErrors,
      });
    }
    const { title, author, year = null, isbn = null } = parsed.data;
    const info = insertStmt.run(title, author, year, isbn);
    const created = selectByIdStmt.get(info.lastInsertRowid) as Book;
    return res.status(201).json(created);
  });

  // GET /books
  router.get("/", (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    const rows =
      author && author.length > 0
        ? (selectByAuthorStmt.all(author) as Book[])
        : (selectAllStmt.all() as Book[]);
    return res.json(rows);
  });

  // GET /books/{id}
  router.get("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: "Invalid id" });
    }
    const book = selectByIdStmt.get(id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: "Book not found" });
    }
    return res.json(book);
  });

  // PUT /books/{id}
  router.put("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: "Invalid id" });
    }
    const existing = selectByIdStmt.get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: "Book not found" });
    }
    const parsed = bookUpdateSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        error: "Validation failed",
        details: parsed.error.flatten().fieldErrors,
      });
    }
    updateStmt.run({
      id,
      title: parsed.data.title ?? null,
      author: parsed.data.author ?? null,
      year: parsed.data.year ?? null,
      isbn: parsed.data.isbn ?? null,
    });
    const updated = selectByIdStmt.get(id) as Book;
    return res.json(updated);
  });

  // DELETE /books/{id}
  router.delete("/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: "Invalid id" });
    }
    const info = deleteStmt.run(id);
    if (info.changes === 0) {
      return res.status(404).json({ error: "Book not found" });
    }
    return res.status(204).send();
  });

  return router;
}
