import request from "supertest";
import type { Express } from "express";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createApp } from "../src/server.js";

describe("books API", () => {
  let app: Express;
  let closeDb: () => void;

  beforeEach(() => {
    const built = createApp({ dbPath: ":memory:", port: 0 });
    app = built.app;
    closeDb = () => built.db.close();
  });

  afterEach(() => {
    closeDb();
  });

  describe("GET /health", () => {
    it("returns ok status", async () => {
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);
      expect(res.body.status).toBe("ok");
      expect(res.body.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
  });

  describe("POST /books", () => {
    it("creates a book and returns 201 with the record", async () => {
      const res = await request(app).post("/books").send({
        title: "The Hobbit",
        author: "J.R.R. Tolkien",
        year: 1937,
        isbn: "978-0262352001",
      });
      expect(res.status).toBe(201);
      expect(res.body.id).toBe(1);
      expect(res.body.title).toBe("The Hobbit");
      expect(res.body.author).toBe("J.R.R. Tolkien");
      expect(res.body.year).toBe(1937);
      expect(res.body.isbn).toBe("978-0262352001");
    });

    it("rejects missing title with 400", async () => {
      const res = await request(app).post("/books").send({ author: "X" });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe("validation_failed");
    });

    it("rejects missing author with 400", async () => {
      const res = await request(app).post("/books").send({ title: "T" });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe("validation_failed");
    });

    it("accepts minimal payload with only title and author", async () => {
      const res = await request(app).post("/books").send({ title: "T", author: "A" });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe("GET /books", () => {
    it("returns an empty list initially", async () => {
      const res = await request(app).get("/books");
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it("returns all created books", async () => {
      await request(app).post("/books").send({ title: "A", author: "Alice" });
      await request(app).post("/books").send({ title: "B", author: "Bob" });
      const res = await request(app).get("/books");
      expect(res.body).toHaveLength(2);
    });

    it("filters by author", async () => {
      await request(app).post("/books").send({ title: "A", author: "Alice" });
      await request(app).post("/books").send({ title: "A2", author: "Alice" });
      await request(app).post("/books").send({ title: "B", author: "Bob" });
      const res = await request(app).get("/books?author=Alice");
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
    });
  });

  describe("GET /books/:id", () => {
    it("returns a single book", async () => {
      const created = await request(app).post("/books").send({ title: "T", author: "A" });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("T");
    });

    it("returns 404 for unknown id", async () => {
      const res = await request(app).get("/books/999");
      expect(res.status).toBe(404);
    });

    it("returns 400 for invalid id", async () => {
      const res = await request(app).get("/books/abc");
      expect(res.status).toBe(400);
    });
  });

  describe("PUT /books/:id", () => {
    it("updates a book and returns the updated record", async () => {
      const created = await request(app).post("/books").send({ title: "T", author: "A" });
      const res = await request(app).put(`/books/${created.body.id}`).send({ title: "T2" });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("T2");
      expect(res.body.author).toBe("A");
    });

    it("returns 404 for unknown id", async () => {
      const res = await request(app).put("/books/999").send({ title: "X" });
      expect(res.status).toBe(404);
    });

    it("returns 400 when no fields provided", async () => {
      const created = await request(app).post("/books").send({ title: "T", author: "A" });
      const res = await request(app).put(`/books/${created.body.id}`).send({});
      expect(res.status).toBe(400);
    });
  });

  describe("DELETE /books/:id", () => {
    it("deletes a book returning 204", async () => {
      const created = await request(app).post("/books").send({ title: "T", author: "A" });
      const res = await request(app).delete(`/books/${created.body.id}`);
      expect(res.status).toBe(204);
      const after = await request(app).get(`/books/${created.body.id}`);
      expect(after.status).toBe(404);
    });

    it("returns 404 for unknown id", async () => {
      const res = await request(app).delete("/books/999");
      expect(res.status).toBe(404);
    });
  });

  describe("unknown routes", () => {
    it("returns 404 for unknown paths", async () => {
      const res = await request(app).get("/nope");
      expect(res.status).toBe(404);
    });
  });
});
