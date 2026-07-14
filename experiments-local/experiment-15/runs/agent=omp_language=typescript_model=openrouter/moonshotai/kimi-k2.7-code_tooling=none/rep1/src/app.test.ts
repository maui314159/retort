import { beforeEach, afterEach, describe, it, expect } from "vitest";
import request from "supertest";
import { createApp } from "./app.js";
import { initDatabase, closeDatabase, getDb } from "./db.js";

describe("Books API", () => {
  beforeEach(async () => {
    await initDatabase(":memory:");
  });

  afterEach(async () => {
    await closeDatabase();
  });

  it("GET /health returns ok", async () => {
    const app = createApp();
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });

  it("POST /books creates a book and GET /books lists it", async () => {
    const app = createApp();

    const createRes = await request(app)
      .post("/books")
      .send({ title: "The Hobbit", author: "J.R.R. Tolkien", year: 1937, isbn: "978-0547928227" });

    expect(createRes.status).toBe(201);
    expect(createRes.body.title).toBe("The Hobbit");
    expect(createRes.body.author).toBe("J.R.R. Tolkien");
    expect(createRes.body.year).toBe(1937);
    expect(createRes.body.isbn).toBe("978-0547928227");
    expect(createRes.body.id).toBeDefined();

    const listRes = await request(app).get("/books");
    expect(listRes.status).toBe(200);
    expect(listRes.body).toHaveLength(1);
    expect(listRes.body[0].title).toBe("The Hobbit");
  });

  it("GET /books?author filters by author", async () => {
    const app = createApp();
    const db = getDb();
    await db.run(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
      "Book A",
      "Alice",
      2020,
      "111"
    );
    await db.run(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
      "Book B",
      "Bob",
      2021,
      "222"
    );

    const res = await request(app).get("/books?author=Alice");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe("Alice");
  });

  it("GET /books/:id returns a single book", async () => {
    const app = createApp();
    const createRes = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert" });

    const id = createRes.body.id;
    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body.title).toBe("Dune");
  });

  it("GET /books/:id returns 404 for missing book", async () => {
    const app = createApp();
    const res = await request(app).get("/books/999");
    expect(res.status).toBe(404);
  });

  it("PUT /books/:id updates a book", async () => {
    const app = createApp();
    const createRes = await request(app)
      .post("/books")
      .send({ title: "Old Title", author: "Old Author" });

    const id = createRes.body.id;
    const updateRes = await request(app)
      .put(`/books/${id}`)
      .send({ title: "New Title", author: "New Author", year: 2022 });

    expect(updateRes.status).toBe(200);
    expect(updateRes.body.title).toBe("New Title");
    expect(updateRes.body.year).toBe(2022);
  });

  it("DELETE /books/:id removes a book", async () => {
    const app = createApp();
    const createRes = await request(app)
      .post("/books")
      .send({ title: "To Delete", author: "Author" });

    const id = createRes.body.id;
    const deleteRes = await request(app).delete(`/books/${id}`);
    expect(deleteRes.status).toBe(204);

    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(404);
  });

  it("POST /books rejects missing title", async () => {
    const app = createApp();
    const res = await request(app)
      .post("/books")
      .send({ author: "Author Only" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation failed");
  });

  it("POST /books rejects empty title", async () => {
    const app = createApp();
    const res = await request(app)
      .post("/books")
      .send({ title: "", author: "Author" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation failed");
  });
});
