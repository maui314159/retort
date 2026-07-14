import { Request, Response, Router } from 'express';
import { getDb } from '../db';
import { Book, CreateBookRequest, UpdateBookRequest } from '../types';

const router = Router();

router.post('/', async (req: Request, res: Response) => {
  const body = req.body as CreateBookRequest;
  
  if (!body?.title || !body?.author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  const db = await getDb();
  const result = await db.run(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    [body.title, body.author, body.year ?? null, body.isbn ?? null]
  );
  
  const newBook = await db.get<Book>('SELECT * FROM books WHERE id = ?', [result.lastID]);
  res.status(201).json(newBook);
});

router.get('/', async (req: Request, res: Response) => {
  const db = await getDb();
  const authorFilter = typeof req.query.author === 'string' ? req.query.author : undefined;
  const query = authorFilter ? 'SELECT * FROM books WHERE author = ?' : 'SELECT * FROM books';
  const params = authorFilter ? [authorFilter] : [];
  
  const books = await db.all<Book[]>(query, params);
  res.status(200).json(books);
});

router.get('/:id', async (req: Request, res: Response) => {
  const db = await getDb();
  const book = await db.get<Book>('SELECT * FROM books WHERE id = ?', [req.params.id]);
  
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  
  res.status(200).json(book);
});

router.put('/:id', async (req: Request, res: Response) => {
  const body = req.body as UpdateBookRequest;
  
  if (body?.title === '' || body?.author === '') {
    return res.status(400).json({ error: 'Title and author cannot be empty' });
  }

  const db = await getDb();
  const existingBook = await db.get<Book>('SELECT * FROM books WHERE id = ?', [req.params.id]);
  if (!existingBook) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const updatedTitle = body.title ?? existingBook.title;
  const updatedAuthor = body.author ?? existingBook.author;
  const updatedYear = body.year ?? existingBook.year;
  const updatedIsbn = body.isbn ?? existingBook.isbn;

  await db.run(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
    [updatedTitle, updatedAuthor, updatedYear, updatedIsbn, req.params.id]
  );

  const updatedBook = await db.get<Book>('SELECT * FROM books WHERE id = ?', [req.params.id]);
  res.status(200).json(updatedBook);
});

router.delete('/:id', async (req: Request, res: Response) => {
  const db = await getDb();
  const existingBook = await db.get<Book>('SELECT * FROM books WHERE id = ?', [req.params.id]);
  if (!existingBook) {
    return res.status(404).json({ error: 'Book not found' });
  }

  await db.run('DELETE FROM books WHERE id = ?', [req.params.id]);
  res.status(204).send();
});

export default router;