import express, { Request, Response, NextFunction } from 'express';
import { Database } from './database.js';
import { Book, CreateBookInput, UpdateBookInput, HealthResponse, ErrorResponse } from './types.js';

const app = express();
const db = new Database(':memory:');

app.use(express.json());

// Health check endpoint
app.get('/health', (_req: Request, res: Response<HealthResponse>): void => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
  });
});

// Create a new book
app.post('/books', async (req: Request, res: Response): Promise<void> => {
  try {
    const { title, author, year, isbn } = req.body as Record<string, unknown>;

    if (!title || !author) {
      res.status(400).json({ error: 'Title and author are required' } as ErrorResponse);
      return;
    }

    if (typeof title !== 'string' || typeof author !== 'string') {
      res.status(400).json({ error: 'Title and author must be strings' } as ErrorResponse);
      return;
    }

    const input: CreateBookInput = {
      title,
      author,
      year: typeof year === 'number' ? year : undefined,
      isbn: typeof isbn === 'string' ? isbn : undefined,
    };

    const book = await db.createBook(input);
    res.status(201).json(book);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    res.status(500).json({ error: message } as ErrorResponse);
  }
});

// List all books (with optional author filter)
app.get('/books', async (req: Request, res: Response): Promise<void> => {
  try {
    const authorFilter = typeof req.query.author === 'string' ? req.query.author : undefined;
    const books = await db.getAllBooks(authorFilter);
    res.json(books);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    res.status(500).json({ error: message } as ErrorResponse);
  }
});

// Get a single book by ID
app.get('/books/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const id = parseInt(req.params.id, 10);
    
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' } as ErrorResponse);
      return;
    }

    const book = await db.getBookById(id);
    
    if (!book) {
      res.status(404).json({ error: 'Book not found' } as ErrorResponse);
      return;
    }

    res.json(book);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    res.status(500).json({ error: message } as ErrorResponse);
  }
});

// Update a book
app.put('/books/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const id = parseInt(req.params.id, 10);
    
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' } as ErrorResponse);
      return;
    }

    const { title, author, year, isbn } = req.body as Record<string, unknown>;

    const input: UpdateBookInput = {};
    
    if (title !== undefined) {
      if (typeof title !== 'string') {
        res.status(400).json({ error: 'Title must be a string' } as ErrorResponse);
        return;
      }
      input.title = title;
    }
    
    if (author !== undefined) {
      if (typeof author !== 'string') {
        res.status(400).json({ error: 'Author must be a string' } as ErrorResponse);
        return;
      }
      input.author = author;
    }
    
    if (year !== undefined && typeof year !== 'number') {
      res.status(400).json({ error: 'Year must be a number' } as ErrorResponse);
      return;
    }
    
    if (isbn !== undefined && typeof isbn !== 'string') {
      res.status(400).json({ error: 'ISBN must be a string' } as ErrorResponse);
      return;
    }

    input.year = typeof year === 'number' ? year : undefined;
    input.isbn = typeof isbn === 'string' ? isbn : undefined;

    const book = await db.updateBook(id, input);
    
    if (!book) {
      res.status(404).json({ error: 'Book not found' } as ErrorResponse);
      return;
    }

    res.json(book);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    res.status(500).json({ error: message } as ErrorResponse);
  }
});

// Delete a book
app.delete('/books/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const id = parseInt(req.params.id, 10);
    
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' } as ErrorResponse);
      return;
    }

    const deleted = await db.deleteBook(id);
    
    if (!deleted) {
      res.status(404).json({ error: 'Book not found' } as ErrorResponse);
      return;
    }

    res.status(204).send();
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    res.status(500).json({ error: message } as ErrorResponse);
  }
});

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

if (process.env.NODE_ENV !== 'test') {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export { app, db };
