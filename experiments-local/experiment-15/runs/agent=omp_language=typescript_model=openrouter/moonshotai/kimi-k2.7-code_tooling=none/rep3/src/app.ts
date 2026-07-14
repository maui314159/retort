import express, { Request, Response, NextFunction, Express } from 'express';
import { initDatabase, createBook, listBooks, getBookById, updateBook, deleteBook } from './db';
import { validateCreateBookInput, validateUpdateBookInput } from './validation';
import { ApiError, Book } from './types';

export function createApp(databasePath?: string): Express {
  const app = express();
  app.use(express.json());

  initDatabase(databasePath);

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response<Book | ApiError>) => {
    const validation = validateCreateBookInput(req.body);
    if (!validation.valid) {
      res.status(400).json(validation.error);
      return;
    }

    const book = createBook(validation.data);
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response<Book[] | ApiError>) => {
    const authorFilter = typeof req.query.author === 'string' ? req.query.author : undefined;
    const books = listBooks(authorFilter);
    res.status(200).json(books);
  });

  app.get('/books/:id', (req: Request, res: Response<Book | ApiError>) => {
    const id = parseInt(req.params.id, 10);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: 'id must be an integer' });
      return;
    }

    const book = getBookById(id);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response<Book | ApiError>) => {
    const id = parseInt(req.params.id, 10);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: 'id must be an integer' });
      return;
    }

    const validation = validateUpdateBookInput(req.body);
    if (!validation.valid) {
      res.status(400).json(validation.error);
      return;
    }

    const book = updateBook(id, validation.data);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(200).json(book);
  });

  app.delete('/books/:id', (req: Request, res: Response<void | ApiError>) => {
    const id = parseInt(req.params.id, 10);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: 'id must be an integer' });
      return;
    }

    const deleted = deleteBook(id);
    if (!deleted) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(204).send();
  });

  app.use((_req: Request, res: Response<ApiError>) => {
    res.status(404).json({ error: 'Not found' });
  });

  app.use((err: Error, _req: Request, res: Response<ApiError>, _next: NextFunction) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
