import request from 'supertest';
import { describe, it, expect, beforeAll } from 'vitest';
import app from './index';
import db from './db';

beforeAll(() => {
  // Clear database before tests
  db.exec('DELETE FROM books');
});

describe('Book Collection API', () => {
  it('GET /health should return ok', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  it('POST /books should create a new book', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: '1984', author: 'George Orwell', year: 1949, isbn: '1234567890' });
    
    expect(res.statusCode).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body.title).toBe('1984');
    expect(res.body.author).toBe('George Orwell');
  });

  it('POST /books should fail validation if title is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'George Orwell', year: 1949 });
    
    expect(res.statusCode).toBe(400);
    expect(res.body).toHaveProperty('error');
  });

  it('GET /books should return all books', async () => {
    const res = await request(app).get('/books');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBeGreaterThan(0);
  });

  it('GET /books?author=Orwell should filter books', async () => {
    const res = await request(app).get('/books?author=Orwell');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body[0].author).toBe('George Orwell');
  });

  it('PUT /books/:id should update a book', async () => {
    const getRes = await request(app).get('/books');
    const bookId = getRes.body[0].id;

    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'Animal Farm', author: 'George Orwell', year: 1945 });
    
    expect(res.statusCode).toBe(200);
    expect(res.body.title).toBe('Animal Farm');
  });

  it('DELETE /books/:id should delete a book', async () => {
    const getRes = await request(app).get('/books');
    const bookId = getRes.body[0].id;

    const res = await request(app).delete(`/books/${bookId}`);
    expect(res.statusCode).toBe(204);

    const getResAfter = await request(app).get(`/books/${bookId}`);
    expect(getResAfter.statusCode).toBe(404);
  });
});
