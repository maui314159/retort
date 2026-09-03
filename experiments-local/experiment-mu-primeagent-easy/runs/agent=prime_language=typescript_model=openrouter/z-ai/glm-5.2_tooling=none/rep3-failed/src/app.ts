import express, { Request, Response, NextFunction } from "express";
import { BookStore } from "./db";
import { validateBookInput } from "./validation";
import { Book, BookInput, ErrorResponse } from "./types";

/**
 * Build the Express application.
 *
 * The `BookStore` is injected so tests can supply an in-memory store. When
 * omitted, a store backed by the file configured via `BOOKS_DB_PATH`
 * (default `./books.db`) is created.
 */
export function createApp(store?: BookStore): express.Express {
  const app = express();
  const books = store ?? new BookStore(process.env.BOOKS_DB_PATH ?? "./books.db");

  app.locals.books = books;

  // JSON body parser. Treat malformed JSON as a 400 instead of crashing.
  app.use(
    express.json({
      type: ["application/json", "application/json; charset=utf-8"],
    })
  );

  // Coerce body-parser 400 errors into our uniform error shape.
  app.use((err: unknown, _req: Request, res: Response, next: NextFunction) => {
    if (err instanceof SyntaxError && "status" in err && (err as { status?: number }).status === 400) {
      const body: ErrorResponse = { error: "Invalid JSON body" };
      res.status(400).json(body);
      return;
    }
    next(err);
  });

  // --- Health check ---
  app.get("/health", (_req: Request, res: Response): void => {
    res.status(200).json({ status: "ok" });
  });

  // --- Create a book ---
  app.post("/books", (req: Request, res: Response<Book | ErrorResponse>): void => {
    const result = validateBookInput(req.body as BookInput);
    if (!result.ok) {
      res.status(400).json({ error: "Validation failed", details: result.details });
      return;
    }
    const book = books.create(result.value);
    res.status(201).json(book);
  });

  // --- List books (with optional ?author= filter) ---
  app.get("/books", (req: Request, res: Response<Book[] | ErrorResponse>): void => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    const all = books.list(author);
    res.status(200).json(all);
  });

  // --- Get a single book by id ---
  app.get("/books/:id", (req: Request, res: Response<Book | ErrorResponse>): void => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const book = books.get(id);
    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(book);
  });

  // --- Update a book (full replacement) ---
  app.put("/books/:id", (req: Request, res: Response<Book | ErrorResponse>): void => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const result = validateBookInput(req.body as BookInput);
    if (!result.ok) {
      res.status(400).json({ error: "Validation failed", details: result.details });
      return;
    }
    const updated = books.update(id, result.value);
    if (!updated) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(updated);
  });

  // --- Delete a book ---
  app.delete("/books/:id", (req: Request, res: Response<ErrorResponse>): void => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const deleted = books.delete(id);
    if (!deleted) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(204).send();
  });

  // --- 404 handler for unknown routes ---
  app.use((_req: Request, res: Response<ErrorResponse>): void => {
    res.status(404).json({ error: "Not found" });
  });

  return app;
}
