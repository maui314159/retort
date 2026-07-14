import request from 'supertest';
import { describe, it, expect, beforeEach } from 'vitest';
import { createApp } from '../src/app';

function freshApp() {
  return createApp({ dbPath: ':memory:' });
}

describe('Health check', () => {
  it('GET /health returns 200 ok', async () => {
    const { app } = freshApp();
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('Books CRUD', () => {
  it('creates, lists, gets, updates, and deletes a book', async () => {
    const { app } = freshApp();

    // create
    const createRes = await request(app).post('/books').send({
      title: 'The Pragmatic Programmer',
      author: 'Andy Hunt',
      year: 1999,
      isbn: '978-0201616224',
    });
    expect(createRes.status).toBe(201);
    expect(createRes.body).toMatchObject({
      title: 'The Pragmatic Programmer',
      author: 'Andy Hunt',
      year: 1999,
      isbn: '978-0201616224',
    });
    const id = createRes.body.id;
    expect(typeof id).toBe('number');

    // list
    const listRes = await request(app).get('/books');
    expect(listRes.status).toBe(200);
    expect(listRes.body).toHaveLength(1);
    expect(listRes.body[0].id).toBe(id);

    // get by id
    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body.title).toBe('The Pragmatic Programmer');

    // update
    const updateRes = await request(app).put(`/books/${id}`).send({ year: 2019 });
    expect(updateRes.status).toBe(200);
    expect(updateRes.body.year).toBe(2019);
    expect(updateRes.body.title).toBe('The Pragmatic Programmer');

    // delete
    const delRes = await request(app).delete(`/books/${id}`);
    expect(delRes.status).toBe(204);

    // get after delete -> 404
    const afterDelete = await request(app).get(`/books/${id}`);
    expect(afterDelete.status).toBe(404);
  });
});

describe('Validation', () => {
  it('rejects creating a book without title/author', async () => {
    const { app } = freshApp();
    const res = await request(app).post('/books').send({ year: 2020 });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/);
  });

  it('returns 404 for unknown book id', async () => {
    const { app } = freshApp();
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
  });
});

describe('Author filter', () => {
  beforeEach(() => {});

  it('filters books by ?author=', async () => {
    const { app } = freshApp();
    await request(app).post('/books').send({ title: 'Book A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Bob' });
    await request(app).post('/books').send({ title: 'Book C', author: 'Alice' });

    const all = await request(app).get('/books');
    expect(all.body).toHaveLength(3);

    const alice = await request(app).get('/books?author=Alice');
    expect(alice.status).toBe(200);
    expect(alice.body).toHaveLength(2);
    expect(alice.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
  });
});
