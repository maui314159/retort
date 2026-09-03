import { describe, beforeEach, afterAll, it, expect } from "vitest";
import request from "supertest";
import { createApp } from "../src/app";
import { getDb, resetDb } from "../src/db";
import type { Express } from "express";

let app: Express;

beforeEach(() => {
  // Start each test with a fresh in-memory database
  resetDb();
  getDb(":memory:");
  app = createApp();
});

afterAll(() => {
  resetDb();
});

describe("Books API", () => {
  describe("POST /books", () => {
    it("should create a new book with valid input", async () => {
      const res = await request(app).post("/books").send({
        title: "The Great Gatsby",
        author: "F. Scott Fitzgerald",
        year: 1925,
        isbn: "978-0743273565",
      });

      expect(res.status).toBe(201);
      expect(res.body).toHaveProperty("id");
      expect(res.body.title).toBe("The Great Gatsby");
      expect(res.body.author).toBe("F. Scott Fitzgerald");
      expect(res.body.year).toBe(1925);
      expect(res.body.isbn).toBe("978-0743273565");
    });

    it("should return 400 when title is missing", async () => {
      const res = await request(app).post("/books").send({
        author: "Some Author",
        year: 2000,
      });

      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty("error", "Validation failed");
      expect(res.body.details).toHaveProperty("title");
    });

    it("should return 400 when author is missing", async () => {
      const res = await request(app).post("/books").send({
        title: "Some Title",
        year: 2000,
      });

      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty("error", "Validation failed");
      expect(res.body.details).toHaveProperty("author");
    });

    it("should create a book with only title and author", async () => {
      const res = await request(app).post("/books").send({
        title: "Minimal Book",
        author: "Minimal Author",
      });

      expect(res.status).toBe(201);
      expect(res.body.title).toBe("Minimal Book");
      expect(res.body.author).toBe("Minimal Author");
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe("GET /books", () => {
    it("should list all books", async () => {
      await request(app).post("/books").send({
        title: "Book A",
        author: "Author X",
        year: 2001,
      });
      await request(app).post("/books").send({
        title: "Book B",
        author: "Author Y",
        year: 2002,
      });

      const res = await request(app).get("/books");

      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
    });

    it("should filter books by author", async () => {
      await request(app).post("/books").send({
        title: "Book A",
        author: "Author X",
      });
      await request(app).post("/books").send({
        title: "Book B",
        author: "Author Y",
      });
      await request(app).post("/books").send({
        title: "Book C",
        author: "Author X",
      });

      const res = await request(app).get("/books?author=Author X");

      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(
        res.body.every((b: { author: string }) => b.author === "Author X")
      ).toBe(true);
    });

    it("should return empty array when no books exist", async () => {
      const res = await request(app).get("/books");

      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body).toHaveLength(0);
    });
  });

  describe("GET /books/:id", () => {
    it("should get a single book by id", async () => {
      const createRes = await request(app).post("/books").send({
        title: "Test Book",
        author: "Test Author",
        year: 2020,
      });

      const id = createRes.body.id;
      const res = await request(app).get(`/books/${id}`);

      expect(res.status).toBe(200);
      expect(res.body.id).toBe(id);
      expect(res.body.title).toBe("Test Book");
    });

    it("should return 404 for non-existent book", async () => {
      const res = await request(app).get("/books/9999");

      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty("error", "Book not found");
    });

    it("should return 400 for invalid id", async () => {
      const res = await request(app).get("/books/abc");

      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty("error", "Invalid book id");
    });
  });

  describe("PUT /books/:id", () => {
    it("should update a book", async () => {
      const createRes = await request(app).post("/books").send({
        title: "Old Title",
        author: "Old Author",
        year: 2000,
      });

      const id = createRes.body.id;
      const res = await request(app).put(`/books/${id}`).send({
        title: "New Title",
        author: "New Author",
        year: 2021,
      });

      expect(res.status).toBe(200);
      expect(res.body.title).toBe("New Title");
      expect(res.body.author).toBe("New Author");
      expect(res.body.year).toBe(2021);
    });

    it("should partially update a book", async () => {
      const createRes = await request(app).post("/books").send({
        title: "Keep This",
        author: "Keep Author",
        year: 2000,
        isbn: "123",
      });

      const id = createRes.body.id;
      const res = await request(app).put(`/books/${id}`).send({
        title: "Changed Title",
      });

      expect(res.status).toBe(200);
      expect(res.body.title).toBe("Changed Title");
      expect(res.body.author).toBe("Keep Author");
    });

    it("should return 404 when updating non-existent book", async () => {
      const res = await request(app).put("/books/9999").send({
        title: "Whatever",
      });

      expect(res.status).toBe(404);
    });
  });

  describe("DELETE /books/:id", () => {
    it("should delete a book", async () => {
      const createRes = await request(app).post("/books").send({
        title: "To Delete",
        author: "Some Author",
      });

      const id = createRes.body.id;
      const delRes = await request(app).delete(`/books/${id}`);

      expect(delRes.status).toBe(204);

      const getRes = await request(app).get(`/books/${id}`);
      expect(getRes.status).toBe(404);
    });

    it("should return 404 when deleting non-existent book", async () => {
      const res = await request(app).delete("/books/9999");

      expect(res.status).toBe(404);
    });
  });
});
