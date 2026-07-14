import express, { Request, Response, NextFunction } from 'express';
import { db, Book } from './db';
import { bookSchema, BookInput } from './validation';
import { ZodError } from 'zod';

const app = express();
app.use(express.json());

app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

app.get('/books', (req: Request, res: Response, next: NextFunction) => {
  try {
    const { author } = req.query;
    let query = 'SELECT * FROM books';
    const params: unknown[] = [];

    if (typeof author === 'string' && author.length > 0) {
      query += ' WHERE author LIKE ?';
      params.push(`%${author}%`);
    }

    const books = db.prepare(query).all(...params) as Book[];
    res.status(200).json(books);
  } catch (error) {
    next(error);
  }
});

app.post('/books', (req: Request, res: Response, next: NextFunction) => {
  try {
    const validatedData = bookSchema.parse(req.body) as BookInput;
    const stmt = db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const result = stmt.run(
      validatedData.title,
      validatedData.author,
      validatedData.year ?? null,
      validatedData.isbn ?? null
    );

    const newBook = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
    res.status(201).json(newBook);
  } catch (error) {
    if (error instanceof ZodError) {
      res.status(400).json({ error: error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join(', ') });
    } else {
      next(error);
    }
  }
});

app.get('/books/:id', (req: Request, res: Response, next: NextFunction) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(200).json(book);
  } catch (error) {
    next(error);
  }
});

app.put('/books/:id', (req: Request, res: Response, next: NextFunction) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const existingBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existingBook) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    const validatedData = bookSchema.parse(req.body) as BookInput;
    const stmt = db.prepare(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
    );
    stmt.run(
      validatedData.title,
      validatedData.author,
      validatedData.year ?? null,
      validatedData.isbn ?? null,
      id
    );

    const updatedBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
    res.status(200).json(updatedBook);
  } catch (error) {
    if (error instanceof ZodError) {
      res.status(400).json({ error: error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join(', ') });
    } else {
      next(error);
    }
  }
});

app.delete('/books/:id', (req: Request, res: Response, next: NextFunction) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (Number.isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const existingBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existingBook) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    db.prepare('DELETE FROM books WHERE id = ?').run(id);
    res.status(204).send();
  } catch (error) {
    next(error);
  }
});

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export default app;
