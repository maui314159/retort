import express, { type Application, type Request, type Response } from "express";
import {
  createBook,
  deleteBook,
  getBook,
  initDb,
  listBooks,
  updateBook,
  type BookInput,
  type DB,
} from "./db.js";

export interface AppOptions {
  dbPath?: string;
  db?: DB;
}

export function createApp(options: AppOptions = {}): Application {
  const app = express();
  app.use(express.json());

  const db = options.db ?? initDb(options.dbPath ?? ":memory:");

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const input: BookInput = {
      title: req.body?.title,
      author: req.body?.author,
      year: req.body?.year,
      isbn: req.body?.isbn,
    };
    try {
      const book = createBook(db, input);
      res.status(201).json(book);
    } catch (err) {
      handleError(err, res);
    }
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    const books = listBooks(db, author);
    res.status(200).json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const book = getBook(db, id);
    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const input: Partial<BookInput> = {
      title: req.body?.title,
      author: req.body?.author,
      year: req.body?.year,
      isbn: req.body?.isbn,
    };
    try {
      const book = updateBook(db, id, input);
      res.status(200).json(book);
    } catch (err) {
      handleError(err, res);
    }
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const deleted = deleteBook(db, id);
    if (!deleted) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(204).send();
  });

  return app;
}

function handleError(err: unknown, res: Response): void {
  const e = err as Error & { status?: number; errors?: unknown };
  if (e && typeof e.status === "number") {
    res.status(e.status).json({ error: e.message, errors: e.errors });
    return;
  }
  res.status(500).json({ error: "Internal server error" });
}

export function closeDb(app: Application): void {
  const db = (app as unknown as { locals?: { db?: DB } }).locals?.db;
  if (db) db.close();
}

const isMain = process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href;
if (isMain) {
  const port = Number(process.env.PORT ?? 3000);
  const app = createApp({ dbPath: process.env.DB_PATH ?? "books.db" });
  app.listen(port, () => {
    console.log(`Book collection API listening on port ${port}`);
  });
}
