import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import Database from "better-sqlite3";
import type { Database as DBType } from "better-sqlite3";
import { createApp } from "../src/app.js";

function makeDb(): DBType {
  const db = new Database(":memory:");
  db.pragma("journal_mode = WAL").catch?.(() => {});
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
  return db;
}

let db: DBType;

beforeEach(() => {
  db = makeDb();
});

describe("Health check", () => {
  it("GET /health returns 200 ok", async () => {
    const app = createApp(db);
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("Book CRUD happy path", () => {
  it("creates, retrieves, updates, lists, and deletes a book", async () => {
    const app = createApp(db);

    const createRes = await request(app)
      .post("/books")
      .send({ title: "The Hobbit", author: "J.R.R. Tolkien", year: 1937, isbn: "9780261102217" });
    expect(createRes.status).toBe(201);
    expect(createRes.body).toMatchObject({
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "9780261102217",
    });
    const id = createRes.body.id;
    expect(id).toBeGreaterThan(0);

    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body.id).toBe(id);

    const updateRes = await request(app)
      .put(`/books/${id}`)
      .send({ year: 1938 });
    expect(updateRes.status).toBe(200);
    expect(updateRes.body.year).toBe(1938);
    expect(updateRes.body.title).toBe("The Hobbit");

    const listRes = await request(app).get("/books");
    expect(listRes.status).toBe(200);
    expect(Array.isArray(listRes.body)).toBe(true);
    expect(listRes.body).toHaveLength(1);

    const deleteRes = await request(app).delete(`/books/${id}`);
    expect(deleteRes.status).toBe(204);

    const afterDelete = await request(app).get(`/books/${id}`);
    expect(afterDelete.status).toBe(404);
  });
});

describe("Input validation", () => {
  it("rejects book creation without title and author with 400", async () => {
    const app = createApp(db);
    const res = await request(app).post("/books").send({ year: 1999 });
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty("error");
  });

  it("rejects empty/whitespace title and author", async () => {
    const app = createApp(db);
    const res = await request(app)
      .post("/books")
      .send({ title: "   ", author: "" });
    expect(res.status).toBe(400);
  });

  it("returns 404 for unknown book id", async () => {
    const app = createApp(db);
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
  });

  it("filters books by author", async () => {
    const app = createApp(db);
    await request(app).post("/books").send({ title: "A", author: "Alice" });
    await request(app).post("/books").send({ title: "B", author: "Bob" });
    await request(app).post("/books").send({ title: "C", author: "Alice" });

    const res = await request(app).get("/books?author=Alice");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });
});
