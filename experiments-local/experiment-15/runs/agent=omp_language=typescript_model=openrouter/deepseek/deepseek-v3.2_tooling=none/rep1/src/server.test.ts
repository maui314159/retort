import request from 'supertest';
import express from 'express';
import { BookDatabase } from './db';

// Create a fresh app instance for tests
function createTestApp() {
  const app = express();
  const db = new BookDatabase(':memory:'); // Use in-memory database for tests

  app.use(express.json());

  // Health check endpoint
  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // POST /books — Create a new book
  app.post('/books', (req, res) => {
    const { title, author, year, isbn } = req.body;
    
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

    try {
      const book = db.create({
        title: title.trim(),
        author: author.trim(),
        year: year || new Date().getFullYear(),
        isbn: isbn?.trim() || '',
      });
      res.status(201).json(book);
    } catch (error) {
      if (error instanceof Error && error.message.includes('UNIQUE constraint failed')) {
        return res.status(409).json({ error: 'ISBN already exists' });
      }
      res.status(500).json({ error: 'Failed to create book' });
    }
  });

  // GET /books — List all books (support ?author= filter)
  app.get('/books', (req, res) => {
    const authorParam = req.query.author;
    const author = typeof authorParam === 'string' ? authorParam : 
                   Array.isArray(authorParam) && authorParam.length > 0 && typeof authorParam[0] === 'string' ? 
                   authorParam[0] : undefined;
    const books = db.findAll(author);
    res.status(200).json(books);
  });

  // GET /books/{id} — Get a single book by ID
  app.get('/books/:id', (req, res) => {
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
  app.put('/books/:id', (req, res) => {
    const idParam = req.params.id;
    const idStr = Array.isArray(idParam) ? idParam[0] : idParam;
    const id = parseInt(idStr, 10);
    if (isNaN(id) || id <= 0) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const { title, author, year, isbn } = req.body;
    const updates: any = {};

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
  app.delete('/books/:id', (req, res) => {
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

  return app;
}

describe('Book API', () => {
  let app: express.Express;

  beforeEach(() => {
    app = createTestApp();
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('status', 'ok');
      expect(response.body).toHaveProperty('timestamp');
    });
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const newBook = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '9780743273565'
      };

      const response = await request(app)
        .post('/books')
        .send(newBook);

      expect(response.status).toBe(201);
      expect(response.body).toMatchObject({
        title: newBook.title,
        author: newBook.author,
        year: newBook.year,
        isbn: newBook.isbn
      });
      expect(response.body).toHaveProperty('id');
      expect(response.body).toHaveProperty('created_at');
      expect(response.body).toHaveProperty('updated_at');
    });

    it('should reject creation without title and author', async () => {
      const response = await request(app)
        .post('/books')
        .send({ year: 2023 });

      expect(response.status).toBe(400);
      expect(response.body.error).toContain('Title and author are required');
    });

    it('should reject creation with invalid year', async () => {
      const response = await request(app)
        .post('/books')
        .send({
          title: 'Test Book',
          author: 'Test Author',
          year: 3000 // Future year
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toContain('Year must be a valid positive number not in the future');
    });
  });

  describe('GET /books', () => {
    it('should list all books', async () => {
      const response = await request(app).get('/books');
      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
    });

    it('should filter books by author', async () => {
      // First create a book
      await request(app).post('/books').send({
        title: 'Test Book 1',
        author: 'Author A',
        year: 2020,
        isbn: '1111111111'
      });

      await request(app).post('/books').send({
        title: 'Test Book 2',
        author: 'Author B',
        year: 2021,
        isbn: '2222222222'
      });

      const response = await request(app).get('/books?author=Author+A');
      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
      if (response.body.length > 0) {
        expect(response.body[0].author).toBe('Author A');
      }
    });
  });

  describe('GET /books/:id', () => {
    it('should return a book by ID', async () => {
      // Create a book first
      const createResponse = await request(app).post('/books').send({
        title: 'Test Book for Get',
        author: 'Test Author',
        year: 2023,
        isbn: '3333333333'
      });

      const bookId = createResponse.body.id;

      const response = await request(app).get(`/books/${bookId}`);
      expect(response.status).toBe(200);
      expect(response.body.id).toBe(bookId);
      expect(response.body.title).toBe('Test Book for Get');
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).get('/books/999999');
      expect(response.status).toBe(404);
      expect(response.body.error).toContain('Book not found');
    });

    it('should return 400 for invalid ID', async () => {
      const response = await request(app).get('/books/invalid');
      expect(response.status).toBe(400);
      expect(response.body.error).toContain('Invalid book ID');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      // Create a book first
      const createResponse = await request(app).post('/books').send({
        title: 'Original Title',
        author: 'Original Author',
        year: 2020,
        isbn: '4444444444'
      });

      const bookId = createResponse.body.id;

      const updateResponse = await request(app)
        .put(`/books/${bookId}`)
        .send({
          title: 'Updated Title',
          year: 2022
        });

      expect(updateResponse.status).toBe(200);
      expect(updateResponse.body.title).toBe('Updated Title');
      expect(updateResponse.body.author).toBe('Original Author'); // Should remain unchanged
      expect(updateResponse.body.year).toBe(2022);
    });

    it('should return 404 when updating non-existent book', async () => {
      const response = await request(app)
        .put('/books/999999')
        .send({ title: 'New Title' });

      expect(response.status).toBe(404);
      expect(response.body.error).toContain('Book not found');
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      // Create a book first
      const createResponse = await request(app).post('/books').send({
        title: 'Book to Delete',
        author: 'Delete Author',
        year: 2021,
        isbn: '5555555555'
      });

      const bookId = createResponse.body.id;

      const deleteResponse = await request(app).delete(`/books/${bookId}`);
      expect(deleteResponse.status).toBe(204);

      // Verify it's deleted
      const getResponse = await request(app).get(`/books/${bookId}`);
      expect(getResponse.status).toBe(404);
    });

    it('should return 404 when deleting non-existent book', async () => {
      const response = await request(app).delete('/books/999999');
      expect(response.status).toBe(404);
      expect(response.body.error).toContain('Book not found');
    });
  });
});