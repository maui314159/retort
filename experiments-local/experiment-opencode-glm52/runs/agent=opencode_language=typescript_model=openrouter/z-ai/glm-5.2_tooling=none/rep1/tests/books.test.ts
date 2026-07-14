import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { openDatabase } from "../src/db.js";
import type { Database as DB } from "better-sqlite3";

function freshDb(): DB {
  const db = openDatabase(":memory:");
  db.exec("DELETE FROM books;");
  return db;
}

describe("health", () => {
  let db: DB;
  beforeEach(() => {
    db = freshDb();
  });

  it("returns ok status", async () => {
    const app = createApp(db);
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("books CRUD", () => {
  let db: DB;
  beforeEach(() => {
    db = freshDb();
  });

  it("creates a book and retrieves it by id", async () => {
    const app = createApp(db);
    const create = await request(app)
      .post("/books")
      .send({ title: "The Hobbit", author: "Tolkien", year: 1937, isbn: "978-0261102217" });
    expect(create.status).toBe(201);
    expect(create.body).toMatchObject({
      title: "The Hobbit",
      author: "Tolkien",
      year: 1937,
      isbn: "978-0261102217",
    });
    expect(typeof create.body.id).toBe("number");

    const get = await request(app).get(`/books/${create.body.id}`);
    expect(get.status).toBe(200);
    expect(get.body).toEqual(create.body);
  });

  it("rejects creation without required fields", async () => {
    const app = createApp(db);
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(Array.isArray(res.body.errors)).toBe(true);
    const fields = res.body.errors.map((e: { field: string }) => e.field);
    expect(fields).toContain("title");
    expect(fields).toContain("author");
  });

  it("lists all books and supports ?author= filter", async () => {
    const app = createApp(db);
    await request(app).post("/books").send({ title: "A", author: "Alice" });
    await request(app).post("/books").send({ title: "B", author: "Bob" });
    await request(app).post("/books").send({ title: "C", author: "Alice" });

    const all = await request(app).get("/books");
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const filtered = await request(app).get("/books?author=Alice");
    expect(filtered.status).toBe(200);
    expect(filtered.body).toHaveLength(2);
    expect(filtered.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });

  it("updates a book via PUT", async () => {
    const app = createApp(db);
    const created = await request(app)
      .post("/books")
      .send({ title: "Old", author: "Old Author", year: 1990 });
    const id = created.body.id;

    const updated = await request(app)
      .put(`/books/${id}`)
      .send({ title: "New", author: "New Author", year: 2000, isbn: "123" });
    expect(updated.status).toBe(200);
    expect(updated.body).toMatchObject({
      id,
      title: "New",
      author: "New Author",
      year: 2000,
      isbn: "123",
    });
  });

  it("deletes a book and returns 404 afterwards", async () => {
    const app = createApp(db);
    const created = await request(app)
      .post("/books")
      .send({ title: "ToDelete", author: "Author" });
    const id = created.body.id;

    const del = await request(app).delete(`/books/${id}`);
    expect(del.status).toBe(204);

    const get = await request(app).get(`/books/${id}`);
    expect(get.status).toBe(404);
  });

  it("returns 404 for unknown id on GET, PUT, DELETE", async () => {
    const app = createApp(db);
    expect((await request(app).get("/books/9999")).status).toBe(404);
    expect(
      (await request(app).put("/books/9999").send({ title: "x", author: "y" })).status
    ).toBe(404);
    expect((await request(app).delete("/books/9999")).status).toBe(404);
  });

  it("rejects invalid id format", async () => {
    const app = createApp(db);
    expect((await request(app).get("/books/abc")).status).toBe(400);
  });
});
