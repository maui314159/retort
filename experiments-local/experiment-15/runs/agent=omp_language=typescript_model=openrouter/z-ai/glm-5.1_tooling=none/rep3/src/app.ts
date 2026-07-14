import express, { Request, Response } from 'express';
import { createDb, insertBook, getAllBooks, getBookById, updateBook, deleteBook, BookInput } from './db';
import Database from 'better-sqlite3';

export type AppInstance = { app: express.Express; db: Database.Database };

export function createApp(db?: Database.Database): AppInstance {
  const app = express();
  const database = db ?? createDb();

  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  // Create a book
  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body;

    if (!title || !author) {
      res.status(400).json({ error: 'title and author are required' });
      return;
    }

    const book = insertBook(database, { title, author, year, isbn });
    res.status(201).json(book);
  });

  // List books
  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    const books = getAllBooks(database, author);
    res.json(books);
  });

  // Get a single book
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const book = getBookById(database, id);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    res.json(book);
  });

  // Update a book
  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const { title, author, year, isbn } = req.body;

    if (title !== undefined && !title) {
      res.status(400).json({ error: 'title must not be empty' });
      return;
    }
    if (author !== undefined && !author) {
      res.status(400).json({ error: 'author must not be empty' });
      return;
    }

    const book = updateBook(database, id, { title, author, year, isbn });
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    res.json(book);
  });

  // Delete a book
  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const deleted = deleteBook(database, id);
    if (!deleted) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    res.status(204).send();
  });

  return { app, db: database };
}
