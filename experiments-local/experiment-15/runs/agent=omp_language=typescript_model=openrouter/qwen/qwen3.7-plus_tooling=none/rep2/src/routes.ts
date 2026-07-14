import { Router, Request, Response } from 'express';
import db from './db';
import { z } from 'zod';

const router = Router();

const bookSchema = z.object({
  title: z.string().min(1, "Title is required"),
  author: z.string().min(1, "Author is required"),
  year: z.coerce.number().int().optional(),
  isbn: z.string().optional(),
});

router.post('/books', (req: Request, res: Response) => {
  try {
    const validated = bookSchema.parse(req.body);
    const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
    const info = stmt.run(validated.title, validated.author, validated.year ?? null, validated.isbn ?? null);
    res.status(201).json({ id: info.lastInsertRowid, ...validated });
  } catch (error) {
    if (error instanceof z.ZodError) {
      res.status(400).json({ error: error.errors });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

router.get('/books', (req: Request, res: Response) => {
  try {
    const { author } = req.query;
    let stmt;
    let books;
    if (typeof author === 'string') {
      stmt = db.prepare('SELECT * FROM books WHERE author LIKE ?');
      books = stmt.all(`%${author}%`);
    } else {
      stmt = db.prepare('SELECT * FROM books');
      books = stmt.all();
    }
    res.json(books);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/books/:id', (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid ID' });
    }
    const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
    const book = stmt.get(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(book);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.put('/books/:id', (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid ID' });
    }
    
    const stmtGet = db.prepare('SELECT * FROM books WHERE id = ?');
    const book = stmtGet.get(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }

    const validated = bookSchema.parse(req.body);
    const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?');
    stmt.run(validated.title, validated.author, validated.year ?? null, validated.isbn ?? null, id);
    
    const updatedBook = stmtGet.get(id);
    res.json(updatedBook);
  } catch (error) {
    if (error instanceof z.ZodError) {
      res.status(400).json({ error: error.errors });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

router.delete('/books/:id', (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid ID' });
    }
    const stmt = db.prepare('DELETE FROM books WHERE id = ?');
    const info = stmt.run(id);
    if (info.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(204).send();
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
