import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../src/app.js';
import type { BookStore } from '../src/db.js';

let app: Express;
let store: BookStore;

beforeEach(() => {
  const created = createApp();
  app = created.app;
  store = created.store;
});

afterEach(() => {
  store.close();
});

describe('GET /health', () => {
  it('returns ok status', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book with valid input', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      title: 'Dune',
      author: 'Frank Herbert',
      year: 1965,
      isbn: '9780441172719',
    });
    expect(typeof res.body.id).toBe('number');
  });

  it('rejects missing required fields with 400', async () => {
    const res = await request(app).post('/books').send({ title: 'No Author' });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe('validation_failed');
    expect(res.body.details).toEqual(
      expect.arrayContaining([expect.stringMatching(/author/)])
    );
  });
});

describe('GET /books author filter', () => {
  it('lists books and supports case-insensitive substring author filter', async () => {
    store.create({ title: 'A', author: 'Alice Walker', year: 2000, isbn: null });
    store.create({ title: 'B', author: 'Bob Smith', year: 2001, isbn: null });
    store.create({ title: 'C', author: 'Alice Munro', year: 2002, isbn: null });

    const all = await request(app).get('/books');
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const byAlice = await request(app).get('/books').query({ author: 'alice' });
    expect(byAlice.status).toBe(200);
    expect(byAlice.body).toHaveLength(2);
    expect(byAlice.body.every((b: { author: string }) => b.author.startsWith('Alice'))).toBe(true);

    // Substring match (not exact) — partial name still filters.
    const partial = await request(app).get('/books').query({ author: 'walk' });
    expect(partial.status).toBe(200);
    expect(partial.body).toHaveLength(1);
    expect(partial.body[0].title).toBe('A');

    // % in input is treated as a literal, not a wildcard.
    store.create({ title: 'Ten% Off', author: '10%off', year: null, isbn: null });
    const literal = await request(app).get('/books').query({ author: '10%' });
    expect(literal.status).toBe(200);
    expect(literal.body).toHaveLength(1);
  });
});

describe('GET /books/:id', () => {
  it('returns a book by id', async () => {
    const created = store.create({ title: 'X', author: 'Y', year: null, isbn: null });
    const res = await request(app).get(`/books/${created.id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(created.id);
    expect(res.body.title).toBe('X');
  });

  it('returns 404 for missing id', async () => {
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
  });

  it('returns 400 for malformed id', async () => {
    const res = await request(app).get('/books/abc');
    expect(res.status).toBe(400);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book and reflects changes on subsequent GET', async () => {
    const created = store.create({ title: 'Old', author: 'A', year: 1900, isbn: '1' });
    const res = await request(app)
      .put(`/books/${created.id}`)
      .send({ title: 'New', author: 'A', year: 2000, isbn: '2' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New');
    expect(res.body.year).toBe(2000);

    const after = await request(app).get(`/books/${created.id}`);
    expect(after.body.title).toBe('New');
    expect(after.body.isbn).toBe('2');
  });

  it('returns 404 when updating a missing book', async () => {
    const res = await request(app)
      .put('/books/9999')
      .send({ title: 'X', author: 'Y' });
    expect(res.status).toBe(404);
  });

  it('returns 400 when body is missing required fields', async () => {
    const created = store.create({ title: 'A', author: 'B', year: null, isbn: null });
    const res = await request(app).put(`/books/${created.id}`).send({ title: 'A' });
    expect(res.status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book and returns 204', async () => {
    const created = store.create({ title: 'X', author: 'Y', year: null, isbn: null });
    const del = await request(app).delete(`/books/${created.id}`);
    expect(del.status).toBe(204);

    const after = await request(app).get(`/books/${created.id}`);
    expect(after.status).toBe(404);
  });

  it('returns 404 for unknown id', async () => {
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});
