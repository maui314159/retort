import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { createDb } from "../src/db.js";
import type { Database as DB } from "better-sqlite3";

function freshApp(): { app: ReturnType<typeof createApp>; db: DB } {
  const db = createDb(":memory:");
  const app = createApp(db);
  return { app, db };
}

describe("GET /health", () => {
  it("returns 200 ok", async () => {
    const { app } = freshApp();
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("Books API", () => {
  let app: ReturnType<typeof createApp>;
  let db: DB;

  beforeEach(() => {
    ({ app, db } = freshApp());
  });

  it("creates, lists, gets, updates, and deletes a book", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "1984", author: "Orwell", year: 1949, isbn: "123" });
    expect(created.status).toBe(201);
    expect(created.body).toMatchObject({
      title: "1984",
      author: "Orwell",
      year: 1949,
      isbn: "123",
    });
    expect(typeof created.body.id).toBe("number");
    const id = created.body.id;

    const list = await request(app).get("/books");
    expect(list.status).toBe(200);
    expect(list.body).toHaveLength(1);
    expect(list.body[0].id).toBe(id);

    const one = await request(app).get(`/books/${id}`);
    expect(one.status).toBe(200);
    expect(one.body.title).toBe("1984");

    const updated = await request(app)
      .put(`/books/${id}`)
      .send({ title: "Nineteen Eighty-Four", author: "George Orwell" });
    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe("Nineteen Eighty-Four");
    expect(updated.body.author).toBe("George Orwell");

    const del = await request(app).delete(`/books/${id}`);
    expect(del.status).toBe(204);

    const after = await request(app).get(`/books/${id}`);
    expect(after.status).toBe(404);
  });

  it("validates required fields", async () => {
    const noTitle = await request(app).post("/books").send({ author: "X" });
    expect(noTitle.status).toBe(400);
    expect(noTitle.body.error).toMatch(/title/);

    const noAuthor = await request(app)
      .post("/books")
      .send({ title: "T" });
    expect(noAuthor.status).toBe(400);
    expect(noAuthor.body.error).toMatch(/author/);

    const empty = await request(app)
      .post("/books")
      .send({ title: "   ", author: "X" });
    expect(empty.status).toBe(400);
  });

  it("supports author filter", async () => {
    await request(app)
      .post("/books")
      .send({ title: "A", author: "Alice", year: 2000 });
    await request(app)
      .post("/books")
      .send({ title: "B", author: "Bob", year: 2001 });
    await request(app)
      .post("/books")
      .send({ title: "C", author: "Alice", year: 2002 });

    const alice = await request(app).get("/books?author=Alice");
    expect(alice.status).toBe(200);
    expect(alice.body).toHaveLength(2);
    expect(alice.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);

    const bob = await request(app).get("/books?author=Bob");
    expect(bob.body).toHaveLength(1);
    expect(bob.body[0].title).toBe("B");

    const none = await request(app).get("/books?author=Zed");
    expect(none.body).toHaveLength(0);
  });

  it("returns 404 for unknown ids", async () => {
    const get404 = await request(app).get("/books/9999");
    expect(get404.status).toBe(404);

    const put404 = await request(app)
      .put("/books/9999")
      .send({ title: "X", author: "Y" });
    expect(put404.status).toBe(404);

    const del404 = await request(app).delete("/books/9999");
    expect(del404.status).toBe(404);
  });
});
