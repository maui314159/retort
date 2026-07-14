import { Router } from "express";
import type Database from "better-sqlite3";
import {
  createBook,
  deleteBook,
  getBook,
  listBooks,
  updateBook,
} from "../db.js";
import { formatZodError, parseCreate, parseUpdate } from "../validation.js";
import type { ApiError } from "../types.js";

export function buildBooksRouter(db: Database.Database): Router {
  const router = Router();

  router.get("/", (req, res) => {
    const author = req.query.author;
    const authorFilter = typeof author === "string" ? author : undefined;
    const books = listBooks(db, authorFilter);
    res.json(books);
  });

  router.post("/", (req, res) => {
    let payload;
    try {
      payload = parseCreate(req.body);
    } catch (err) {
      const body: ApiError = formatZodError(err as never);
      return res.status(400).json(body);
    }
    const book = createBook(db, payload);
    res.status(201).json(book);
  });

  router.get("/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid_id" });
    const book = getBook(db, id);
    if (!book) return res.status(404).json({ error: "not_found" });
    res.json(book);
  });

  router.put("/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid_id" });
    let payload;
    try {
      payload = parseUpdate(req.body);
    } catch (err) {
      const body: ApiError = formatZodError(err as never);
      return res.status(400).json(body);
    }
    const updated = updateBook(db, id, payload);
    if (!updated) return res.status(404).json({ error: "not_found" });
    res.json(updated);
  });

  router.delete("/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid_id" });
    const ok = deleteBook(db, id);
    if (!ok) return res.status(404).json({ error: "not_found" });
    res.status(204).send();
  });

  return router;
}

function parseId(raw: string | undefined): number | null {
  if (!raw) return null;
  const n = Number(raw);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}
