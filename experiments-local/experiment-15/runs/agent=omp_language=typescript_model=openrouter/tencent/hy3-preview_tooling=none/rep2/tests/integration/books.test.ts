import request from 'supertest';
import { BookDatabase } from '../../src/db/database';
import { createApp } from '../../src/app';
import { Express } from 'express';
interface ErrorResponse {
  error: string;
}

interface HealthResponse {
  status: string;
}

let db: BookDatabase;
let app: Express;

beforeEach(() => {
  db = new BookDatabase(':memory:');
  app = createApp(db);
});

afterEach(() => {
  db.close();
});

describe('POST /books', () => {
  it('should create a book with all fields', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: '1984', author: 'George Orwell', year: 1949, isbn: '978-0451524935' });

    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      title: '1984',
      author: 'George Orwell',
      year: 1949,
      isbn: '978-0451524935',
    });
    expect(res.body.id).toBeDefined();
  });

  it('should create a book with only required fields', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Animal Farm', author: 'George Orwell' });

    expect(res.status).toBe(201);
    expect(res.body.title).toBe('Animal Farm');
    expect(res.body.year).toBeUndefined();
  });

  it('should return 400 when title is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'George Orwell' });

    expect(res.status).toBe(400);
    expect((res.body as ErrorResponse).error).toMatch(/title/);
  });

  it('should return 400 when author is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: '1984' });

    expect(res.status).toBe(400);
    expect((res.body as ErrorResponse).error).toMatch(/author/);
  });
});

describe('GET /books', () => {
  beforeEach(async () => {
    await request(app).post('/books').send({ title: 'Book A', author: 'Author X' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Author Y' });
    await request(app).post('/books').send({ title: 'Book C', author: 'Author X' });
  });

  it('should list all books', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect((res.body as Array<unknown>).length).toBe(3);
  });

  it('should filter by author', async () => {
    const res = await request(app).get('/books?author=Author+X');
    expect(res.status).toBe(200);
    const books = res.body as Array<{ author: string }>;
    expect(books.length).toBe(2);
    expect(books.every((b) => b.author === 'Author X')).toBe(true);
  });
});

describe('GET /books/:id', () => {
  let createdId: number;

  beforeEach(async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Test Book', author: 'Test Author' });
    createdId = res.body.id;
  });

  it('should return a book by id', async () => {
    const res = await request(app).get(`/books/${createdId}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(createdId);
    expect(res.body.title).toBe('Test Book');
  });

  it('should return 404 for non-existent id', async () => {
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
  });

  it('should return 400 for invalid id', async () => {
    const res = await request(app).get('/books/abc');
    expect(res.status).toBe(400);
  });
});

describe('PUT /books/:id', () => {
  let createdId: number;

  beforeEach(async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Old Title', author: 'Old Author', year: 2000 });
    createdId = res.body.id;
  });

  it('should update a book', async () => {
    const res = await request(app)
      .put(`/books/${createdId}`)
      .send({ title: 'New Title', year: 2020 });

    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('Old Author');
    expect(res.body.year).toBe(2020);
  });

  it('should return 404 for non-existent book', async () => {
    const res = await request(app)
      .put('/books/9999')
      .send({ title: 'X' });
    expect(res.status).toBe(404);
  });
});

describe('DELETE /books/:id', () => {
  let createdId: number;

  beforeEach(async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'To Delete', author: 'Author' });
    createdId = res.body.id;
  });

  it('should delete a book', async () => {
    const res = await request(app).delete(`/books/${createdId}`);
    expect(res.status).toBe(204);

    const getRes = await request(app).get(`/books/${createdId}`);
    expect(getRes.status).toBe(404);
  });

  it('should return 404 for non-existent book', async () => {
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});

describe('GET /health', () => {
  it('should return ok status', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect((res.body as HealthResponse).status).toBe('ok');
  });
});
