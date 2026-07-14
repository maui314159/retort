import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import request from 'supertest';
import app from '../src/index';
import { db } from '../src/db';

beforeEach(() => {
  db.exec('DELETE FROM books');
});

afterEach(() => {
  db.exec('DELETE FROM books');
});

describe('Book API', () => {
  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const newBook = {
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        year: 1937,
        isbn: '978-0547928227'
      };
      const response = await request(app).post('/books').send(newBook);
      expect(response.status).toBe(201);
      expect(response.body.title).toBe('The Hobbit');
      expect(response.body.author).toBe('J.R.R. Tolkien');
    });

    it('should reject creation with missing title', async () => {
      const newBook = {
        author: 'J.R.R. Tolkien',
        year: 1937
      };
      const response = await request(app).post('/books').send(newBook);
      expect(response.status).toBe(400);
      expect(response.body.error).toContain('title');
    });

    it('should reject creation with missing author', async () => {
      const newBook = {
        title: 'The Hobbit',
        year: 1937
      };
      const response = await request(app).post('/books').send(newBook);
      expect(response.status).toBe(400);
      expect(response.body.error).toContain('author');
    });
  });

  describe('GET /books', () => {
    it('should return empty list initially', async () => {
      const response = await request(app).get('/books');
      expect(response.status).toBe(200);
      expect(response.body).toEqual([]);
    });

    it('should return books filtered by author', async () => {
      await request(app).post('/books').send({ title: 'Book 1', author: 'Alice', year: 2020 });
      await request(app).post('/books').send({ title: 'Book 2', author: 'Bob', year: 2021 });

      const response = await request(app).get('/books?author=Alice');
      expect(response.status).toBe(200);
      expect(response.body).toHaveLength(1);
      expect(response.body[0].title).toBe('Book 1');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a single book by ID', async () => {
      const createRes = await request(app).post('/books').send({ title: 'Test Book', author: 'Test Author' });
      const id = createRes.body.id;

      const response = await request(app).get(`/books/${id}`);
      expect(response.status).toBe(200);
      expect(response.body.title).toBe('Test Book');
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).get('/books/999');
      expect(response.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('should update an existing book', async () => {
      const createRes = await request(app).post('/books').send({ title: 'Old Title', author: 'Old Author' });
      const id = createRes.body.id;

      const updateData = { title: 'New Title', author: 'New Author', year: 2024 };
      const response = await request(app).put(`/books/${id}`).send(updateData);
      expect(response.status).toBe(200);
      expect(response.body.title).toBe('New Title');
      expect(response.body.author).toBe('New Author');
    });

    it('should return 404 when updating non-existent book', async () => {
      const response = await request(app).put('/books/999').send({ title: 'New', author: 'New' });
      expect(response.status).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete an existing book', async () => {
      const createRes = await request(app).post('/books').send({ title: 'To Delete', author: 'Author' });
      const id = createRes.body.id;

      const response = await request(app).delete(`/books/${id}`);
      expect(response.status).toBe(204);

      const getResponse = await request(app).get(`/books/${id}`);
      expect(getResponse.status).toBe(404);
    });

    it('should return 404 when deleting non-existent book', async () => {
      const response = await request(app).delete('/books/999');
      expect(response.status).toBe(404);
    });
  });
});
