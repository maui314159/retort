import express, { type Application, type Request, type Response } from 'express';
import { BookStore, type BookInput, type BookUpdate } from './db';

export interface AppOptions {
  dbPath?: string;
}

export function createApp(options: AppOptions = {}): { app: Application; store: BookStore } {
  const store = new BookStore(options.dbPath ?? ':memory:');

  const app: Application = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const input = req.body as Partial<BookInput>;
    const validationError = validateCreate(input);
    if (validationError) {
      res.status(400).json({ error: validationError });
      return;
    }
    const book = store.create({
      title: input.title as string,
      author: input.author as string,
      year: typeof input.year === 'number' ? input.year : null,
      isbn: typeof input.isbn === 'string' ? input.isbn : null,
    });
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    res.status(200).json(store.list(author));
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const book = store.getById(id);
    if (!book) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const input = req.body as Partial<BookUpdate>;
    const validationError = validateUpdate(input);
    if (validationError) {
      res.status(400).json({ error: validationError });
      return;
    }
    const updated = store.update(id, input);
    if (!updated) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.status(200).json(updated);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const deleted = store.delete(id);
    if (!deleted) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.status(204).send();
  });

  return { app, store };
}

function parseId(raw: string): number | null {
  const id = Number(raw);
  if (!Number.isInteger(id) || id <= 0) return null;
  return id;
}

function validateCreate(input: Partial<BookInput>): string | null {
  if (input === null || typeof input !== 'object') {
    return 'request body must be a JSON object';
  }
  if (typeof input.title !== 'string' || input.title.trim() === '') {
    return 'title is required and must be a non-empty string';
  }
  if (typeof input.author !== 'string' || input.author.trim() === '') {
    return 'author is required and must be a non-empty string';
  }
  if (input.year !== undefined && input.year !== null) {
    if (typeof input.year !== 'number' || !Number.isInteger(input.year)) {
      return 'year must be an integer or null';
    }
    if (input.year < 0 || input.year > new Date().getFullYear() + 5) {
      return 'year is out of range';
    }
  }
  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== 'string') {
      return 'isbn must be a string or null';
    }
  }
  return null;
}

function validateUpdate(input: Partial<BookUpdate>): string | null {
  if (input === null || typeof input !== 'object') {
    return 'request body must be a JSON object';
  }
  if (input.title !== undefined && (typeof input.title !== 'string' || input.title.trim() === '')) {
    return 'title must be a non-empty string';
  }
  if (input.author !== undefined && (typeof input.author !== 'string' || input.author.trim() === '')) {
    return 'author must be a non-empty string';
  }
  if (input.year !== undefined && input.year !== null) {
    if (typeof input.year !== 'number' || !Number.isInteger(input.year)) {
      return 'year must be an integer or null';
    }
    if (input.year < 0 || input.year > new Date().getFullYear() + 5) {
      return 'year is out of range';
    }
  }
  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== 'string') {
      return 'isbn must be a string or null';
    }
  }
  return null;
}

export { express };
