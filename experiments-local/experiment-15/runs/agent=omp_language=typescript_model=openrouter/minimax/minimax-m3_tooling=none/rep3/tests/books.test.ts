import { afterEach, beforeEach, describe, expect, it } from "vitest";
import request from "supertest";
import type { Express } from "express";
import type { Db } from "../src/db.js";
import { createApp } from "../src/app.js";

let app: Express;
let db: Db;

beforeEach(() => {
  process.env.NODE_ENV = "test";
  const created = createApp();
  app = created.app;
  db = created.db;
  // Make sure tests start from an empty collection
  db.exec("DELETE FROM books; DELETE FROM sqlite_sequence WHERE name='books';");
});

afterEach(() => {
  db.close();
});

describe("GET /health", () => {
  it("returns ok status with db reachable", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");
    expect(res.body.db).toBe("ok");
    expect(typeof res.body.uptime_seconds).toBe("number");
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with the resource", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "978-0441172719" });

    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: expect.any(Number),
      title: "Dune",
      author: "Frank Herbert",
      year: 1965,
      isbn: "978-0441172719",
    });
    expect(typeof res.body.created_at).toBe("string");
    expect(typeof res.body.updated_at).toBe("string");
  });

  it("rejects missing title with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ author: "Anonymous" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("ValidationError");
  });

  it("rejects missing author with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Untitled" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("ValidationError");
  });

  it("rejects blank-only title with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "   ", author: "Anon" });

    expect(res.status).toBe(400);
  });
});

describe("GET /books", () => {
  it("returns an empty list initially", async () => {
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("lists all books and filters by author", async () => {
    await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert" });
    await request(app).post("/books").send({ title: "Children of Dune", author: "Frank Herbert" });
    await request(app).post("/books").send({ title: "Hyperion", author: "Dan Simmons" });

    const all = await request(app).get("/books");
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const herbert = await request(app).get("/books").query({ author: "Frank Herbert" });
    expect(herbert.status).toBe(200);
    expect(herbert.body).toHaveLength(2);
    expect(herbert.body.every((b: { author: string }) => b.author === "Frank Herbert")).toBe(true);
  });
});

describe("GET /books/:id", () => {
  it("returns a book by id", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Neuromancer", author: "William Gibson", year: 1984 });

    const id = created.body.id as number;
    const res = await request(app).get(`/books/${id}`);

    expect(res.status).toBe(200);
    expect(res.body.title).toBe("Neuromancer");
  });

  it("returns 404 for unknown id", async () => {
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("NotFound");
  });

  it("returns 400 for non-numeric id", async () => {
    const res = await request(app).get("/books/abc");
    expect(res.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("updates a book and returns the updated resource", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Old Title", author: "Author X" });
    const id = created.body.id as number;

    const updated = await request(app)
      .put(`/books/${id}`)
      .send({ title: "New Title", year: 2020 });

    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe("New Title");
    expect(updated.body.author).toBe("Author X"); // preserved
    expect(updated.body.year).toBe(2020);
  });

  it("returns 404 when updating a missing book", async () => {
    const res = await request(app)
      .put("/books/424242")
      .send({ title: "Whatever" });
    expect(res.status).toBe(404);
  });

  it("rejects an empty body with 400", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "T", author: "A" });
    const id = created.body.id as number;

    const res = await request(app).put(`/books/${id}`).send({});
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("ValidationError");
  });

  it("rejects setting title to blank with 400", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "T", author: "A" });
    const id = created.body.id as number;

    const res = await request(app).put(`/books/${id}`).send({ title: " " });
    expect(res.status).toBe(400);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes an existing book and returns 204", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Doomed", author: "X" });
    const id = created.body.id as number;

    const del = await request(app).delete(`/books/${id}`);
    expect(del.status).toBe(204);
    expect(del.text).toBe("");

    const after = await request(app).get(`/books/${id}`);
    expect(after.status).toBe(404);
  });

  it("returns 404 when deleting a missing book", async () => {
    const res = await request(app).delete("/books/7777");
    expect(res.status).toBe(404);
  });

  it("returns 400 for non-numeric id", async () => {
    const res = await request(app).delete("/books/not-a-number");
    expect(res.status).toBe(400);
  });
});
