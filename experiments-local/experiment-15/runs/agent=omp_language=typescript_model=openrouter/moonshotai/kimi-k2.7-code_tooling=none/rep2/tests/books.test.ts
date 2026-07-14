import request from 'supertest';
import app from '../src/app';
import { db, resetDatabase } from '../src/db';

beforeEach(() => {
  resetDatabase();
});

afterAll(() => {
  db.close();
});

describe('GET /health', () => {
  it('returns a 200 OK status', async () => {
    const response = await request(app).get('/health');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a new book with all fields', async () => {
    const response = await request(app)
      .post('/books')
      .send({
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        year: 1937,
        isbn: '978-0547928227',
      });

    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({
      id: expect.any(Number),
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0547928227',
    });
  });

  it('creates a book with only required fields', async () => {
    const response = await request(app)
      .post('/books')
      .send({
        title: 'Dune',
        author: 'Frank Herbert',
      });

    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({
      title: 'Dune',
      author: 'Frank Herbert',
      year: null,
      isbn: null,
    });
  });

  it('rejects a book without a title', async () => {
    const response = await request(app)
      .post('/books')
      .send({
        author: 'Frank Herbert',
      });

    expect(response.status).toBe(400);
    expect(response.body).toHaveProperty('error');
  });

  it('rejects a book without an author', async () => {
    const response = await request(app)
      .post('/books')
      .send({
        title: 'Dune',
      });

    expect(response.status).toBe(400);
    expect(response.body).toHaveProperty('error');
  });
});

describe('GET /books', () => {
  it('lists all books', async () => {
    await request(app).post('/books').send({ title: 'Book A', author: 'Author A' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Author B' });

    const response = await request(app).get('/books');

    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(2);
  });

  it('filters books by author', async () => {
    await request(app).post('/books').send({ title: 'Book A', author: 'Jane Doe' });
    await request(app).post('/books').send({ title: 'Book B', author: 'John Smith' });

    const response = await request(app).get('/books?author=Jane');

    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].author).toBe('Jane Doe');
  });
});

describe('GET /books/:id', () => {
  it('returns a single book by ID', async () => {
    const createResponse = await request(app)
      .post('/books')
      .send({ title: '1984', author: 'George Orwell' });

    const response = await request(app).get(`/books/${createResponse.body.id}`);

    expect(response.status).toBe(200);
    expect(response.body).toMatchObject({
      title: '1984',
      author: 'George Orwell',
    });
  });

  it('returns 404 for a non-existent book', async () => {
    const response = await request(app).get('/books/9999');

    expect(response.status).toBe(404);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book', async () => {
    const createResponse = await request(app)
      .post('/books')
      .send({ title: 'Old Title', author: 'Old Author' });

    const response = await request(app)
      .put(`/books/${createResponse.body.id}`)
      .send({ title: 'New Title' });

    expect(response.status).toBe(200);
    expect(response.body).toMatchObject({
      id: createResponse.body.id,
      title: 'New Title',
      author: 'Old Author',
    });
  });

  it('returns 404 for a non-existent book', async () => {
    const response = await request(app)
      .put('/books/9999')
      .send({ title: 'New Title' });

    expect(response.status).toBe(404);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book', async () => {
    const createResponse = await request(app)
      .post('/books')
      .send({ title: 'To Delete', author: 'Author' });

    const deleteResponse = await request(app).delete(`/books/${createResponse.body.id}`);
    expect(deleteResponse.status).toBe(204);

    const getResponse = await request(app).get(`/books/${createResponse.body.id}`);
    expect(getResponse.status).toBe(404);
  });

  it('returns 404 for a non-existent book', async () => {
    const response = await request(app).delete('/books/9999');

    expect(response.status).toBe(404);
  });
});
