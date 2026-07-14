import request from 'supertest';
import { app, db } from '../src/index.js';
import { Book } from '../src/types.js';

const agent = request(app);

beforeEach(async () => {
  // Clean up database before each test
  const books = await db.getAllBooks();
  for (let i = 0; i < books.length; i++) {
    await db.deleteBook(books[i].id);
  }
});

afterAll(() => {
  db.close();
});

describe('POST /books', () => {
  it('should create a new book', async () => {
    const response = await agent
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '9780743273565',
      });

    expect(response.status).toBe(201);
    expect(response.body).toHaveProperty('id');
    expect(response.body.title).toBe('The Great Gatsby');
    expect(response.body.author).toBe('F. Scott Fitzgerald');
    expect(response.body.year).toBe(1925);
    expect(response.body.isbn).toBe('9780743273565');
  });

  it('should return 400 if title is missing', async () => {
    const response = await agent
      .post('/books')
      .send({
        author: 'F. Scott Fitzgerald',
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('Title and author are required');
  });

  it('should return 400 if author is missing', async () => {
    const response = await agent
      .post('/books')
      .send({
        title: 'The Great Gatsby',
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('Title and author are required');
  });
});

describe('GET /books', () => {
  it('should return all books', async () => {
    await agent.post('/books').send({ title: 'Book 1', author: 'Author 1' });
    await agent.post('/books').send({ title: 'Book 2', author: 'Author 2' });

    const response = await agent.get('/books');

    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(2);
  });

  it('should filter by author', async () => {
    await agent.post('/books').send({ title: 'Book 1', author: 'Author A' });
    await agent.post('/books').send({ title: 'Book 2', author: 'Author B' });

    const response = await agent.get('/books?author=Author A');

    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].author).toBe('Author A');
  });
});

describe('GET /books/:id', () => {
  it('should return a single book', async () => {
    const createResponse = await agent
      .post('/books')
      .send({ title: 'Test Book', author: 'Test Author' });

    const bookId = createResponse.body.id;

    const response = await agent.get(`/books/${bookId}`);

    expect(response.status).toBe(200);
    expect(response.body.id).toBe(bookId);
    expect(response.body.title).toBe('Test Book');
  });

  it('should return 404 if book not found', async () => {
    const response = await agent.get('/books/999');

    expect(response.status).toBe(404);
    expect(response.body.error).toBe('Book not found');
  });

  it('should return 400 if id is invalid', async () => {
    const response = await agent.get('/books/invalid');

    expect(response.status).toBe(400);
    expect(response.body.error).toBe('Invalid book ID');
  });
});

describe('PUT /books/:id', () => {
  it('should update a book', async () => {
    const createResponse = await agent
      .post('/books')
      .send({ title: 'Original Title', author: 'Original Author' });

    const bookId = createResponse.body.id;

    const response = await agent
      .put(`/books/${bookId}`)
      .send({ title: 'Updated Title' });

    expect(response.status).toBe(200);
    expect(response.body.id).toBe(bookId);
    expect(response.body.title).toBe('Updated Title');
    expect(response.body.author).toBe('Original Author');
  });

  it('should return 404 if book not found', async () => {
    const response = await agent
      .put('/books/999')
      .send({ title: 'Updated Title' });

    expect(response.status).toBe(404);
    expect(response.body.error).toBe('Book not found');
  });
});

describe('DELETE /books/:id', () => {
  it('should delete a book', async () => {
    const createResponse = await agent
      .post('/books')
      .send({ title: 'Test Book', author: 'Test Author' });

    const bookId = createResponse.body.id;

    const response = await agent.delete(`/books/${bookId}`);

    expect(response.status).toBe(204);

    const getResponse = await agent.get(`/books/${bookId}`);
    expect(getResponse.status).toBe(404);
  });

  it('should return 404 if book not found', async () => {
    const response = await agent.delete('/books/999');

    expect(response.status).toBe(404);
    expect(response.body.error).toBe('Book not found');
  });
});

describe('GET /health', () => {
  it('should return ok status', async () => {
    const response = await agent.get('/health');

    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
    expect(response.body).toHaveProperty('timestamp');
  });
});
