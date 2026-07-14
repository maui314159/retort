import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/server.js";
import { initDb, type DB } from "../src/db.js";
import type { Application } from "express";

let db: DB;
let app: Application;

beforeEach(() => {
  db = initDb(":memory:");
  app = createApp({ db });
});

describe("GET /health", () => {
  it("returns 200 ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201", async () => {
    const res = await request(app).post("/books").send({
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "978-0261102217",
    });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "978-0261102217",
    });
    expect(res.body.id).toBeGreaterThan(0);
  });

  it("rejects missing required fields with 400", async () => {
    const res = await request(app).post("/books").send({ year: 1999 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toBeDefined();
    const fields = res.body.errors.map((e: { field: string }) => e.field);
    expect(fields).toContain("title");
    expect(fields).toContain("author");
  });
});

describe("GET /books and filtering", () => {
  beforeEach(async () => {
    await request(app).post("/books").send({ title: "A", author: "Alice", year: 2001 });
    await request(app).post("/books").send({ title: "B", author: "Bob", year: 2002 });
    await request(app).post("/books").send({ title: "C", author: "Alice", year: 2003 });
  });

  it("lists all books", async () => {
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(3);
  });

  it("filters by author", async () => {
    const res = await request(app).get("/books?author=Alice");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });
});

describe("GET /books/:id", () => {
  it("returns a book by id", async () => {
    const created = await request(app).post("/books").send({ title: "X", author: "Y" });
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe("X");
  });

  it("returns 404 for unknown id", async () => {
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
  });
});

describe("PUT /books/:id", () => {
  it("updates an existing book", async () => {
    const created = await request(app).post("/books").send({ title: "Old", author: "A" });
    const res = await request(app).put(`/books/${created.body.id}`).send({ title: "New" });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe("New");
    expect(res.body.author).toBe("A");
  });

  it("returns 404 when updating missing book", async () => {
    const res = await request(app).put("/books/9999").send({ title: "New" });
    expect(res.status).toBe(404);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book and returns 204", async () => {
    const created = await request(app).post("/books").send({ title: "Z", author: "A" });
    const res = await request(app).delete(`/books/${created.body.id}`);
    expect(res.status).toBe(204);
    const get = await request(app).get(`/books/${created.body.id}`);
    expect(get.status).toBe(404);
  });

  it("returns 404 when deleting missing book", async () => {
    const res = await request(app).delete("/books/9999");
    expect(res.status).toBe(404);
  });
});
