import express from "express";
import { createDb, type Book, type BookInput } from "./db.js";
import type Database from "better-sqlite3";
export type App = express.Express;

export function createApp(db?: Database.Database): App {
  const app = express();
  const database = db ?? createDb();

  app.use(express.json());

  // Health check
  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  // Create a book
  app.post("/books", (req, res) => {
    const { title, author, year, isbn }: BookInput = req.body;

    if (!title || !author) {
      res.status(400).json({
        error: "title and author are required",
      });
      return;
    }

    const stmt = database.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const result = stmt.run(title, author, year ?? null, isbn ?? null);

    const book = database
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(result.lastInsertRowid) as Book;

    res.status(201).json(book);
  });

  // List books (with optional author filter)
  app.get("/books", (req, res) => {
    const author = req.query.author as string | undefined;

    let books: Book[];
    if (author) {
      books = database
        .prepare("SELECT * FROM books WHERE author = ?")
        .all(author) as Book[];
    } else {
      books = database.prepare("SELECT * FROM books").all() as Book[];
    }

    res.json(books);
  });

  // Get a single book
  app.get("/books/:id", (req, res) => {
    const book = database
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(req.params.id) as Book | undefined;

    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }

    res.json(book);
  });

  // Update a book
  app.put("/books/:id", (req, res) => {
    const existing = database
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(req.params.id) as Book | undefined;

    if (!existing) {
      res.status(404).json({ error: "Book not found" });
      return;
    }

    const { title, author, year, isbn }: BookInput = req.body;

    if (!title || !author) {
      res.status(400).json({
        error: "title and author are required",
      });
      return;
    }

    database.prepare(
      "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    ).run(title, author, year ?? null, isbn ?? null, req.params.id);

    const updated = database
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(req.params.id) as Book;

    res.json(updated);
  });

  // Delete a book
  app.delete("/books/:id", (req, res) => {
    const existing = database
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(req.params.id) as Book | undefined;

    if (!existing) {
      res.status(404).json({ error: "Book not found" });
      return;
    }

    database.prepare("DELETE FROM books WHERE id = ?").run(req.params.id);
    res.status(204).send();
  });

  return app;
}
