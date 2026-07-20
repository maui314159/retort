import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import type { Express } from "express";
import { createApp } from "../src/app.js";
import { createDatabase } from "../src/db.js";
import type { Database } from "better-sqlite3";

let db: Database;
let app: Express;

beforeEach(() => {
  db = createDatabase(":memory:");
  app = createApp(db);
});

describe("GET /health", () => {
  it("returns 200 with status ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719" });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      title: "Dune",
      author: "Frank Herbert",
      year: 1965,
      isbn: "9780441172719",
    });
    expect(res.body.id).toBeGreaterThan(0);
  });

  it("returns 400 when title or author is missing", async () => {
    const res = await request(app).post("/books").send({ title: "No Author" });
    expect(res.status).toBe(400);
    expect(res.body.error).toBeDefined();

    const res2 = await request(app).post("/books").send({ author: "No Title" });
    expect(res2.status).toBe(400);
  });
});

describe("GET /books", () => {
  it("lists all books and supports the ?author= filter", async () => {
    await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert" });
    await request(app).post("/books").send({ title: "Dune Messiah", author: "Frank Herbert" });
    await request(app).post("/books").send({ title: "Neuromancer", author: "William Gibson" });

    const all = await request(app).get("/books");
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const filtered = await request(app).get("/books").query({ author: "Frank Herbert" });
    expect(filtered.status).toBe(200);
    expect(filtered.body).toHaveLength(2);
    expect(filtered.body.every((b: { author: string }) => b.author === "Frank Herbert")).toBe(true);
  });
});

describe("GET /books/:id", () => {
  it("returns a single book or 404", async () => {
    const created = await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert" });
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe("Dune");

    const missing = await request(app).get("/books/9999");
    expect(missing.status).toBe(404);
  });
});

describe("PUT /books/:id", () => {
  it("updates a book and returns the updated record", async () => {
    const created = await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert" });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ year: 1965, isbn: "9780441172719" });
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ title: "Dune", author: "Frank Herbert", year: 1965 });

    const missing = await request(app).put("/books/9999").send({ title: "X" });
    expect(missing.status).toBe(404);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book (204) and 404s on subsequent fetch", async () => {
    const created = await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert" });
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);

    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(404);

    const again = await request(app).delete(`/books/${created.body.id}`);
    expect(again.status).toBe(404);
  });
});
