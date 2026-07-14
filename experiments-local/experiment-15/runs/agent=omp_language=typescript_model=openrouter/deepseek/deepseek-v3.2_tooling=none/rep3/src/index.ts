import express from 'express';
import cors from 'cors';
import { BookDatabase } from './database';
import { CreateBookRequest, UpdateBookRequest } from './types';

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

const db = new BookDatabase('books.db');

// Validation middleware
function validateCreateBook(req: express.Request, res: express.Response, next: express.NextFunction): void {
  const { title, author, year, isbn }: CreateBookRequest = req.body;

  if (!title || typeof title !== 'string' || title.trim().length === 0) {
    res.status(400).json({ error: 'Title is required and must be a non-empty string' });
    return;
  }

  if (!author || typeof author !== 'string' || author.trim().length === 0) {
    res.status(400).json({ error: 'Author is required and must be a non-empty string' });
    return;
  }

  if (year === undefined || typeof year !== 'number' || !Number.isInteger(year) || year < 0 || year > new Date().getFullYear() + 1) {
    res.status(400).json({ error: 'Year is required and must be a valid integer between 0 and current year + 1' });
    return;
  }

  if (!isbn || typeof isbn !== 'string' || isbn.trim().length === 0) {
    res.status(400).json({ error: 'ISBN is required and must be a non-empty string' });
    return;
  }

  next();
}

function validateUpdateBook(req: express.Request, res: express.Response, next: express.NextFunction): void {
  const { title, author, year, isbn }: UpdateBookRequest = req.body;

  if (title !== undefined && (typeof title !== 'string' || title.trim().length === 0)) {
    res.status(400).json({ error: 'Title must be a non-empty string if provided' });
    return;
  }

  if (author !== undefined && (typeof author !== 'string' || author.trim().length === 0)) {
    res.status(400).json({ error: 'Author must be a non-empty string if provided' });
    return;
  }

  if (year !== undefined && (typeof year !== 'number' || !Number.isInteger(year) || year < 0 || year > new Date().getFullYear() + 1)) {
    res.status(400).json({ error: 'Year must be a valid integer between 0 and current year + 1 if provided' });
    return;
  }

  if (isbn !== undefined && (typeof isbn !== 'string' || isbn.trim().length === 0)) {
    res.status(400).json({ error: 'ISBN must be a non-empty string if provided' });
    return;
  }

  if (Object.keys(req.body).length === 0) {
    res.status(400).json({ error: 'At least one field must be provided for update' });
    return;
  }

  next();
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// POST /books — Create a new book
app.post('/books', validateCreateBook, (req, res) => {
  try {
    const book = db.createBook(req.body as CreateBookRequest);
    res.status(201).json(book);
  } catch (error) {
    console.error('Error creating book:', error);
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// GET /books — List all books (with optional author filter)
app.get('/books', (req, res) => {
  try {
    const authorParam = req.query.author;
    const author = typeof authorParam === 'string' ? authorParam : undefined;
    const books = db.getAllBooks(author);
    res.status(200).json(books);
  } catch (error) {
    console.error('Error fetching books:', error);
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// GET /books/{id} — Get a single book by ID
app.get('/books/:id', (req, res) => {
  try {
    const idParam = req.params.id;
    const id = typeof idParam === 'string' ? parseInt(idParam, 10) : NaN;
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const book = db.getBookById(id);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(200).json(book);
  } catch (error) {
    console.error('Error fetching book:', error);
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// PUT /books/{id} — Update a book
  try {
    const idParam = req.params.id;
    const id = typeof idParam === 'string' ? parseInt(idParam, 10) : NaN;
    if (isNaN(id) || id <= 0) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const updatedBook = db.updateBook(id, req.body as UpdateBookRequest);
    if (!updatedBook) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(200).json(updatedBook);
  } catch (error) {
    console.error('Error updating book:', error);
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// DELETE /books/{id} — Delete a book
  try {
    const idParam = req.params.id;
    const id = typeof idParam === 'string' ? parseInt(idParam, 10) : NaN;
    if (isNaN(id) || id <= 0) {
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
    console.error('Error deleting book:', error);
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

if (require.main === module) {
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
    console.log(`Health check available at http://localhost:${port}/health`);
  });
}

export default app;