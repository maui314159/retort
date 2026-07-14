import request from 'supertest';
import app from '../index';
import { resetDb, getDb } from '../db';

describe('Book API', () => {
  afterAll(async () => {
    await resetDb();
  });

  beforeEach(async () => {
    await resetDb();
    const db = await getDb();
    await db.run('DELETE FROM books');
  });

  describe('GET /health', () => {
    it('returns 200 ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a new book with valid data', async () => {
      const res = await request(app).post('/books').send({
        title: 'The Pragmatic Programmer',
        author: 'Andrew Hunt',
        year: 1999,
        isbn: '978-0201616224',
      });
      expect(res.status).toBe(201);
      expect(res.body.title).toBe('The Pragmatic Programmer');
      expect(res.body.author).toBe('Andrew Hunt');
    });

    it('returns 400 if title is missing', async () => {
      const res = await request(app).post('/books').send({
        author: 'Andrew Hunt',
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Title and author are required');
    });
  });

  describe('GET /books', () => {
    it('lists all books', async () => {
      await request(app).post('/books').send({ title: 'Book 1', author: 'Author A' });
      await request(app).post('/books').send({ title: 'Book 2', author: 'Author A' });
      
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
    });

    it('filters books by author', async () => {
      await request(app).post('/books').send({ title: 'Book 1', author: 'Author A' });
      await request(app).post('/books').send({ title: 'Book 2', author: 'Author B' });
      
      const res = await request(app).get('/books?author=Author A');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(1);
      expect(res.body[0].title).toBe('Book 1');
    });
  });

  describe('GET /books/:id', () => {
    it('returns a single book', async () => {
      const postRes = await request(app).post('/books').send({ title: 'Book 1', author: 'Author A' });
      const bookId = postRes.body.id;

      const res = await request(app).get(`/books/${bookId}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Book 1');
    });

    it('returns 404 if book not found', async () => {
      const res = await request(app).get('/books/999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates a book', async () => {
      const postRes = await request(app).post('/books').send({ title: 'Old Title', author: 'Author A' });
      const bookId = postRes.body.id;

      const res = await request(app).put(`/books/${bookId}`).send({ title: 'New Title' });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New Title');
      expect(res.body.author).toBe('Author A');
    });

    it('returns 404 if book not found', async () => {
      const res = await request(app).put('/books/999').send({ title: 'New Title' });
      expect(res.status).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes a book', async () => {
      const postRes = await request(app).post('/books').send({ title: 'To Delete', author: 'Author A' });
      const bookId = postRes.body.id;

      const res = await request(app).delete(`/books/${bookId}`);
      expect(res.status).toBe(204);

      const getRes = await request(app).get(`/books/${bookId}`);
      expect(getRes.status).toBe(404);
    });

    it('returns 404 if book not found', async () => {
      const res = await request(app).delete('/books/999');
      expect(res.status).toBe(404);
    });
  });
});