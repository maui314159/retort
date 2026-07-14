import request from 'supertest';
import { createApp } from '../src/app';
import { createDatabase } from '../src/database';
import { Database } from 'better-sqlite3';

let db: Database;
let app: ReturnType<typeof createApp>['app'];

beforeEach(() => {
  db = createDatabase();
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
      .send({ title: 'The Hobbit', author: 'J.R.R. Tolkien', year: 1937, isbn: '978-0261102217' });

    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: 1,
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0261102217',
    });
  });

  it('rejects missing title with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'Anonymous' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Validation failed');
  });

  it('rejects missing author with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'No Author Book' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Validation failed');
  });
});

describe('GET /books', () => {
  it('returns empty list initially', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it('returns all books', async () => {
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('Book A', 'Alice');
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('Book B', 'Bob');

    const res = await request(app).get('/books');
    expect(res.body).toHaveLength(2);
  });

  it('filters by author', async () => {
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('Book A', 'Alice');
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('Book B', 'Bob');

    const res = await request(app).get('/books?author=Alice');
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe('Alice');
  });
});

describe('GET /books/:id', () => {
  it('returns a book by id', async () => {
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('Found Book', 'Finder');

    const res = await request(app).get('/books/1');
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Found Book');
  });

  it('returns 404 for missing book', async () => {
    const res = await request(app).get('/books/999');
    expect(res.status).toBe(404);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book', async () => {
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('Old Title', 'Author');

    const res = await request(app)
      .put('/books/1')
      .send({ title: 'New Title' });

    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('Author');
  });

  it('returns 404 for missing book', async () => {
    const res = await request(app)
      .put('/books/999')
      .send({ title: 'Nope' });

    expect(res.status).toBe(404);
  });

  it('rejects empty title with 400', async () => {
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('Title', 'Author');

    const res = await request(app)
      .put('/books/1')
      .send({ title: '' });

    expect(res.status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book and returns 204', async () => {
    db.prepare('INSERT INTO books (title, author) VALUES (?, ?)').run('ToDelete', 'Author');

    const res = await request(app).delete('/books/1');
    expect(res.status).toBe(204);

    const check = await request(app).get('/books/1');
    expect(check.status).toBe(404);
  });

  it('returns 404 for missing book', async () => {
    const res = await request(app).delete('/books/999');
    expect(res.status).toBe(404);
  });
});
