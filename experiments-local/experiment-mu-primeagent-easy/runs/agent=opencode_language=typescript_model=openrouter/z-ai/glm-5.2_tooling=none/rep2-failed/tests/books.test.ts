import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import type { Express } from "express";
import { createApp } from "../src/app.js";
import { BookStore } from "../src/db.js";

describe("Books API (integration)", () => {
  let store: BookStore;
  let app: Express;

  beforeEach(() => {
    store = new BookStore(":memory:");
    app = createApp({ store }) as unknown as Express;
  });

  afterEach(() => {
    store.close();
  });

  it("creates a book and retrieves it by id", async () => {
    const createRes = await request(app)
      .post("/books")
      .send({ title: "1984", author: "George Orwell", year: 1949, isbn: "978-0451524935" });

    expect(createRes.status).toBe(201);
    expect(createRes.body.id).toBeDefined();
    expect(createRes.body.title).toBe("1984");
    expect(createRes.body.author).toBe("George Orwell");
    expect(createRes.body.year).toBe(1949);
    expect(createRes.body.isbn).toBe("978-0451524935");

    const getRes = await request(app).get(`/books/${createRes.body.id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body).toEqual(createRes.body);
  });

  it("rejects creation when title/author are missing", async () => {
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/i);
    expect(res.body.error).toMatch(/author/i);
  });

  it("lists all books and supports the author filter (case-insensitive)", async () => {
    await request(app)
      .post("/books")
      .send({ title: "Animal Farm", author: "George Orwell", year: 1945 });
    await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965 });

    const all = await request(app).get("/books");
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(2);

    const filtered = await request(app).get("/books?author=george");
    expect(filtered.status).toBe(200);
    expect(filtered.body).toHaveLength(1);
    expect(filtered.body[0].title).toBe("Animal Farm");
  });

  it("updates an existing book with PUT", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965 });

    const updated = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "Dune (Revised)", author: "Frank Herbert", year: 1965, isbn: "111" });

    expect(updated.status).toBe(200);
    expect(updated.body.id).toBe(created.body.id);
    expect(updated.body.title).toBe("Dune (Revised)");
    expect(updated.body.isbn).toBe("111");
  });

  it("returns 404 when updating a non-existent book", async () => {
    const res = await request(app)
      .put("/books/99999")
      .send({ title: "x", author: "y" });
    expect(res.status).toBe(404);
  });

  it("deletes a book and confirms it is gone", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "T", author: "A" });

    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);

    const after = await request(app).get(`/books/${created.body.id}`);
    expect(after.status).toBe(404);
  });

  it("returns 404 when deleting a non-existent book", async () => {
    const res = await request(app).delete("/books/99999");
    expect(res.status).toBe(404);
  });

  it("returns 404 for an unknown book id on GET", async () => {
    const res = await request(app).get("/books/99999");
    expect(res.status).toBe(404);
    expect(res.body.error).toMatch(/not found/i);
  });

  it("rejects malformed JSON with a 400", async () => {
    const res = await request(app)
      .post("/books")
      .set("Content-Type", "application/json")
      .send("{ not valid json");
    expect(res.status).toBe(400);
  });
});
