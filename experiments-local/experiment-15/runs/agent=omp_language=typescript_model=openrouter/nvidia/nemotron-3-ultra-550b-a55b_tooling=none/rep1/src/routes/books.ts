import { Router, Request, Response, NextFunction } from 'express';
import { createBook, getAllBooks, getBookById, updateBook, deleteBook } from '../db/database.js';
import { createBookSchema, updateBookSchema, bookIdSchema, authorFilterSchema } from '../validation/book.js';
import type { CreateBookInput, UpdateBookInput } from '../types/book.js';

const router = Router();

function validateBody<T>(schema: { parse: (data: unknown) => T }) {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      req.body = schema.parse(req.body);
      next();
    } catch (error) {
      if (error instanceof Error && 'issues' in error) {
        const zodError = error as { issues: { path: (string | number)[]; message: string }[] };
        return res.status(400).json({
          error: 'Validation failed',
          details: zodError.issues.map((i) => `${i.path.join('.')}: ${i.message}`),
        });
      }
      return res.status(400).json({ error: 'Invalid request body' });
    }
  };
}

function validateParams<T>(schema: { parse: (data: unknown) => T }) {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      req.params = schema.parse(req.params) as Record<string, string>;
      next();
    } catch (error) {
      if (error instanceof Error && 'issues' in error) {
        const zodError = error as { issues: { path: (string | number)[]; message: string }[] };
        return res.status(400).json({
          error: 'Validation failed',
          details: zodError.issues.map((i) => `${i.path.join('.')}: ${i.message}`),
        });
      }
      return res.status(400).json({ error: 'Invalid request parameters' });
    }
  };
}

function validateQuery<T>(schema: { parse: (data: unknown) => T }) {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      req.query = schema.parse(req.query) as Record<string, string>;
      next();
    } catch (error) {
      if (error instanceof Error && 'issues' in error) {
        const zodError = error as { issues: { path: (string | number)[]; message: string }[] };
        return res.status(400).json({
          error: 'Validation failed',
          details: zodError.issues.map((i) => `${i.path.join('.')}: ${i.message}`),
        });
      }
      return res.status(400).json({ error: 'Invalid query parameters' });
    }
  };
}

router.post(
  '/',
  validateBody(createBookSchema),
  (req: Request, res: Response) => {
    const input = req.body as CreateBookInput;
    const book = createBook(input);
    res.status(201).json(book);
  }
);

router.get(
  '/',
  validateQuery(authorFilterSchema),
  (req: Request, res: Response) => {
    const author = Array.isArray(req.query.author) ? req.query.author[0] : req.query.author;
    const books = getAllBooks({ author });
    res.json(books);
  }
);

router.get(
  '/:id',
  validateParams(bookIdSchema),
  (req: Request, res: Response) => {
    const id = parseInt(req.params.id, 10);
    const book = getBookById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(book);
  }
);

router.put(
  '/:id',
  validateParams(bookIdSchema),
  validateBody(updateBookSchema),
  (req: Request, res: Response) => {
    const id = parseInt(req.params.id, 10);
    const input = req.body as UpdateBookInput;
    const book = updateBook(id, input);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(book);
  }
);

router.delete(
  '/:id',
  validateParams(bookIdSchema),
  (req: Request, res: Response) => {
    const id = parseInt(req.params.id, 10);
    const deleted = deleteBook(id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(204).send();
  }
);

export default router;