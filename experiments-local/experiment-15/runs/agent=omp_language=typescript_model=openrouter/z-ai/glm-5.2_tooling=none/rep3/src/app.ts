import { Hono } from "hono";
import type { BooksDb } from "./db.js";
import {
  createBook,
  deleteBook,
  getBook,
  listBooks,
  updateBook,
} from "./books.js";
import { validateBookInput, validateBookUpdate } from "./validate.js";

/** Build the Hono application wired to a given database. Tests pass an in-memory db. */
export function createApp(db: BooksDb): Hono {
  const app = new Hono();

  app.get("/health", (c) => c.json({ status: "ok" }));

  app.post("/books", async (c) => {
    const body = await c.req.json().catch(() => null);
    const result = validateBookInput(body);
    if (!result.ok) {
      return c.json({ errors: result.errors }, 400);
    }
    const book = createBook(db, result.value);
    return c.json(book, 201);
  });

  app.get("/books", (c) => {
    const author = c.req.query("author");
    const books = listBooks(db, author);
    return c.json(books);
  });

  app.get("/books/:id", (c) => {
    const id = Number(c.req.param("id"));
    if (!Number.isInteger(id) || id <= 0) {
      return c.json({ errors: { id: "id must be a positive integer" } }, 400);
    }
    const book = getBook(db, id);
    if (!book) {
      return c.json({ errors: { id: `no book with id ${id}` } }, 404);
    }
    return c.json(book);
  });

  app.put("/books/:id", async (c) => {
    const id = Number(c.req.param("id"));
    if (!Number.isInteger(id) || id <= 0) {
      return c.json({ errors: { id: "id must be a positive integer" } }, 400);
    }
    const body = await c.req.json().catch(() => null);
    const result = validateBookUpdate(body);
    if (!result.ok) {
      return c.json({ errors: result.errors }, 400);
    }
    const updated = updateBook(db, id, result.value);
    if (!updated) {
      return c.json({ errors: { id: `no book with id ${id}` } }, 404);
    }
    return c.json(updated);
  });

  app.delete("/books/:id", (c) => {
    const id = Number(c.req.param("id"));
    if (!Number.isInteger(id) || id <= 0) {
      return c.json({ errors: { id: "id must be a positive integer" } }, 400);
    }
    const removed = deleteBook(db, id);
    if (!removed) {
      return c.json({ errors: { id: `no book with id ${id}` } }, 404);
    }
    return c.body(null, 204);
  });

  return app;
}
