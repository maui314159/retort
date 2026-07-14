import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { openDatabase, type Database as DatabaseType } from "../src/db.js";
import type { Application } from "express";

let db: DatabaseType;
let app: Application;

beforeEach(() => {
  db = openDatabase(":memory:");
  app = createApp(db);
});

describe("GET /health", () => {
  it("returns 200 ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("Books API", () => {
  it("creates, fetches, lists, updates, and deletes a book", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "1984", author: "George Orwell", year: 1949, isbn: "123" });
    expect(created.status).toBe(201);
    expect(created.body.id).toBeDefined();
    expect(created.body.title).toBe("1984");

    const fetched = await request(app).get(`/books/${created.body.id}`);
    expect(fetched.status).toBe(200);
    expect(fetched.body.title).toBe("1984");

    const listed = await request(app).get("/books");
    expect(listed.status).toBe(200);
    expect(Array.isArray(listed.body)).toBe(true);
    expect(listed.body.length).toBe(1);

    const updated = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "Nineteen Eighty-Four", author: "George Orwell", year: 1949, isbn: "123" });
    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe("Nineteen Eighty-Four");

    const deleted = await request(app).delete(`/books/${created.body.id}`);
    expect(deleted.status).toBe(204);

    const notFound = await request(app).get(`/books/${created.body.id}`);
    expect(notFound.status).toBe(404);
  });

  it("rejects creating a book without required fields", async () => {
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toBeDefined();
    const fields = res.body.errors.map((e: { field: string }) => e.field);
    expect(fields).toContain("title");
    expect(fields).toContain("author");
  });

  it("filters books by author", async () => {
    await request(app).post("/books").send({ title: "Book A", author: "Alice" });
    await request(app).post("/books").send({ title: "Book B", author: "Bob" });
    await request(app).post("/books").send({ title: "Book C", author: "Alice" });

    const res = await request(app).get("/books?author=Alice");
    expect(res.status).toBe(200);
    expect(res.body.length).toBe(2);
    expect(res.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });

  it("returns 404 for unknown book on GET, PUT, DELETE", async () => {
    expect((await request(app).get("/books/9999")).status).toBe(404);
    expect(
      (
        await request(app)
          .put("/books/9999")
          .send({ title: "X", author: "Y" })
      ).status
    ).toBe(404);
    expect((await request(app).delete("/books/9999")).status).toBe(404);
  });
});
