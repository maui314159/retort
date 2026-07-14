import express, { type Express, type Request, type Response, type NextFunction } from 'express';
import { openBookStore, type BookStore } from './db.js';
import { parseBookInput, parseId } from './validation.js';

export type AppOptions = {
  store?: BookStore;
};

export function createApp(options: AppOptions = {}): { app: Express; store: BookStore } {
  const store = options.store ?? openBookStore(':memory:');
  const app = express();

  app.use(express.json({ limit: '64kb' }));

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const parsed = parseBookInput(req.body);
    if (!parsed.ok) {
      res.status(400).json({ error: 'validation_failed', details: parsed.errors });
      return;
    }
    const book = store.create(parsed.value);
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const authorParam = req.query.author;
    const filter =
      typeof authorParam === 'string' && authorParam.length > 0
        ? { author: authorParam }
        : undefined;
    res.status(200).json(store.list(filter));
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'invalid_id' });
      return;
    }
    const book = store.get(id);
    if (!book) {
      res.status(404).json({ error: 'not_found' });
      return;
    }
    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'invalid_id' });
      return;
    }
    const parsed = parseBookInput(req.body);
    if (!parsed.ok) {
      res.status(400).json({ error: 'validation_failed', details: parsed.errors });
      return;
    }
    const book = store.update(id, parsed.value);
    if (!book) {
      res.status(404).json({ error: 'not_found' });
      return;
    }
    res.status(200).json(book);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'invalid_id' });
      return;
    }
    const removed = store.remove(id);
    if (!removed) {
      res.status(404).json({ error: 'not_found' });
      return;
    }
    res.status(204).send();
  });

  // Last-resort error handler. Express requires the 4-arg signature.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const message = err instanceof Error ? err.message : 'internal_error';
    res.status(500).json({ error: 'internal_error', message });
  });

  return { app, store };
}
