import { Router, Request, Response } from 'express';
import { BookDatabase } from '../db/database';
import { NewBook, UpdateBook } from '../models/book';

function hasRequiredStringFields(
  body: unknown,
  fields: string[]
): body is Record<string, unknown> {
  if (typeof body !== 'object' || body === null) return false;
  const record = body as Record<string, unknown>;
  return fields.every((f) => {
    const val = record[f];
    return typeof val === 'string' && val.trim().length > 0;
  });
}

function parseId(paramId: string): number | null {
  const id = Number(paramId);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function createBookRouter(db: BookDatabase): Router {
  const router = Router();

  router.post('/books', (req: Request, res: Response): void => {
    const body: unknown = req.body;
    if (!hasRequiredStringFields(body, ['title', 'author'])) {
      res.status(400).json({ error: 'title and author are required and must be non-empty strings' });
      return;
    }
    const record = body as Record<string, unknown>;
    const newBook: NewBook = {
      title: String(record['title']),
      author: String(record['author']),
      year: record['year'] !== undefined ? Number(record['year']) : undefined,
      isbn: record['isbn'] !== undefined ? String(record['isbn']) : undefined,
    };
    const created = db.createBook(newBook);
    res.status(201).json(created);
  });

  router.get('/books', (req: Request, res: Response): void => {
    const authorFilter =
      typeof req.query['author'] === 'string' ? req.query['author'] : undefined;
    const books = db.getAllBooks(authorFilter);
    res.json(books);
  });

  router.get('/books/:id', (req: Request, res: Response): void => {
    const id = parseId(req.params['id'] as string);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const book = db.getBookById(id);
    if (!book) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.json(book);
  });

  router.put('/books/:id', (req: Request, res: Response): void => {
    const id = parseId(req.params['id'] as string);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const body: unknown = req.body;
    if (typeof body !== 'object' || body === null) {
      res.status(400).json({ error: 'request body must be a JSON object' });
      return;
    }
    const record = body as Record<string, unknown>;
    const updates: UpdateBook = {};
    if (record['title'] !== undefined) {
      if (typeof record['title'] !== 'string' || (record['title'] as string).trim().length === 0) {
        res.status(400).json({ error: 'title must be a non-empty string' });
        return;
      }
      updates.title = record['title'] as string;
    }
    if (record['author'] !== undefined) {
      if (typeof record['author'] !== 'string' || (record['author'] as string).trim().length === 0) {
        res.status(400).json({ error: 'author must be a non-empty string' });
        return;
      }
      updates.author = record['author'] as string;
    }
    if (record['year'] !== undefined) updates.year = Number(record['year']);
    if (record['isbn'] !== undefined) updates.isbn = String(record['isbn']);
    const updated = db.updateBook(id, updates);
    if (!updated) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.json(updated);
  });

  router.delete('/books/:id', (req: Request, res: Response): void => {
    const id = parseId(req.params['id'] as string);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const deleted = db.deleteBook(id);
    if (!deleted) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.status(204).send();
  });

  return router;
}
