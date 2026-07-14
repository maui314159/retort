import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import { createMemoryDb } from "../src/db.js";
import { createApp } from "../src/server.js";
import type { Database as SqliteDb } from "better-sqlite3";

function setupApp(): { app: ReturnType<typeof createApp> } {
  const db: SqliteDb = createMemoryDb();
  const app = createApp(db);
  return { app };
}

const validBook = {
  title: "The Pragmatic Programmer",
  author: "Andrew Hunt",
  year: 1999,
  isbn: "978-0201616224",
};

describe("health check", () => {
  it("GET /health returns ok", async () => {
    const { app } = setupApp();
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("book collection API", () => {
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    ({ app } = setupApp());
  });

  it("creates, lists, gets, updates, and deletes a book (happy path)", async () => {
    // create
    const createRes = await request(app).post("/books").send(validBook);
    expect(createRes.status).toBe(201);
    expect(createRes.body.id).toBe(1);
    expect(createRes.body.title).toBe(validBook.title);
    expect(createRes.body.author).toBe(validBook.author);
    expect(createRes.body.year).toBe(validBook.year);
    expect(createRes.body.isbn).toBe(validBook.isbn);

    const id = createRes.body.id;

    // list
    const listRes = await request(app).get("/books");
    expect(listRes.status).toBe(200);
    expect(listRes.body).toHaveLength(1);
    expect(listRes.body[0].id).toBe(id);

    // get by id
    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body.title).toBe(validBook.title);

    // update (partial)
    const updateRes = await request(app).put(`/books/${id}`).send({ year: 2005 });
    expect(updateRes.status).toBe(200);
    expect(updateRes.body.year).toBe(2005);
    expect(updateRes.body.title).toBe(validBook.title); // unchanged

    // delete
    const delRes = await request(app).delete(`/books/${id}`);
    expect(delRes.status).toBe(204);

    // subsequent get is 404
    const afterDel = await request(app).get(`/books/${id}`);
    expect(afterDel.status).toBe(404);
  });

  it("rejects creation without required title and author", async () => {
    const res = await request(app).post("/books").send({ year: 2020, isbn: "123" });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("validation_failed");
    const fields = res.body.details.map((d: { field: string }) => d.field);
    expect(fields).toContain("title");
    expect(fields).toContain("author");
  });

  it("rejects empty-string title and author", async () => {
    const res = await request(app).post("/books").send({ title: "   ", author: "" });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("validation_failed");
  });

  it("rejects invalid year", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "T", author: "A", year: "not-a-number" });
    expect(res.status).toBe(400);
    expect(res.body.details.some((d: { field: string }) => d.field === "year")).toBe(true);
  });

  it("filters books by author", async () => {
    await request(app).post("/books").send({ title: "Book A", author: "Alice", year: 2001 });
    await request(app).post("/books").send({ title: "Book B", author: "Bob", year: 2002 });
    await request(app).post("/books").send({ title: "Book C", author: "Alice", year: 2003 });

    const all = await request(app).get("/books");
    expect(all.body).toHaveLength(3);

    const alice = await request(app).get("/books?author=Alice");
    expect(alice.status).toBe(200);
    expect(alice.body).toHaveLength(2);
    expect(alice.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);

    const bob = await request(app).get("/books").query({ author: "Bob" });
    expect(bob.body).toHaveLength(1);
    expect(bob.body[0].title).toBe("Book B");
  });

  it("returns 404 for unknown book id on GET, PUT, DELETE", async () => {
    expect((await request(app).get("/books/999")).status).toBe(404);
    expect((await request(app).put("/books/999").send({ title: "X" })).status).toBe(404);
    expect((await request(app).delete("/books/999")).status).toBe(404);
  });

  it("rejects PUT with no updatable fields", async () => {
    const createRes = await request(app).post("/books").send(validBook);
    const id = createRes.body.id;
    const res = await request(app).put(`/books/${id}`).send({});
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("validation_failed");
  });

  it("rejects unknown routes with 404", async () => {
    const res = await request(app).get("/nonexistent");
    expect(res.status).toBe(404);
  });

  it("rejects malformed JSON body", async () => {
    const res = await request(app)
      .post("/books")
      .set("Content-Type", "application/json")
      .send("{ not json");
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("invalid_json");
  });
});
