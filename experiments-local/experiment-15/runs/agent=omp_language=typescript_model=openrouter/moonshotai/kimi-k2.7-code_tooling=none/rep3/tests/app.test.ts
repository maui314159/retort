import request from 'supertest';
import { createApp } from '../src/app';
import { closeDatabase, resetDatabaseState } from '../src/db';

const app = createApp(':memory:');

afterEach(() => {
  resetDatabaseState();
});

afterAll(() => {
  closeDatabase();
});

describe('GET /health', () => {
  it('returns status ok', async () => {
    const response = await request(app).get('/health');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book with all fields', async () => {
    const response = await request(app)
      .post('/books')
      .send({ title: 'The Hobbit', author: 'J.R.R. Tolkien', year: 1937, isbn: '978-0547928227' });

    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({
      id: expect.any(Number),
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0547928227',
    });
  });

  it('rejects a book without a title', async () => {
    const response = await request(app)
      .post('/books')
      .send({ author: 'Anonymous' });

    expect(response.status).toBe(400);
    expect(response.body.error).toMatch(/title/);
  });

  it('rejects a book without an author', async () => {
    const response = await request(app)
      .post('/books')
      .send({ title: 'Untitled' });

    expect(response.status).toBe(400);
    expect(response.body.error).toMatch(/author/);
  });

  it('rejects a non-integer year', async () => {
    const response = await request(app)
      .post('/books')
      .send({ title: 'Test', author: 'Tester', year: 2000.5 });

    expect(response.status).toBe(400);
    expect(response.body.error).toMatch(/year/);
  });
});

describe('GET /books', () => {
  it('lists all books', async () => {
    await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    await request(app).post('/books').send({ title: 'Foundation', author: 'Isaac Asimov' });

    const response = await request(app).get('/books');

    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(2);
  });

  it('filters books by author', async () => {
    await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    await request(app).post('/books').send({ title: 'Foundation', author: 'Isaac Asimov' });

    const response = await request(app).get('/books?author=Asimov');

    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].author).toBe('Isaac Asimov');
  });
});

describe('GET /books/:id', () => {
  it('returns a single book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert' });

    const response = await request(app).get(`/books/${created.body.id}`);

    expect(response.status).toBe(200);
    expect(response.body.title).toBe('Dune');
  });

  it('returns 404 for a missing book', async () => {
    const response = await request(app).get('/books/999');

    expect(response.status).toBe(404);
  });

  it('returns 400 for an invalid id', async () => {
    const response = await request(app).get('/books/abc');

    expect(response.status).toBe(400);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert', year: 1965 });

    const response = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ year: 1966 });

    expect(response.status).toBe(200);
    expect(response.body.year).toBe(1966);
    expect(response.body.title).toBe('Dune');
  });

  it('returns 404 for a missing book', async () => {
    const response = await request(app)
      .put('/books/999')
      .send({ year: 2000 });

    expect(response.status).toBe(404);
  });

  it('returns 400 for empty update body', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert' });

    const response = await request(app)
      .put(`/books/${created.body.id}`)
      .send({});

    expect(response.status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert' });

    const deleteResponse = await request(app).delete(`/books/${created.body.id}`);
    expect(deleteResponse.status).toBe(204);

    const getResponse = await request(app).get(`/books/${created.body.id}`);
    expect(getResponse.status).toBe(404);
  });

  it('returns 404 for a missing book', async () => {
    const response = await request(app).delete('/books/999');

    expect(response.status).toBe(404);
  });
});
