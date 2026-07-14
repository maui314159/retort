import request from "supertest";
import { createApp } from "../src/app";
import type { Express } from "express";
import type { BookStore } from "../src/bookStore";

describe("Books API", () => {
  let app: Express;
  let store: BookStore;

  beforeEach(() => {
    app = createApp();
    store = app.locals.store as BookStore;
  });

  afterEach(() => {
    store.close();
  });

  describe("GET /health", () => {
    it("returns ok status", async () => {
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
        id: expect.any(Number),
        title: "Dune",
        author: "Frank Herbert",
        year: 1965,
        isbn: "9780441172719",
      });
    });

    it("rejects when title is missing", async () => {
      const res = await request(app)
        .post("/books")
        .send({ author: "Frank Herbert" });

      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/title/i);
    });

    it("rejects when author is missing", async () => {
      const res = await request(app)
        .post("/books")
        .send({ title: "Dune" });

      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/author/i);
    });

    it("rejects an invalid year", async () => {
      const res = await request(app)
        .post("/books")
        .send({ title: "Dune", author: "Herbert", year: "not-a-year" });

      expect(res.status).toBe(400);
    });
  });

  describe("GET /books", () => {
    beforeEach(() => {
      store.create({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: null });
      store.create({ title: "1984", author: "George Orwell", year: 1949, isbn: null });
      store.create({ title: "The Martian", author: "Andy Weir", year: 2011, isbn: null });
    });

    it("lists all books", async () => {
      const res = await request(app).get("/books");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(3);
    });

    it("filters by author", async () => {
      const res = await request(app).get("/books?author=Frank Herbert");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(1);
      expect(res.body[0].title).toBe("Dune");
    });
  });

  describe("GET /books/:id", () => {
    it("returns a single book", async () => {
      const created = store.create({ title: "Dune", author: "Herbert", year: 1965, isbn: null });
      const res = await request(app).get(`/books/${created.id}`);
      expect(res.status).toBe(200);
      expect(res.body.id).toBe(created.id);
    });

    it("returns 404 for missing book", async () => {
      const res = await request(app).get("/books/9999");
      expect(res.status).toBe(404);
    });

    it("returns 400 for invalid id", async () => {
      const res = await request(app).get("/books/abc");
      expect(res.status).toBe(400);
    });
  });

  describe("PUT /books/:id", () => {
    it("updates fields on an existing book", async () => {
      const created = store.create({ title: "Dune", author: "Herbert", year: 1965, isbn: null });
      const res = await request(app)
        .put(`/books/${created.id}`)
        .send({ year: 1966, isbn: "9780441172719" });

      expect(res.status).toBe(200);
      expect(res.body.year).toBe(1966);
      expect(res.body.isbn).toBe("9780441172719");
      expect(res.body.title).toBe("Dune");
    });

    it("returns 404 for missing book", async () => {
      const res = await request(app).put("/books/9999").send({ title: "X" });
      expect(res.status).toBe(404);
    });
  });

  describe("DELETE /books/:id", () => {
    it("deletes an existing book", async () => {
      const created = store.create({ title: "Dune", author: "Herbert", year: 1965, isbn: null });
      const res = await request(app).delete(`/books/${created.id}`);
      expect(res.status).toBe(204);
      const getRes = await request(app).get(`/books/${created.id}`);
      expect(getRes.status).toBe(404);
    });

    it("returns 404 for missing book", async () => {
      const res = await request(app).delete("/books/9999");
      expect(res.status).toBe(404);
    });
  });
});
