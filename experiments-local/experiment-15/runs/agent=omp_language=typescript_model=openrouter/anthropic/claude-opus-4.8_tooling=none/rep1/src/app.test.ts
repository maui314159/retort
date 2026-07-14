import { test } from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { createApp } from "./app";
import { BookStore } from "./db";

function freshApp() {
  const store = new BookStore(":memory:");
  return createApp(store);
}

test("GET /health returns ok", async () => {
  const res = await request(freshApp()).get("/health");
  assert.equal(res.status, 200);
  assert.deepEqual(res.body, { status: "ok" });
});

test("POST /books creates a book and returns 201 with id", async () => {
  const app = freshApp();
  const res = await request(app)
    .post("/books")
    .send({ title: "Dune", author: "Herbert", year: 1965, isbn: "111" });
  assert.equal(res.status, 201);
  assert.equal(res.body.title, "Dune");
  assert.equal(res.body.author, "Herbert");
  assert.equal(res.body.year, 1965);
  assert.equal(res.body.isbn, "111");
  assert.ok(Number.isInteger(res.body.id));
});

test("POST /books rejects missing title/author with 400", async () => {
  const app = freshApp();
  const res = await request(app).post("/books").send({ year: 2000 });
  assert.equal(res.status, 400);
  assert.ok(Array.isArray(res.body.errors));
  assert.equal(res.body.errors.length, 2);
});

test("GET /books lists all and filters by author", async () => {
  const app = freshApp();
  await request(app).post("/books").send({ title: "A", author: "Alice" });
  await request(app).post("/books").send({ title: "B", author: "Bob" });
  await request(app).post("/books").send({ title: "C", author: "Alice" });

  const all = await request(app).get("/books");
  assert.equal(all.status, 200);
  assert.equal(all.body.length, 3);

  const filtered = await request(app).get("/books").query({ author: "Alice" });
  assert.equal(filtered.status, 200);
  assert.equal(filtered.body.length, 2);
  assert.ok(filtered.body.every((b: { author: string }) => b.author === "Alice"));
});

test("GET /books/:id returns one book or 404", async () => {
  const app = freshApp();
  const created = await request(app)
    .post("/books")
    .send({ title: "Solo", author: "X" });
  const id = created.body.id;

  const found = await request(app).get(`/books/${id}`);
  assert.equal(found.status, 200);
  assert.equal(found.body.title, "Solo");

  const missing = await request(app).get("/books/99999");
  assert.equal(missing.status, 404);

  const bad = await request(app).get("/books/abc");
  assert.equal(bad.status, 400);
});

test("PUT /books/:id updates an existing book", async () => {
  const app = freshApp();
  const created = await request(app)
    .post("/books")
    .send({ title: "Old", author: "Auth", year: 1990 });
  const id = created.body.id;

  const updated = await request(app)
    .put(`/books/${id}`)
    .send({ title: "New", author: "Auth", year: 2000, isbn: "222" });
  assert.equal(updated.status, 200);
  assert.equal(updated.body.title, "New");
  assert.equal(updated.body.year, 2000);
  assert.equal(updated.body.isbn, "222");

  const missing = await request(app)
    .put("/books/99999")
    .send({ title: "Nope", author: "Auth" });
  assert.equal(missing.status, 404);

  const invalid = await request(app).put(`/books/${id}`).send({ title: "" });
  assert.equal(invalid.status, 400);
});

test("DELETE /books/:id removes a book and 404s after", async () => {
  const app = freshApp();
  const created = await request(app)
    .post("/books")
    .send({ title: "Temp", author: "Auth" });
  const id = created.body.id;

  const del = await request(app).delete(`/books/${id}`);
  assert.equal(del.status, 204);

  const after = await request(app).get(`/books/${id}`);
  assert.equal(after.status, 404);

  const delAgain = await request(app).delete(`/books/${id}`);
  assert.equal(delAgain.status, 404);
});
