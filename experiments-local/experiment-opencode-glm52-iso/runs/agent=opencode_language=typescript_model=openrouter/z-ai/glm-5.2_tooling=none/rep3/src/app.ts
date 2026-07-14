import express, { type Request, type Response, type NextFunction } from 'express';
import { BookStore, type NewBook } from './store';

export function createApp(store: BookStore): express.Express {
  const app = express();
  app.use(express.json());

  const validateBook = (
    body: unknown
  ): { ok: true; value: NewBook } | { ok: false; errors: string[] } => {
    const errors: string[] = [];
    if (typeof body !== 'object' || body === null) {
      return { ok: false, errors: ['Request body must be a JSON object'] };
    }
    const b = body as Record<string, unknown>;
    if (typeof b.title !== 'string' || b.title.trim() === '') {
      errors.push('title is required and must be a non-empty string');
    }
    if (typeof b.author !== 'string' || b.author.trim() === '') {
      errors.push('author is required and must be a non-empty string');
    }
    if (b.year !== undefined && b.year !== null) {
      if (typeof b.year !== 'number' || !Number.isInteger(b.year)) {
        errors.push('year must be an integer or null');
      }
    }
    if (b.isbn !== undefined && b.isbn !== null) {
      if (typeof b.isbn !== 'string') {
        errors.push('isbn must be a string or null');
      }
    }
    if (errors.length > 0) {
      return { ok: false, errors };
    }
    return {
      ok: true,
      value: {
        title: (b.title as string).trim(),
        author: (b.author as string).trim(),
        year: b.year === undefined ? null : (b.year as number),
        isbn: b.isbn === undefined ? null : (b.isbn as string),
      },
    };
  };

  const parseId = (req: Request): number | null => {
    const raw = req.params.id;
    const n = Number(raw);
    if (!Number.isInteger(n) || n <= 0) {
      return null;
    }
    return n;
  };

  const asyncHandler =
    (fn: (req: Request, res: Response) => Promise<void>) =>
    (req: Request, res: Response, next: NextFunction) => {
      Promise.resolve(fn(req, res)).catch(next);
    };

  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post(
    '/books',
    asyncHandler(async (req, res) => {
      const result = validateBook(req.body);
      if (!result.ok) {
        res.status(400).json({ errors: result.errors });
        return;
      }
      const created = store.insert(result.value);
      res.status(201).json(created);
    })
  );

  app.get(
    '/books',
    asyncHandler(async (req, res) => {
      const author = typeof req.query.author === 'string' ? req.query.author : undefined;
      const books = store.list(author);
      res.status(200).json(books);
    })
  );

  app.get(
    '/books/:id',
    asyncHandler(async (req, res) => {
      const id = parseId(req);
      if (id === null) {
        res.status(400).json({ errors: ['id must be a positive integer'] });
        return;
      }
      const book = store.getById(id);
      if (!book) {
        res.status(404).json({ errors: ['book not found'] });
        return;
      }
      res.status(200).json(book);
    })
  );

  app.put(
    '/books/:id',
    asyncHandler(async (req, res) => {
      const id = parseId(req);
      if (id === null) {
        res.status(400).json({ errors: ['id must be a positive integer'] });
        return;
      }
      const existing = store.getById(id);
      if (!existing) {
        res.status(404).json({ errors: ['book not found'] });
        return;
      }
      const result = validateBook(req.body);
      if (!result.ok) {
        res.status(400).json({ errors: result.errors });
        return;
      }
      const updated = store.update(id, result.value);
      res.status(200).json(updated);
    })
  );

  app.delete(
    '/books/:id',
    asyncHandler(async (req, res) => {
      const id = parseId(req);
      if (id === null) {
        res.status(400).json({ errors: ['id must be a positive integer'] });
        return;
      }
      const ok = store.delete(id);
      if (!ok) {
        res.status(404).json({ errors: ['book not found'] });
        return;
      }
      res.status(204).send();
    })
  );

  app.use(
    (err: unknown, _req: Request, res: Response, _next: NextFunction) => {
      if (err instanceof SyntaxError && 'body' in err && 'type' in err) {
        res.status(400).json({ errors: ['invalid JSON body'] });
        return;
      }
      res.status(500).json({ errors: ['internal server error'] });
    }
  );

  return app;
}
