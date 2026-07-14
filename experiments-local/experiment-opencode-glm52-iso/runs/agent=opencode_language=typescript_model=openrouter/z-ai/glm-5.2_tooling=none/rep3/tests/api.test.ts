import { createApp } from '../src/app';
import { BookStore } from '../src/store';
import request from 'supertest';
import type { Express } from 'express';
import fs from 'fs';

let store: BookStore;
let app: Express;

function uniqueDbPath(): string {
  return `/tmp/books-test-${Date.now()}-${Math.random().toString(36).slice(2)}.db`;
}

beforeEach(() => {
  store = new BookStore(uniqueDbPath());
  app = createApp(store);
});

afterEach(() => {
  store.close();
});

describe('Book API', () => {
  describe('GET /health', () => {
    it('returns 200 ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a book and returns 201', async () => {
      const res = await request(app).post('/books').send({
        title: 'The Pragmatic Programmer',
        author: 'Hunt & Thomas',
        year: 1999,
        isbn: '9780201616224',
      });
      expect(res.status).toBe(201);
      expect(res.body.id).toBeGreaterThan(0);
      expect(res.body.title).toBe('The Pragmatic Programmer');
      expect(res.body.author).toBe('Hunt & Thomas');
      expect(res.body.year).toBe(1999);
      expect(res.body.isbn).toBe('9780201616224');
    });

    it('rejects missing title with 400', async () => {
      const res = await request(app).post('/books').send({
        author: 'Someone',
      });
      expect(res.status).toBe(400);
      expect(res.body.errors).toEqual(
        expect.arrayContaining([
          'title is required and must be a non-empty string',
        ])
      );
    });

    it('rejects missing author with 400', async () => {
      const res = await request(app).post('/books').send({
        title: 'A Title',
      });
      expect(res.status).toBe(400);
      expect(res.body.errors).toEqual(
        expect.arrayContaining([
          'author is required and must be a non-empty string',
        ])
      );
    });

    it('rejects empty title with 400', async () => {
      const res = await request(app).post('/books').send({
        title: '   ',
        author: 'Someone',
      });
      expect(res.status).toBe(400);
    });

    it('rejects invalid year with 400', async () => {
      const res = await request(app).post('/books').send({
        title: 'T',
        author: 'A',
        year: 'nineteen',
      });
      expect(res.status).toBe(400);
      expect(res.body.errors).toEqual(
        expect.arrayContaining(['year must be an integer or null'])
      );
    });
  });

  describe('GET /books', () => {
    it('lists all books', async () => {
      await request(app).post('/books').send({ title: 'A', author: 'Alice' });
      await request(app).post('/books').send({ title: 'B', author: 'Bob' });
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
    });

    it('filters by author', async () => {
      await request(app).post('/books').send({ title: 'A1', author: 'Alice' });
      await request(app).post('/books').send({ title: 'A2', author: 'Alice' });
      await request(app).post('/books').send({ title: 'B1', author: 'Bob' });
      const res = await request(app).get('/books?author=Alice');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    it('returns a book by id', async () => {
      const created = await request(app).post('/books').send({
        title: 'T',
        author: 'A',
      });
      const id = created.body.id;
      const res = await request(app).get(`/books/${id}`);
      expect(res.status).toBe(200);
      expect(res.body.id).toBe(id);
    });

    it('returns 404 for unknown id', async () => {
      const res = await request(app).get('/books/9999');
      expect(res.status).toBe(404);
    });

    it('returns 400 for invalid id', async () => {
      const res = await request(app).get('/books/abc');
      expect(res.status).toBe(400);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates an existing book', async () => {
      const created = await request(app).post('/books').send({
        title: 'Old',
        author: 'Old Author',
      });
      const id = created.body.id;
      const res = await request(app).put(`/books/${id}`).send({
        title: 'New Title',
        author: 'New Author',
        year: 2020,
      });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New Title');
      expect(res.body.author).toBe('New Author');
      expect(res.body.year).toBe(2020);
    });

    it('returns 404 for unknown id', async () => {
      const res = await request(app).put('/books/9999').send({
        title: 'T',
        author: 'A',
      });
      expect(res.status).toBe(404);
    });

    it('rejects invalid body with 400', async () => {
      const created = await request(app).post('/books').send({
        title: 'Old',
        author: 'Old Author',
      });
      const id = created.body.id;
      const res = await request(app).put(`/books/${id}`).send({ title: 'Only title' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes a book and returns 204', async () => {
      const created = await request(app).post('/books').send({
        title: 'T',
        author: 'A',
      });
      const id = created.body.id;
      const res = await request(app).delete(`/books/${id}`);
      expect(res.status).toBe(204);
      const follow = await request(app).get(`/books/${id}`);
      expect(follow.status).toBe(404);
    });

    it('returns 404 for unknown id', async () => {
      const res = await request(app).delete('/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
