import express from "express";
import type { Request, Response, NextFunction } from "express";
import { ZodError } from "zod";
import { getDb } from "./db.js";
import { bookSchema } from "./types.js";
import type { BookInput } from "./types.js";

export function createApp(): express.Application {
  const app = express();

  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "ok" });
  });

  app.get("/books", async (req: Request, res: Response, next: NextFunction) => {
    try {
      const db = getDb();
      const authorFilter = req.query.author;

      let books;
      if (typeof authorFilter === "string" && authorFilter.length > 0) {
        books = await db.all(
          "SELECT * FROM books WHERE author = ? ORDER BY id",
          authorFilter
        );
      } else {
        books = await db.all("SELECT * FROM books ORDER BY id");
      }

      res.json(books);
    } catch (err) {
      next(err);
    }
  });

  app.get("/books/:id", async (req: Request, res: Response, next: NextFunction) => {
    try {
      const db = getDb();
      const id = Number(req.params.id);

      if (Number.isNaN(id)) {
        res.status(400).json({ error: "Invalid book ID" });
        return;
      }

      const book = await db.get("SELECT * FROM books WHERE id = ?", id);

      if (!book) {
        res.status(404).json({ error: "Book not found" });
        return;
      }

      res.json(book);
    } catch (err) {
      next(err);
    }
  });

  app.post("/books", async (req: Request, res: Response, next: NextFunction) => {
    try {
      const input: BookInput = bookSchema.parse(req.body);
      const db = getDb();

      const result = await db.run(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        input.title,
        input.author,
        input.year ?? null,
        input.isbn ?? null
      );

      const book = await db.get("SELECT * FROM books WHERE id = ?", result.lastID);
      res.status(201).json(book);
    } catch (err) {
      next(err);
    }
  });

  app.put("/books/:id", async (req: Request, res: Response, next: NextFunction) => {
    try {
      const db = getDb();
      const id = Number(req.params.id);

      if (Number.isNaN(id)) {
        res.status(400).json({ error: "Invalid book ID" });
        return;
      }

      const existing = await db.get("SELECT * FROM books WHERE id = ?", id);
      if (!existing) {
        res.status(404).json({ error: "Book not found" });
        return;
      }

      const input: BookInput = bookSchema.parse(req.body);

      await db.run(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        input.title,
        input.author,
        input.year ?? null,
        input.isbn ?? null,
        id
      );

      const book = await db.get("SELECT * FROM books WHERE id = ?", id);
      res.json(book);
    } catch (err) {
      next(err);
    }
  });

  app.delete("/books/:id", async (req: Request, res: Response, next: NextFunction) => {
    try {
      const db = getDb();
      const id = Number(req.params.id);

      if (Number.isNaN(id)) {
        res.status(400).json({ error: "Invalid book ID" });
        return;
      }

      const existing = await db.get("SELECT * FROM books WHERE id = ?", id);
      if (!existing) {
        res.status(404).json({ error: "Book not found" });
        return;
      }

      await db.run("DELETE FROM books WHERE id = ?", id);
      res.status(204).send();
    } catch (err) {
      next(err);
    }
  });

  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: "Not found" });
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof ZodError) {
      const messages = err.issues.map((e) => `${e.path.join(".")}: ${e.message}`);
      res.status(400).json({ error: "Validation failed", details: messages });
      return;
    }

    console.error(err);
    res.status(500).json({ error: "Internal server error" });
  });

  return app;
}
