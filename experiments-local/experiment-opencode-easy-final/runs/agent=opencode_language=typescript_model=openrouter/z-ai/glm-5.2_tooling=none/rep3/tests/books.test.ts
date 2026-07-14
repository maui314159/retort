import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { createApp } from "../src/server.js";
import { resetDbForTesting, closeDb } from "../src/db.js";
import type { Express } from "express";

let tmpDir: string;
let dbPath: string;

function setupFresh(): Express {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "bookapi-"));
  dbPath = path.join(tmpDir, "test.db");
  resetDbForTesting(dbPath);
  return createApp();
}

function cleanup(): void {
  closeDb();
  if (fs.existsSync(tmpDir)) {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

describe("Book API", () => {
  let app: Express;

  beforeEach(() => {
    app = setupFresh();
  });

  afterEach(() => {
    cleanup();
  });

  describe("GET /health", () => {
    it("returns 200 ok when DB is reachable", async () => {
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);
      expect(res.body.status).toBe("ok");
      expect(res.body.db).toBe("connected");
    });
  });

  describe("POST /books", () => {
    it("creates a book and returns 201 with the stored record", async () => {
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
      expect(typeof res.body.id).toBe("number");
    });

    it("returns 400 when title is missing", async () => {
      const res = await request(app).post("/books").send({ author: "Frank Herbert" });
      expect(res.status).toBe(400);
      expect(res.body.message).toBe("Validation failed");
      expect(Array.isArray(res.body.details)).toBe(true);
    });

    it("returns 400 when author is missing", async () => {
      const res = await request(app).post("/books").send({ title: "Dune" });
      expect(res.status).toBe(400);
      expect(res.body.message).toBe("Validation failed");
    });
  });

  describe("GET /books", () => {
    it("lists all books", async () => {
      await request(app).post("/books").send({ title: "A", author: "X" });
      await request(app).post("/books").send({ title: "B", author: "Y" });
      const res = await request(app).get("/books");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
    });

    it("filters by author", async () => {
      await request(app).post("/books").send({ title: "A", author: "X" });
      await request(app).post("/books").send({ title: "B", author: "Y" });
      await request(app).post("/books").send({ title: "C", author: "X" });
      const res = await request(app).get("/books?author=X");
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: { author: string }) => b.author === "X")).toBe(true);
    });
  });

  describe("GET /books/:id", () => {
    it("returns 404 for non-existent id", async () => {
      const res = await request(app).get("/books/9999");
      expect(res.status).toBe(404);
      expect(res.body.message).toBe("Book not found");
    });

    it("returns 400 for invalid id", async () => {
      const res = await request(app).get("/books/abc");
      expect(res.status).toBe(400);
    });
  });

  describe("PUT /books/:id", () => {
    it("updates an existing book", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "A", author: "X" });
      const id = created.body.id;
      const res = await request(app)
        .put(`/books/${id}`)
        .send({ title: "A2", year: 2001 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("A2");
      expect(res.body.year).toBe(2001);
      expect(res.body.author).toBe("X");
    });

    it("returns 404 when updating a missing book", async () => {
      const res = await request(app).put("/books/9999").send({ title: "X" });
      expect(res.status).toBe(404);
    });
  });

  describe("DELETE /books/:id", () => {
    it("deletes a book and returns 204", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "A", author: "X" });
      const id = created.body.id;
      const del = await request(app).delete(`/books/${id}`);
      expect(del.status).toBe(204);
      const after = await request(app).get(`/books/${id}`);
      expect(after.status).toBe(404);
    });

    it("returns 404 when deleting missing book", async () => {
      const res = await request(app).delete("/books/9999");
      expect(res.status).toBe(404);
    });
  });
});
