import { Router } from "express";
import type { Database as DB } from "better-sqlite3";
import { rowToBook, type Book } from "./db.js";
import {
  bookCreateSchema,
  bookUpdateSchema,
  normalizeCreate,
  normalizeUpdate,
  type BookCreate,
  type BookUpdate,
} from "./validation.js";

export interface BooksService {
  create(input: BookCreate): Book;
  list(filter?: { author?: string }): Book[];
  get(id: number): Book | null;
  update(id: number, input: BookUpdate): Book | null;
  remove(id: number): boolean;
}

export function createBooksService(db: DB): BooksService {
  const insert = db.prepare(
    `INSERT INTO books (title, author, year, isbn) VALUES (@title, @author, @year, @isbn)
     RETURNING *;`,
  );
  const selectAll = db.prepare(
    `SELECT * FROM books WHERE (@author IS NULL OR author = @author) ORDER BY id;`,
  );
  const selectOne = db.prepare(`SELECT * FROM books WHERE id = @id;`);
  const updateAll = db.prepare(
    `UPDATE books
       SET title = COALESCE(@title, title),
           author = COALESCE(@author, author),
           year = COALESCE(@year, year),
           isbn = COALESCE(@isbn, isbn),
           updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
     WHERE id = @id RETURNING *;`,
  );
  const deleteOne = db.prepare(`DELETE FROM books WHERE id = @id;`);

  return {
    create(input) {
      const norm = normalizeCreate(input);
      return rowToBook(insert.get(norm) as Record<string, unknown>);
    },
    list(filter) {
      const rows = selectAll.all({
        author: filter?.author ?? null,
      }) as Record<string, unknown>[];
      return rows.map(rowToBook);
    },
    get(id) {
      const row = selectOne.get({ id }) as Record<string, unknown> | undefined;
      return row ? rowToBook(row) : null;
    },
    update(id, input) {
      const norm = normalizeUpdate(input);
      const row = updateAll.get({
        id,
        title: norm.title ?? null,
        author: norm.author ?? null,
        year: norm.year ?? null,
        isbn: norm.isbn ?? null,
      }) as Record<string, unknown> | undefined;
      return row ? rowToBook(row) : null;
    },
    remove(id) {
      const res = deleteOne.run({ id });
      return res.changes > 0;
    },
  };
}

export function createBooksRouter(service: BooksService): Router {
  const router = Router();

  router.get("/health", (_req, res) => {
    res.status(200).json({ status: "ok" });
  });

  router.get("/books", (req, res) => {
    const author = req.query.author;
    const filter =
      typeof author === "string" && author.length > 0
        ? { author }
        : undefined;
    res.json(service.list(filter));
  });

  router.get("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const book = service.get(id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.json(book);
  });

  router.post("/books", (req, res) => {
    const parsed = bookCreateSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(422).json({
        error: "validation failed",
        issues: parsed.error.issues.map((i) => ({
          path: i.path.join("."),
          message: i.message,
        })),
      });
      return;
    }
    const book = service.create(parsed.data);
    res.status(201).json(book);
  });

  router.put("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const parsed = bookUpdateSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(422).json({
        error: "validation failed",
        issues: parsed.error.issues.map((i) => ({
          path: i.path.join("."),
          message: i.message,
        })),
      });
      return;
    }
    const book = service.update(id, parsed.data);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.json(book);
  });

  router.delete("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "id must be an integer" });
      return;
    }
    const ok = service.remove(id);
    if (!ok) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).send();
  });

  return router;
}
