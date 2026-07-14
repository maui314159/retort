import request from 'supertest';
import app from '../index';
import { BookDatabase } from '../database';

// Mock the database to use in-memory for tests
jest.mock('../database', () => {
  const actual = jest.requireActual('../database');
  return {
    ...actual,
    BookDatabase: class MockBookDatabase extends actual.BookDatabase {
      constructor() {
        super(':memory:');
      }
    }
  };
});

describe('Book Collection API', () => {
  beforeEach(() => {
    // Each test runs with a fresh in-memory database
  });

  describe('GET /health', () => {
    it('should return 200 OK', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('status', 'OK');
      expect(response.body).toHaveProperty('timestamp');
    });
  });

  describe('POST /books', () => {
    it('should create a new book with valid data', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '9780743273565'
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .set('Content-Type', 'application/json');

      expect(response.status).toBe(201);
      expect(response.body).toMatchObject(bookData);
      expect(response.body).toHaveProperty('id');
      expect(typeof response.body.id).toBe('number');
    });

    it('should return 400 when title is missing', async () => {
      const invalidData = {
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '9780743273565'
      };

      const response = await request(app)
        .post('/books')
        .send(invalidData)
        .set('Content-Type', 'application/json');

      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Title');
    });

    it('should return 400 when author is missing', async () => {
      const invalidData = {
        title: 'The Great Gatsby',
        year: 1925,
        isbn: '9780743273565'
      };

      const response = await request(app)
        .post('/books')
        .send(invalidData)
        .set('Content-Type', 'application/json');

      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Author');
    });

    it('should return 400 when year is invalid', async () => {
      const invalidData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: -100,
        isbn: '9780743273565'
      };

      const response = await request(app)
        .post('/books')
        .send(invalidData)
        .set('Content-Type', 'application/json');

      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Year');
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      // Seed some test data
      await request(app).post('/books').send({
        title: 'Book 1',
        author: 'Author A',
        year: 2000,
        isbn: '1111111111'
      });

      await request(app).post('/books').send({
        title: 'Book 2',
        author: 'Author B',
        year: 2010,
        isbn: '2222222222'
      });

      await request(app).post('/books').send({
        title: 'Book 3',
        author: 'Author A',
        year: 2020,
        isbn: '3333333333'
      });
    });

    it('should return all books', async () => {
      const response = await request(app).get('/books');
      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body.length).toBe(3);
    });

    it('should filter books by author', async () => {
      const response = await request(app).get('/books?author=Author A');
      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body.length).toBe(2);
      expect(response.body[0].author).toBe('Author A');
      expect(response.body[1].author).toBe('Author A');
    });
  });

  describe('GET /books/:id', () => {
    let bookId: number;

    beforeEach(async () => {
      const response = await request(app).post('/books').send({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890'
      });
      bookId = response.body.id;
    });

    it('should return a book by id', async () => {
      const response = await request(app).get(`/books/${bookId}`);
      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        id: bookId,
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890'
      });
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).get('/books/99999');
      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('not found');
    });

    it('should return 400 for invalid id', async () => {
      const response = await request(app).get('/books/abc');
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Invalid book ID');
    });
  });

  describe('PUT /books/:id', () => {
    let bookId: number;

    beforeEach(async () => {
      const response = await request(app).post('/books').send({
        title: 'Original Title',
        author: 'Original Author',
        year: 2000,
        isbn: '1111111111'
      });
      bookId = response.body.id;
    });

    it('should update a book', async () => {
      const updates = {
        title: 'Updated Title',
        year: 2023
      };

      const response = await request(app)
        .put(`/books/${bookId}`)
        .send(updates)
        .set('Content-Type', 'application/json');

      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        id: bookId,
        title: 'Updated Title',
        author: 'Original Author', // unchanged
        year: 2023,
        isbn: '1111111111' // unchanged
      });
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app)
        .put('/books/99999')
        .send({ title: 'New Title' })
        .set('Content-Type', 'application/json');

      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('error');
    });

    it('should return 400 when no fields are provided', async () => {
      const response = await request(app)
        .put(`/books/${bookId}`)
        .send({})
        .set('Content-Type', 'application/json');

      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('At least one field');
    });
  });

  describe('DELETE /books/:id', () => {
    let bookId: number;

    beforeEach(async () => {
      const response = await request(app).post('/books').send({
        title: 'Book to Delete',
        author: 'Author',
        year: 2023,
        isbn: '9999999999'
      });
      bookId = response.body.id;
    });

    it('should delete a book', async () => {
      const deleteResponse = await request(app).delete(`/books/${bookId}`);
      expect(deleteResponse.status).toBe(204);

      const getResponse = await request(app).get(`/books/${bookId}`);
      expect(getResponse.status).toBe(404);
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).delete('/books/99999');
      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('error');
    });
  });
});