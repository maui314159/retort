import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { createApp, type BookApp } from "../src/app.js";
import { createBookDb, type BookDb } from "../src/db.js";

function freshMemoryDb(): BookDb {
  return createBookDb(":memory:");
}

describe("GET /health", () => {
  let app: BookApp;

  beforeEach(() => {
    app = createApp({ db: freshMemoryDb() });
  });
  afterEach(() => app.close());

  test("returns 200 with status ok", async () => {
    const res = await request(app.app).get("/health");
    assert.equal(res.status, 200);
    assert.deepEqual(res.body, { status: "ok" });
  });
});

describe("Books CRUD lifecycle", () => {
  let app: BookApp;

  beforeEach(() => {
    app = createApp({ db: freshMemoryDb() });
  });
  afterEach(() => app.close());

  test("create, get by id, update, delete", async () => {
    const created = await request(app.app).post("/books").send({
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "9780261102217",
    });
    assert.equal(created.status, 201);
    assert.equal(created.body.data.title, "The Hobbit");
    assert.equal(created.body.data.author, "J.R.R. Tolkien");
    assert.equal(created.body.data.id, 1);
    assert.equal(created.body.data.isbn, "9780261102217");

    const id = created.body.data.id;

    const got = await request(app.app).get(`/books/${id}`);
    assert.equal(got.status, 200);
    assert.equal(got.body.data.title, "The Hobbit");

    const updated = await request(app.app).put(`/books/${id}`).send({
      title: "The Hobbit",
      author: "Tolkien",
      year: 1937,
      isbn: null,
    });
    assert.equal(updated.status, 200);
    assert.equal(updated.body.data.author, "Tolkien");
    assert.equal(updated.body.data.isbn, null);

    const deleted = await request(app.app).delete(`/books/${id}`);
    assert.equal(deleted.status, 204);
    assert.equal(deleted.text, "");

    const afterDelete = await request(app.app).get(`/books/${id}`);
    assert.equal(afterDelete.status, 404);
  });
});

describe("Input validation", () => {
  let app: BookApp;

  beforeEach(() => {
    app = createApp({ db: freshMemoryDb() });
  });
  afterEach(() => app.close());

  test("rejects missing title with 400", async () => {
    const res = await request(app.app).post("/books").send({ author: "Someone" });
    assert.equal(res.status, 400);
    assert.equal(res.body.error, "validation_error");
    assert.match(res.body.message, /title/);
  });

  test("rejects missing author with 400", async () => {
    const res = await request(app.app).post("/books").send({ title: "A Book" });
    assert.equal(res.status, 400);
    assert.equal(res.body.error, "validation_error");
    assert.match(res.body.message, /author/);
  });

  test("rejects empty string title", async () => {
    const res = await request(app.app).post("/books").send({ title: "   ", author: "A" });
    assert.equal(res.status, 400);
    assert.equal(res.body.error, "validation_error");
  });

  test("rejects non-integer year", async () => {
    const res = await request(app.app).post("/books").send({
      title: "T",
      author: "A",
      year: 3.14,
    });
    assert.equal(res.status, 400);
    assert.equal(res.body.error, "validation_error");
  });
});

describe("GET /books with author filter", () => {
  let app: BookApp;

  beforeEach(() => {
    app = createApp({ db: freshMemoryDb() });
    app.db.createBook({ title: "Book A", author: "Alice", year: 2000, isbn: null });
    app.db.createBook({ title: "Book B", author: "Bob", year: 2001, isbn: null });
    app.db.createBook({ title: "Book C", author: "Alice", year: 2002, isbn: null });
  });
  afterEach(() => app.close());

  test("returns all books without filter", async () => {
    const res = await request(app.app).get("/books");
    assert.equal(res.status, 200);
    assert.equal(res.body.data.length, 3);
  });

  test("filters by author", async () => {
    const res = await request(app.app).get("/books?author=Alice");
    assert.equal(res.status, 200);
    assert.equal(res.body.data.length, 2);
    assert.ok(res.body.data.every((b: { author: string }) => b.author === "Alice"));
  });
});

describe("Error responses for missing resources", () => {
  let app: BookApp;

  beforeEach(() => {
    app = createApp({ db: freshMemoryDb() });
  });
  afterEach(() => app.close());

  test("GET /books/:id returns 404 for unknown id", async () => {
    const res = await request(app.app).get("/books/999");
    assert.equal(res.status, 404);
    assert.equal(res.body.error, "not_found");
  });

  test("DELETE /books/:id returns 404 for unknown id", async () => {
    const res = await request(app.app).delete("/books/999");
    assert.equal(res.status, 404);
  });

  test("PUT /books/:id returns 404 for unknown id with valid body", async () => {
    const res = await request(app.app).put("/books/999").send({ title: "X", author: "Y" });
    assert.equal(res.status, 404);
  });

  test("GET /books/:id returns 400 for non-numeric id", async () => {
    const res = await request(app.app).get("/books/abc");
    assert.equal(res.status, 400);
    assert.equal(res.body.error, "invalid_id");
  });
});
