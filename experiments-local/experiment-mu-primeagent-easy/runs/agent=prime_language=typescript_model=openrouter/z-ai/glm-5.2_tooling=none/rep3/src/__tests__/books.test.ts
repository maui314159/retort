import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import { createApp } from "../app";
import { BookStore } from "../db";
import { validateBookInput } from "../validation";
import type { Express } from "express";

/**
 * Integration tests that exercise the full Express app against an in-memory
 * SQLite store. Each test gets a fresh database so there is no cross-test
 * contamination.
 */
function appWithMemoryStore(): { app: Express; store: BookStore } {
  const store = new BookStore(":memory:");
  const app = createApp(store);
  return { app, store };
}

describe("Book collection API", () => {
  let app: Express;
  let store: BookStore;

  beforeEach(() => {
    const ctx = appWithMemoryStore();
    app = ctx.app;
    store = ctx.store;
  });

  afterEach(() => {
    store.close();
  });

  // ----------------------------------------------------------------- health
  describe("GET /health", () => {
    it("returns 200 and a status ok body", async () => {
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: "ok" });
    });
  });

  // --------------------------------------------------------------- creation
  describe("POST /books", () => {
    it("creates a book and returns 201 with the persisted record", async () => {
      const res = await request(app).post("/books").send({
        title: "The Pragmatic Programmer",
        author: "Andrew Hunt",
        year: 1999,
        isbn: "978-0201616224",
      });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: expect.any(Number),
        title: "The Pragmatic Programmer",
        author: "Andrew Hunt",
        year: 1999,
        isbn: "978-0201616224",
      });
      expect(res.body.created_at).toBeTruthy();
      expect(res.body.updated_at).toBeTruthy();
    });

    it("accepts a book without optional year/isbn", async () => {
      const res = await request(app).post("/books").send({
        title: "Title Only",
        author: "Anonymous",
      });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });

    it("returns 400 when title is missing", async () => {
      const res = await request(app).post("/books").send({ author: "No Title" });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/validation/i);
      expect(res.body.details).toHaveProperty("title");
    });

    it("returns 400 when author is missing", async () => {
      const res = await request(app).post("/books").send({ title: "No Author" });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/validation/i);
      expect(res.body.details).toHaveProperty("author");
    });

    it("returns 400 when both title and author are empty strings", async () => {
      const res = await request(app).post("/books").send({ title: "  ", author: "" });
      expect(res.status).toBe(400);
      expect(res.body.details).toHaveProperty("title");
      expect(res.body.details).toHaveProperty("author");
    });

    it("returns 400 for a non-integer year", async () => {
      const res = await request(app)
        .post("/books")
        .send({ title: "T", author: "A", year: "nineteen" });
      expect(res.status).toBe(400);
      expect(res.body.details).toHaveProperty("year");
    });

    it("returns 400 for malformed JSON body", async () => {
      const res = await request(app)
        .post("/books")
        .set("Content-Type", "application/json")
        .send("{ not valid json");
      expect(res.status).toBe(400);
    });
  });

  // ------------------------------------------------------------------- list
  describe("GET /books", () => {
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

    it("filters by author (case-insensitive substring)", async () => {
      const res = await request(app).get("/books?author=Alice");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: any) => b.author === "Alice")).toBe(true);
    });

    it("returns an empty array for an unknown author", async () => {
      const res = await request(app).get("/books?author=Nobody");
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });
  });

  // -------------------------------------------------------------- get by id
  describe("GET /books/:id", () => {
    it("returns 404 for a missing id", async () => {
      const res = await request(app).get("/books/9999");
      expect(res.status).toBe(404);
      expect(res.body.error).toMatch(/not found/i);
    });

    it("returns 400 for a non-numeric id", async () => {
      const res = await request(app).get("/books/abc");
      expect(res.status).toBe(400);
    });

    it("returns the book for a valid id", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "Refactoring", author: "Martin Fowler", year: 1999 });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("Refactoring");
    });
  });

  // ------------------------------------------------------------------ update
  describe("PUT /books/:id", () => {
    it("updates an existing book", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "Old", author: "Old Author", year: 2000 });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: "New", author: "New Author", year: 2020, isbn: "123" });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("New");
      expect(res.body.author).toBe("New Author");
      expect(res.body.year).toBe(2020);
      expect(res.body.isbn).toBe("123");
    });

    it("returns 404 when updating a missing book", async () => {
      const res = await request(app)
        .put("/books/9999")
        .send({ title: "X", author: "Y" });
      expect(res.status).toBe(404);
    });

    it("returns 400 on invalid input", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "Keep", author: "Me" });
      const res = await request(app).put(`/books/${created.body.id}`).send({ author: "Only" });
      expect(res.status).toBe(400);
      expect(res.body.details).toHaveProperty("title");
    });
  });

  // ------------------------------------------------------------------ delete
  describe("DELETE /books/:id", () => {
    it("deletes a book and returns 204", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "Gone", author: "Soon" });
      const res = await request(app).delete(`/books/${created.body.id}`);
      expect(res.status).toBe(204);
      const follow = await request(app).get(`/books/${created.body.id}`);
      expect(follow.status).toBe(404);
    });

    it("returns 404 when deleting a missing book", async () => {
      const res = await request(app).delete("/books/9999");
      expect(res.status).toBe(404);
    });
  });

  // -------------------------------------------------------- unknown routes
  describe("unknown routes", () => {
    it("returns 404 for an undefined path", async () => {
      const res = await request(app).get("/nope");
      expect(res.status).toBe(404);
    });
  });
});

// ------------------------------------------------------- validation unit tests
describe("validateBookInput (unit)", () => {
  it("accepts a minimal valid payload", () => {
    const r = validateBookInput({ title: "T", author: "A" });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.value).toEqual({ title: "T", author: "A", year: null, isbn: null });
    }
  });

  it("trims whitespace on title and author", () => {
    const r = validateBookInput({ title: "  T  ", author: " A " });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.value.title).toBe("T");
      expect(r.value.author).toBe("A");
    }
  });

  it("rejects a negative year", () => {
    const r = validateBookInput({ title: "T", author: "A", year: -5 });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.details).toHaveProperty("year");
  });
});
