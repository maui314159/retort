import request from 'supertest';
import { createApp } from '../src/app';
import { createDb } from '../src/db';
import Database from 'better-sqlite3';

describe('Book Collection API', () => {
  let db: Database.Database;
  let app: ReturnType<typeof createApp>['app'];

  beforeEach(() => {
    db = createDb();
    ({ app } = createApp(db));
  });

  afterEach(() => {
    db.close();
  });

  describe('GET /health', () => {
    it('returns ok status', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a book and returns 201', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: 1,
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
    });

    it('returns 400 when title is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ author: 'Some Author' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBeDefined();
    });

    it('returns 400 when author is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Some Title' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBeDefined();
    });

    it('creates a book with only required fields', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Minimal Book', author: 'Minimal Author' });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe('GET /books', () => {
    it('returns empty list initially', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it('returns all books', async () => {
      await request(app).post('/books').send({ title: 'Book A', author: 'Author 1' });
      await request(app).post('/books').send({ title: 'Book B', author: 'Author 2' });
      const res = await request(app).get('/books');
      expect(res.body).toHaveLength(2);
    });

    it('filters by author', async () => {
      await request(app).post('/books').send({ title: 'Book A', author: 'Author 1' });
      await request(app).post('/books').send({ title: 'Book B', author: 'Author 2' });
      const res = await request(app).get('/books?author=Author+1');
      expect(res.body).toHaveLength(1);
      expect(res.body[0].title).toBe('Book A');
    });
  });

  describe('GET /books/:id', () => {
    it('returns a book by id', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'Test Book', author: 'Test Author' });
      const id = createRes.body.id;
      const res = await request(app).get(`/books/${id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Test Book');
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request(app).get('/books/9999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates a book', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'Old Title', author: 'Old Author' });
      const id = createRes.body.id;
      const res = await request(app)
        .put(`/books/${id}`)
        .send({ title: 'New Title' });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New Title');
      expect(res.body.author).toBe('Old Author');
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'Whatever' });
      expect(res.status).toBe(404);
    });

    it('returns 400 when setting title to empty', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'Valid', author: 'Valid' });
      const id = createRes.body.id;
      const res = await request(app)
        .put(`/books/${id}`)
        .send({ title: '' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes a book', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'To Delete', author: 'Author' });
      const id = createRes.body.id;
      const res = await request(app).delete(`/books/${id}`);
      expect(res.status).toBe(204);
      const getRes = await request(app).get(`/books/${id}`);
      expect(getRes.status).toBe(404);
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request(app).delete('/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
