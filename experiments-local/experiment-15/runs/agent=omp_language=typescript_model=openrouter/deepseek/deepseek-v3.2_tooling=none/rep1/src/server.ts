import express, { Request, Response } from 'express';
import { BookDatabase, CreateBookInput, UpdateBookInput } from './db';

const app = express();
const db = new BookDatabase();

app.use(express.json());

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// POST /books — Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;
  
  // Input validation
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required' 
    });
  }

  if (typeof title !== 'string' || typeof author !== 'string') {
    return res.status(400).json({ 
      error: 'Title and author must be strings' 
    });
  }

  if (year && (typeof year !== 'number' || year < 0 || year > new Date().getFullYear())) {
    return res.status(400).json({ 
      error: 'Year must be a valid positive number not in the future' 
    });
  }

  const bookInput: CreateBookInput = {
    title: title.trim(),
    author: author.trim(),
    year: year || new Date().getFullYear(),
    isbn: isbn?.trim() || '',
  };

  try {
    const book = db.create(bookInput);
    res.status(201).json(book);
  } catch (error) {
    if (error instanceof Error && error.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'ISBN already exists' });
    }
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// GET /books — List all books (support ?author= filter)
app.get('/books', (req: Request, res: Response) => {
  const authorParam = req.query.author;
  const author = typeof authorParam === 'string' ? authorParam : 
                 Array.isArray(authorParam) && authorParam.length > 0 && typeof authorParam[0] === 'string' ? 
                 authorParam[0] : undefined;
  const books = db.findAll(author);
  res.status(200).json(books);
});

// GET /books/{id} — Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const idParam = req.params.id;
  const idStr = Array.isArray(idParam) ? idParam[0] : idParam;
  const id = parseInt(idStr, 10);
  if (isNaN(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const book = db.findById(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.status(200).json(book);
});

// PUT /books/{id} — Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  const idParam = req.params.id;
  const idStr = Array.isArray(idParam) ? idParam[0] : idParam;
  const id = parseInt(idStr, 10);
  if (isNaN(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const { title, author, year, isbn } = req.body;
  const updates: UpdateBookInput = {};

  if (title !== undefined) {
    const titleValue = Array.isArray(title) ? title[0] : title;
    if (typeof titleValue !== 'string' || !titleValue.trim()) {
      return res.status(400).json({ error: 'Title must be a non-empty string' });
    }
    updates.title = titleValue.trim();
  }

  if (author !== undefined) {
    const authorValue = Array.isArray(author) ? author[0] : author;
    if (typeof authorValue !== 'string' || !authorValue.trim()) {
      return res.status(400).json({ error: 'Author must be a non-empty string' });
    }
    updates.author = authorValue.trim();
  }

  if (year !== undefined) {
    if (typeof year !== 'number' || year < 0 || year > new Date().getFullYear()) {
      return res.status(400).json({ 
        error: 'Year must be a valid positive number not in the future' 
      });
    }
    updates.year = year;
  }

  if (isbn !== undefined) {
    const isbnValue = Array.isArray(isbn) ? isbn[0] : isbn;
    if (typeof isbnValue !== 'string') {
      return res.status(400).json({ error: 'ISBN must be a string' });
    }
    updates.isbn = isbnValue.trim();
  }

  try {
    const updatedBook = db.update(id, updates);
    if (!updatedBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(updatedBook);
  } catch (error) {
    if (error instanceof Error && error.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'ISBN already exists' });
    }
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// DELETE /books/{id} — Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const idParam = req.params.id;
  const idStr = Array.isArray(idParam) ? idParam[0] : idParam;
  const id = parseInt(idStr, 10);
  if (isNaN(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const deleted = db.delete(id);
  if (!deleted) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.status(204).send();
});

// Graceful shutdown
process.on('SIGINT', () => {
  db.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  db.close();
  process.exit(0);
});

export default app;