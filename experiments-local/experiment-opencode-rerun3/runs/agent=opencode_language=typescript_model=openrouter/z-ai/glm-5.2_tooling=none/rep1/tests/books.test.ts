import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { openDb, closeDb, type DB } from "../src/db.js";

let db: DB;

beforeEach(() => {
  db = openDb(":memory:");
});

afterEach(() => {
  closeDb(db);
});

describe("GET /health", () => {
  it("returns ok status", async () => {
    const res = await request(createApp(db)).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201", async () => {
    const res = await request(createApp(db)).post("/books").send({
      title: "The Pragmatic Programmer",
      author: "Hunt & Thomas",
      year: 1999,
      isbn: "9780201616224",
    });
    expect(res.status).toBe(201);
    expect(res.body.id).toBe(1);
    expect(res.body.title).toBe("The Pragmatic Programmer");
    expect(res.body.author).toBe("Hunt & Thomas");
    expect(res.body.year).toBe(1999);
  });

  it("rejects missing title and author with 400", async () => {
    const res = await request(createApp(db)).post("/books").send({ year: 2020 });
    expect(res.status).toBe(400);
    expect(res.body.errors.title).toBeDefined();
    expect(res.body.errors.author).toBeDefined();
  });

  it("rejects unknown fields with 400", async () => {
    const res = await request(createApp(db))
      .post("/books")
      .send({ title: "T", author: "A", unexpected: "x" });
    expect(res.status).toBe(400);
  });
});

describe("GET /books", () => {
  it("lists all books and supports ?author filter", async () => {
    const app = createApp(db);
    await request(app).post("/books").send({ title: "A", author: "Alice" });
    await request(app).post("/books").send({ title: "B", author: "Bob" });
    await request(app).post("/books").send({ title: "C", author: "Alice" });

    const all = await request(app).get("/books");
    expect(all.status).toBe(200);
    expect(all.body.length).toBe(3);

    const alice = await request(app).get("/books?author=Alice");
    expect(alice.status).toBe(200);
    expect(alice.body.length).toBe(2);
    expect(
      alice.body.every((b: { author: string }) => b.author === "Alice")
    ).toBe(true);
  });
});

describe("GET /books/:id", () => {
  it("returns a single book", async () => {
    const app = createApp(db);
    const created = await request(app).post("/books").send({
      title: "Refactoring",
      author: "Fowler",
    });
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe("Refactoring");
  });

  it("returns 404 for unknown id", async () => {
    const res = await request(createApp(db)).get("/books/999");
    expect(res.status).toBe(404);
  });

  it("returns 400 for non-numeric id", async () => {
    const res = await request(createApp(db)).get("/books/abc");
    expect(res.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("updates a book and preserves other fields", async () => {
    const app = createApp(db);
    const created = await request(app).post("/books").send({
      title: "Old",
      author: "A",
      year: 2000,
    });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "New" });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe("New");
    expect(res.body.author).toBe("A");
    expect(res.body.year).toBe(2000);
  });

  it("returns 404 for unknown id", async () => {
    const res = await request(createApp(db)).put("/books/123").send({
      title: "X",
    });
    expect(res.status).toBe(404);
  });

  it("rejects empty update body with 400", async () => {
    const app = createApp(db);
    const created = await request(app).post("/books").send({
      title: "T",
      author: "A",
    });
    const res = await request(app).put(`/books/${created.body.id}`).send({});
    expect(res.status).toBe(400);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book and returns 204", async () => {
    const app = createApp(db);
    const created = await request(app).post("/books").send({
      title: "X",
      author: "A",
    });
    const res = await request(app).delete(`/books/${created.body.id}`);
    expect(res.status).toBe(204);
  });

  it("returns 404 after deletion", async () => {
    const app = createApp(db);
    const created = await request(app).post("/books").send({
      title: "X",
      author: "A",
    });
    await request(app).delete(`/books/${created.body.id}`);
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(404);
  });

  it("returns 404 for unknown id", async () => {
    const res = await request(createApp(db)).delete("/books/999");
    expect(res.status).toBe(404);
  });
});
