import express, { type Request, type Response, type Application } from "express";
import type { Database as DB } from "better-sqlite3";
import {
  insertBook,
  getBook,
  listBooks,
  updateBook,
  deleteBook,
  type BookInput,
} from "./db.js";

export function createApp(db: DB): Application {
  const app = express();
  app.use(express.json());

  function validate(input: BookInput): string | null {
    if (
      input.title === undefined ||
      input.title === null ||
      String(input.title).trim() === ""
    ) {
      return "title is required";
    }
    if (
      input.author === undefined ||
      input.author === null ||
      String(input.author).trim() === ""
    ) {
      return "author is required";
    }
    if (
      input.year !== undefined &&
      input.year !== null &&
      (typeof input.year !== "number" ||
        !Number.isFinite(input.year) ||
        input.year < 0 ||
        !Number.isInteger(input.year))
    ) {
      return "year must be a non-negative integer";
    }
    if (
      input.isbn !== undefined &&
      input.isbn !== null &&
      typeof input.isbn !== "string"
    ) {
      return "isbn must be a string";
    }
    return null;
  }

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const input: BookInput = req.body ?? {};
    const err = validate(input);
    if (err) {
      res.status(400).json({ error: err });
      return;
    }
    const book = insertBook(db, input);
    res.status(201).json(book);
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    res.status(200).json(listBooks(db, author));
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isFinite(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    const book = getBook(db, id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isFinite(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    const input: BookInput = req.body ?? {};
    const err = validate(input);
    if (err) {
      res.status(400).json({ error: err });
      return;
    }
    const book = updateBook(db, id, input);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isFinite(id)) {
      res.status(400).json({ error: "invalid id" });
      return;
    }
    const ok = deleteBook(db, id);
    if (!ok) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).send();
  });

  return app;
}
