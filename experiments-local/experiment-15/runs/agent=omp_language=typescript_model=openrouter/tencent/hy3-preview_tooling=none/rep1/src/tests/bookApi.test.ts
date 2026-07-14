import { app, db } from '../index';
import request from 'supertest';

describe('Book Collection API', () => {
  beforeEach(() => {
    // Clear database before each test
    db.clear();
  });

  afterAll(() => {
    db.close();
  });

  describe('Health Check', () => {
    it('should return healthy status', async () => {
      const response = await request(app)
        .get('/health')
        .expect('Content-Type', /json/)
        .expect(200);

      expect(response.body).toHaveProperty('status', 'healthy');
      expect(response.body).toHaveProperty('timestamp');
    });
  });

  describe('POST /books', () => {
    it('should create a new book with valid data', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect('Content-Type', /json/)
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.title).toBe(bookData.title);
      expect(response.body.author).toBe(bookData.author);
      expect(response.body.year).toBe(bookData.year);
      expect(response.body.isbn).toBe(bookData.isbn);
      expect(response.body).toHaveProperty('created_at');
      expect(response.body).toHaveProperty('updated_at');
    });

    it('should create a book without optional fields', async () => {
      const bookData = {
        title: '1984',
        author: 'George Orwell',
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);

      expect(response.body.title).toBe(bookData.title);
      expect(response.body.author).toBe(bookData.author);
      expect(response.body.year).toBeUndefined();
      expect(response.body.isbn).toBeUndefined();
    });

    it('should return 400 if title is missing', async () => {
      const bookData = {
        author: 'George Orwell',
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(response.body).toHaveProperty('errors');
      expect(response.body.errors).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ field: 'title', message: 'Title is required' })
        ])
      );
    });

    it('should return 400 if author is missing', async () => {
      const bookData = {
        title: '1984',
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(response.body).toHaveProperty('errors');
      expect(response.body.errors).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ field: 'author', message: 'Author is required' })
        ])
      );
    });

    it('should return 400 if year is invalid', async () => {
      const bookData = {
        title: '1984',
        author: 'George Orwell',
        year: 3000,
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(response.body).toHaveProperty('errors');
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      // Add some test data
      await request(app).post('/books').send({ title: 'Book 1', author: 'Author A' });
      await request(app).post('/books').send({ title: 'Book 2', author: 'Author B' });
      await request(app).post('/books').send({ title: 'Book 3', author: 'Author A' });
    });

    it('should return all books', async () => {
      const response = await request(app)
        .get('/books')
        .expect(200);

      expect(response.body).toHaveLength(3);
    });

    it('should filter books by author', async () => {
      const response = await request(app)
        .get('/books?author=Author A')
        .expect(200);

      expect(response.body).toHaveLength(2);
      expect(response.body[0].author).toBe('Author A');
      expect(response.body[1].author).toBe('Author A');
    });

    it('should return empty array if no books match filter', async () => {
      const response = await request(app)
        .get('/books?author=NonExistent')
        .expect(200);

      expect(response.body).toHaveLength(0);
    });
  });

  describe('GET /books/:id', () => {
    let createdBook: Record<string, unknown>;

    beforeEach(async () => {
      const response = await request(app)
        .post('/books')
        .send({ title: 'Test Book', author: 'Test Author', year: 2023 });
      createdBook = response.body;
    });

    it('should return a book by ID', async () => {
      const response = await request(app)
        .get(`/books/${createdBook.id}`)
        .expect(200);

      expect(response.body.id).toBe(createdBook.id);
      expect(response.body.title).toBe('Test Book');
      expect(response.body.author).toBe('Test Author');
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app)
        .get('/books/9999')
        .expect(404);

      expect(response.body).toHaveProperty('error', 'Book not found');
    });

    it('should return 400 for invalid ID', async () => {
      const response = await request(app)
        .get('/books/invalid')
        .expect(400);

      expect(response.body).toHaveProperty('error', 'Invalid book ID');
    });
  });

  describe('PUT /books/:id', () => {
    let createdBook: Record<string, unknown>;

    beforeEach(async () => {
      const response = await request(app)
        .post('/books')
        .send({ title: 'Original Title', author: 'Original Author' });
      createdBook = response.body;
    });

    it('should update a book with valid data', async () => {
      const updateData = {
        title: 'Updated Title',
        year: 2024,
      };

      const response = await request(app)
        .put(`/books/${createdBook.id}`)
        .send(updateData)
        .expect(200);

      expect(response.body.id).toBe(createdBook.id);
      expect(response.body.title).toBe(updateData.title);
      expect(response.body.author).toBe('Original Author');
      expect(response.body.year).toBe(updateData.year);
    });

    it('should return 404 for updating non-existent book', async () => {
      const updateData = {
        title: 'Updated Title',
      };

      const response = await request(app)
        .put('/books/9999')
        .send(updateData)
        .expect(404);

      expect(response.body).toHaveProperty('error', 'Book not found');
    });

    it('should return 400 for invalid ID', async () => {
      const response = await request(app)
        .put('/books/invalid')
        .send({ title: 'Updated' })
        .expect(400);

      expect(response.body).toHaveProperty('error', 'Invalid book ID');
    });
  });

  describe('DELETE /books/:id', () => {
    let createdBook: Record<string, unknown>;

    beforeEach(async () => {
      const response = await request(app)
        .post('/books')
        .send({ title: 'To Delete', author: 'Author' });
      createdBook = response.body;
    });

    it('should delete a book', async () => {
      await request(app)
        .delete(`/books/${createdBook.id}`)
        .expect(204);

      // Verify book is deleted
      await request(app)
        .get(`/books/${createdBook.id}`)
        .expect(404);
    });

    it('should return 404 for deleting non-existent book', async () => {
      const response = await request(app)
        .delete('/books/9999')
        .expect(404);

      expect(response.body).toHaveProperty('error', 'Book not found');
    });

    it('should return 400 for invalid ID', async () => {
      const response = await request(app)
        .delete('/books/invalid')
        .expect(400);

      expect(response.body).toHaveProperty('error', 'Invalid book ID');
    });
  });
});
