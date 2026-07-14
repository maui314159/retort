import { Router, Request, Response, NextFunction } from 'express';
import { BookDatabase } from '../models/database';
import { CreateBookInput, UpdateBookInput } from '../models/Book';

function validateCreateBook(input: Partial<CreateBookInput>): Array<{field: string; message: string}> {
  const errors: Array<{field: string; message: string}> = [];

  if (!input.title || input.title.trim().length === 0) {
    errors.push({ field: 'title', message: 'Title is required' });
  }

  if (!input.author || input.author.trim().length === 0) {
    errors.push({ field: 'author', message: 'Author is required' });
  }

  if (input.year !== undefined && (typeof input.year !== 'number' || input.year < 0 || input.year > new Date().getFullYear())) {
    errors.push({ field: 'year', message: 'Year must be a valid number between 0 and current year' });
  }

  if (input.isbn !== undefined && input.isbn && !/^(?=(?:\D*\d){10}(?:(?:\D*\d){3})?$)[\d-]+$/.test(input.isbn)) {
    errors.push({ field: 'isbn', message: 'ISBN must be a valid format' });
  }

  return errors;
}

function validateUpdateBook(input: Partial<UpdateBookInput>): Array<{field: string; message: string}> {
  const errors: Array<{field: string; message: string}> = [];

  if (input.title !== undefined && (!input.title || input.title.trim().length === 0)) {
    errors.push({ field: 'title', message: 'Title cannot be empty' });
  }

  if (input.author !== undefined && (!input.author || input.author.trim().length === 0)) {
    errors.push({ field: 'author', message: 'Author cannot be empty' });
  }

  if (input.year !== undefined && (typeof input.year !== 'number' || input.year < 0 || input.year > new Date().getFullYear())) {
    errors.push({ field: 'year', message: 'Year must be a valid number between 0 and current year' });
  }

  if (input.isbn !== undefined && input.isbn && !/^(?=(?:\D*\d){10}(?:(?:\D*\d){3})?$)[\d-]+$/.test(input.isbn)) {
    errors.push({ field: 'isbn', message: 'ISBN must be a valid format' });
  }

  return errors;
}

export function createBookRoutes(db: BookDatabase): Router {
  const router = Router();

  // Health check endpoint
  router.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
  });

  // POST /books - Create a new book
  router.post('/books', (req: Request, res: Response, next: NextFunction) => {
    try {
      const input = req.body as CreateBookInput;

      // Validate input
      const errors = validateCreateBook(input);
      if (errors.length > 0) {
        res.status(400).json({ errors });
        return;
      }

      const book = db.createBook(input);
      res.status(201).json(book);
    } catch (error) {
      next(error);
    }
  });

  // GET /books - List all books with optional author filter
  router.get('/books', (req: Request, res: Response, next: NextFunction) => {
    try {
      const authorFilter = req.query.author as string | undefined;
      const books = db.getAllBooks(authorFilter);
      res.json(books);
    } catch (error) {
      next(error);
    }
  });

  // GET /books/:id - Get a single book by ID
  router.get('/books/:id', (req: Request, res: Response, next: NextFunction) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        res.status(400).json({ error: 'Invalid book ID' });
        return;
      }

      const book = db.getBookById(id);
      if (!book) {
        res.status(404).json({ error: 'Book not found' });
        return;
      }

      res.json(book);
    } catch (error) {
      next(error);
    }
  });

  // PUT /books/:id - Update a book
  router.put('/books/:id', (req: Request, res: Response, next: NextFunction) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        res.status(400).json({ error: 'Invalid book ID' });
        return;
      }

      const input = req.body as UpdateBookInput;

      // Validate input (only validate fields that are present)
      const errors = validateUpdateBook(input);
      if (errors.length > 0) {
        res.status(400).json({ errors });
        return;
      }

      const book = db.updateBook(id, input);
      if (!book) {
        res.status(404).json({ error: 'Book not found' });
        return;
      }

      res.json(book);
    } catch (error) {
      next(error);
    }
  });

  // DELETE /books/:id - Delete a book
  router.delete('/books/:id', (req: Request, res: Response, next: NextFunction) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        res.status(400).json({ error: 'Invalid book ID' });
        return;
      }

      const deleted = db.deleteBook(id);
      if (!deleted) {
        res.status(404).json({ error: 'Book not found' });
        return;
      }

      res.status(204).send();
    } catch (error) {
      next(error);
    }
  });

  return router;
}
