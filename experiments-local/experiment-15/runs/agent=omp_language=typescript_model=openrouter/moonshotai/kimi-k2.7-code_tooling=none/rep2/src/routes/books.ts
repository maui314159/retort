import { Router, Request, Response } from 'express';
import { db } from '../db';
import { Book } from '../types';
import { validateCreateBook, validateUpdateBook } from '../validation';

const router = Router();

router.post('/', (req: Request, res: Response) => {
  const validation = validateCreateBook(req.body);
  if (!validation.valid) {
    return res.status(400).json({ error: validation.error });
  }

  const { title, author, year, isbn } = validation.data;
  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const result = stmt.run(title, author, year ?? null, isbn ?? null);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
  return res.status(201).json(book);
});

router.get('/', (req: Request, res: Response) => {
  const author = req.query.author;
  let books: Book[];

  if (typeof author === 'string' && author.trim().length > 0) {
    books = db
      .prepare('SELECT * FROM books WHERE author LIKE ? ORDER BY id')
      .all(`%${author.trim()}%`) as Book[];
  } else {
    books = db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
  }

  return res.json(books);
});

router.get('/:id', (req: Request, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  return res.json(book);
});

router.put('/:id', (req: Request, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const validation = validateUpdateBook(req.body);
  if (!validation.valid) {
    return res.status(400).json({ error: validation.error });
  }

  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const updates = validation.data;
  const title = updates.title ?? existing.title;
  const author = updates.author ?? existing.author;
  const year = updates.year !== undefined ? updates.year : existing.year;
  const isbn = updates.isbn !== undefined ? updates.isbn : existing.isbn;

  const stmt = db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
  );
  stmt.run(title, author, year, isbn, id);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
  return res.json(book);
});

router.delete('/:id', (req: Request, res: Response) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  return res.status(204).send();
});

export default router;
