import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { AddressInfo } from "node:net";
import { Server } from "node:http";
import { BookStore } from "../src/db";
import { createApp } from "../src/app";

let server: Server;
let store: BookStore;
let baseUrl: string;

before(async () => {
  store = new BookStore(":memory:");
  const app = createApp(store);
  await new Promise<void>((resolve) => {
    server = app.listen(0, () => resolve());
  });
  const { port } = server.address() as AddressInfo;
  baseUrl = `http://127.0.0.1:${port}`;
});

after(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
  store.close();
});

async function postBook(body: unknown): Promise<Response> {
  return fetch(`${baseUrl}/books`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

test("GET /health returns ok", async () => {
  const res = await fetch(`${baseUrl}/health`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.status, "ok");
});

test("POST /books creates a book and GET /books/{id} retrieves it", async () => {
  const res = await postBook({
    title: "The Hobbit",
    author: "J.R.R. Tolkien",
    year: 1937,
    isbn: "978-0-261-10221-7",
  });
  assert.equal(res.status, 201);
  const created = await res.json();
  assert.ok(Number.isInteger(created.id));
  assert.equal(created.title, "The Hobbit");
  assert.equal(created.author, "J.R.R. Tolkien");
  assert.equal(created.year, 1937);
  assert.equal(created.isbn, "978-0-261-10221-7");

  const getRes = await fetch(`${baseUrl}/books/${created.id}`);
  assert.equal(getRes.status, 200);
  const fetched = await getRes.json();
  assert.deepEqual(fetched, created);
});

test("POST /books rejects missing title or author with 400", async () => {
  const noTitle = await postBook({ author: "Someone" });
  assert.equal(noTitle.status, 400);
  const noAuthor = await postBook({ title: "Untitled" });
  assert.equal(noAuthor.status, 400);
  const neither = await postBook({});
  assert.equal(neither.status, 400);
  const body = await neither.json();
  assert.ok(Array.isArray(body.errors));
});

test("GET /books lists all books and supports ?author= filter", async () => {
  await postBook({ title: "Dune", author: "Frank Herbert", year: 1965 });
  await postBook({ title: "Dune Messiah", author: "Frank Herbert", year: 1969 });
  await postBook({ title: "Neuromancer", author: "William Gibson", year: 1984 });

  const allRes = await fetch(`${baseUrl}/books`);
  assert.equal(allRes.status, 200);
  const all = await allRes.json();
  assert.ok(all.length >= 3);

  const filterRes = await fetch(
    `${baseUrl}/books?author=${encodeURIComponent("Frank Herbert")}`
  );
  assert.equal(filterRes.status, 200);
  const filtered = await filterRes.json();
  assert.equal(filtered.length, 2);
  assert.ok(filtered.every((b: { author: string }) => b.author === "Frank Herbert"));
});

test("PUT /books/{id} updates a book", async () => {
  const createRes = await postBook({ title: "Draft", author: "Author" });
  const created = await createRes.json();

  const putRes = await fetch(`${baseUrl}/books/${created.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: "Final",
      author: "Author",
      year: 2001,
      isbn: "1234567890",
    }),
  });
  assert.equal(putRes.status, 200);
  const updated = await putRes.json();
  assert.equal(updated.id, created.id);
  assert.equal(updated.title, "Final");
  assert.equal(updated.year, 2001);
  assert.equal(updated.isbn, "1234567890");
});

test("PUT /books/{id} returns 404 for unknown id", async () => {
  const res = await fetch(`${baseUrl}/books/999999`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "X", author: "Y" }),
  });
  assert.equal(res.status, 404);
});

test("DELETE /books/{id} removes the book", async () => {
  const createRes = await postBook({ title: "Temp", author: "Temp Author" });
  const created = await createRes.json();

  const delRes = await fetch(`${baseUrl}/books/${created.id}`, {
    method: "DELETE",
  });
  assert.equal(delRes.status, 204);

  const getRes = await fetch(`${baseUrl}/books/${created.id}`);
  assert.equal(getRes.status, 404);

  const delAgain = await fetch(`${baseUrl}/books/${created.id}`, {
    method: "DELETE",
  });
  assert.equal(delAgain.status, 404);
});

test("GET /books/{id} returns 400 for non-integer id", async () => {
  const res = await fetch(`${baseUrl}/books/abc`);
  assert.equal(res.status, 400);
});
