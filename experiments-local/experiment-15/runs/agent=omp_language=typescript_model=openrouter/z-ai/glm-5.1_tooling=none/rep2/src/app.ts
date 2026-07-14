import express, { Request, Response } from 'express';
import { Database } from 'better-sqlite3';
import { createDatabase, insertBook, selectBookById, selectBooks, updateBook, deleteBook } from './database';

interface BookPayload {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

function parseBody(body: unknown): BookPayload {
  if (body && typeof body === 'object') {
    const src = body as Record<string, unknown>;
    return {
      title: typeof src.title === 'string' ? src.title : undefined,
      author: typeof src.author === 'string' ? src.author : undefined,
      year: typeof src.year === 'number' ? src.year : undefined,
      isbn: typeof src.isbn === 'string' ? src.isbn : undefined,
    };
  }
  return {};
}

export function createApp(db?: Database): { app: express.Express; database: Database } {
  const app = express();
  const database = db ?? createDatabase();

  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  // Create a book
  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = parseBody(req.body);

    if (!title || !author) {
      res.status(400).json({
        error: 'Validation failed',
        details: 'title and author are required',
      });
      return;
    }

    const book = insertBook(database, { title, author, year, isbn });
    res.status(201).json(book);
  });

  // List books (with optional author filter)
  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    const books = selectBooks(database, author);
    res.json(books);
  });

  // Get a single book
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const book = selectBookById(database, id);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    res.json(book);
  });

  // Update a book
  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const { title, author, year, isbn } = parseBody(req.body);

    if (title !== undefined && !title) {
      res.status(400).json({ error: 'Validation failed', details: 'title must not be empty' });
      return;
    }
    if (author !== undefined && !author) {
      res.status(400).json({ error: 'Validation failed', details: 'author must not be empty' });
      return;
    }

    const updated = updateBook(database, id, { title, author, year, isbn });
    if (!updated) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    res.json(updated);
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

  return { app, database };
}
