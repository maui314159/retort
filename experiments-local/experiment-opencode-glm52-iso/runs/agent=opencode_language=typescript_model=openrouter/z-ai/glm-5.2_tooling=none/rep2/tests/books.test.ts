import request from "supertest";
import fs from "fs";
import path from "path";
import os from "os";

process.env.BOOK_DB_PATH = path.join(
  os.tmpdir(),
  `books-test-${process.pid}-${Date.now()}.db`
);

import app from "../src/server";
import { getDb, resetDb } from "../src/db";

function seed(book: {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}) {
  const db = getDb();
  const info = db
    .prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    )
    .run(book.title, book.author, book.year ?? null, book.isbn ?? null);
  return info.lastInsertRowid as number;
}

afterAll(() => {
  resetDb();
  try {
    fs.unlinkSync(process.env.BOOK_DB_PATH as string);
  } catch {
    // ignore
  }
});

describe("Health check", () => {
  it("GET /health returns 200 and { status: 'ok' }", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("Books CRUD", () => {
  it("creates, fetches, lists, updates, and deletes a book", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719" })
      .expect(201);
    expect(created.body.id).toBeDefined();
    expect(created.body.title).toBe("Dune");

    const id = created.body.id;
    const fetched = await request(app).get(`/books/${id}`).expect(200);
    expect(fetched.body.title).toBe("Dune");
    expect(fetched.body.author).toBe("Frank Herbert");

    const listed = await request(app).get("/books").expect(200);
    expect(Array.isArray(listed.body)).toBe(true);
    expect(listed.body.length).toBeGreaterThanOrEqual(1);

    const updated = await request(app)
      .put(`/books/${id}`)
      .send({ title: "Dune (Updated)", author: "Frank Herbert", year: 1965, isbn: "9780441172719" })
      .expect(200);
    expect(updated.body.title).toBe("Dune (Updated)");

    await request(app).delete(`/books/${id}`).expect(204);
    await request(app).get(`/books/${id}`).expect(404);
  });

  it("filters by author via query param", async () => {
    seed({ title: "Book A", author: "Alice" });
    seed({ title: "Book B", author: "Bob" });
    seed({ title: "Book C", author: "Alice" });

    const filtered = await request(app)
      .get("/books")
      .query({ author: "Alice" })
      .expect(200);
    expect(filtered.body.length).toBeGreaterThanOrEqual(2);
    expect(filtered.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });
});

describe("Validation", () => {
  it("rejects missing title and author with 400", async () => {
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(Array.isArray(res.body.errors)).toBe(true);
    expect(res.body.errors.length).toBe(2);
  });

  it("rejects PUT to a non-existent id with 404", async () => {
    await request(app)
      .put("/books/999999")
      .send({ title: "X", author: "Y" })
      .expect(404);
  });
});
