/// <reference types="vitest" />
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/server.js";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import type { Express } from "express";

let dbPath: string;
let close: () => void;
let app: Express;

function freshApp() {
  dbPath = path.join(
    fs.mkdtempSync(path.join(os.tmpdir(), "books-")),
    "test.db",
  );
  const result = createApp({ dbPath });
  app = result.app;
  close = result.close;
}

function cleanup() {
  close();
  try {
    fs.rmSync(path.dirname(dbPath), { recursive: true, force: true });
  } catch {
    /* ignore */
  }
}

describe("books API", () => {
  beforeEach(freshApp);
  afterEach(cleanup);

  describe("GET /health", () => {
    it("returns ok status", async () => {
      const res = await request(app).get("/health");
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: "ok" });
    });
  });

  describe("POST /books", () => {
    it("creates a book and returns 201", async () => {
      const res = await request(app).post("/books").send({
        title: "The Pragmatic Programmer",
        author: "Andy Hunt",
        year: 1999,
        isbn: "978-0201616224",
      });
      expect(res.status).toBe(201);
      expect(res.body.id).toBeGreaterThan(0);
      expect(res.body.title).toBe("The Pragmatic Programmer");
      expect(res.body.author).toBe("Andy Hunt");
      expect(res.body.year).toBe(1999);
      expect(res.body.isbn).toBe("978-0201616224");
      expect(res.body.created_at).toBeTruthy();
    });

    it("rejects when title is missing", async () => {
      const res = await request(app).post("/books").send({
        author: "Someone",
      });
      expect(res.status).toBe(422);
      expect(res.body.error).toBe("validation failed");
      const messages = res.body.issues.map(
        (i: { message: string }) => i.message,
      );
      expect(messages).toContain("title is required");
    });

    it("rejects when both title and author are missing", async () => {
      const res = await request(app).post("/books").send({});
      expect(res.status).toBe(422);
      expect(res.body.issues).toHaveLength(2);
    });

    it("accepts a book without year and isbn", async () => {
      const res = await request(app).post("/books").send({
        title: "Minimal",
        author: "Anon",
      });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
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
      expect(res.body.every((b: { author: string }) => b.author === "X")).toBe(
true,
      );
    });
  });

  describe("GET /books/:id", () => {
    it("returns a single book", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "Solo", author: "Z" });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("Solo");
    });

    it("returns 404 for unknown id", async () => {
      const res = await request(app).get("/books/9999");
      expect(res.status).toBe(404);
      expect(res.body.error).toBe("book not found");
    });

    it("rejects non-integer id", async () => {
      const res = await request(app).get("/books/abc");
      expect(res.status).toBe(400);
    });
  });

  describe("PUT /books/:id", () => {
    it("updates a book fully", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "Old", author: "OldA", year: 2000 });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: "New", author: "NewA", year: 2020, isbn: "111" });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("New");
      expect(res.body.author).toBe("NewA");
      expect(res.body.year).toBe(2020);
      expect(res.body.isbn).toBe("111");
      expect(res.body.updated_at).not.toBe(created.body.updated_at);
    });

    it("partially updates a book", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "T", author: "A", year: 2010 });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ year: 2024 });
      expect(res.status).toBe(200);
      expect(res.body.year).toBe(2024);
      expect(res.body.title).toBe("T");
      expect(res.body.author).toBe("A");
    });

    it("returns 404 for unknown id", async () => {
      const res = await request(app).put("/books/7777").send({ title: "x" });
      expect(res.status).toBe(404);
    });

    it("validates partial update input", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "T", author: "A" });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: "" });
      expect(res.status).toBe(422);
    });
  });

  describe("DELETE /books/:id", () => {
    it("deletes a book", async () => {
      const created = await request(app)
        .post("/books")
        .send({ title: "Bye", author: "X" });
      const del = await request(app).delete(`/books/${created.body.id}`);
      expect(del.status).toBe(204);
      const after = await request(app).get(`/books/${created.body.id}`);
      expect(after.status).toBe(404);
    });

    it("returns 404 when deleting missing book", async () => {
      const res = await request(app).delete("/books/4040");
      expect(res.status).toBe(404);
    });
  });

  describe("unknown routes", () => {
    it("returns 404 json", async () => {
      const res = await request(app).get("/nope");
      expect(res.status).toBe(404);
      expect(res.body.error).toContain("route not found");
    });
  });
});
