import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import type { DatabaseSync } from "node:sqlite";
import { createDatabase } from "../src/db.ts";
import { createBookServer } from "../src/server.ts";
import type { Book } from "../src/types.ts";

let db: DatabaseSync;
let server: Server;
let baseUrl: string;

async function postJson(
  path: string,
  body: unknown,
  method: "POST" | "PUT" = "POST",
): Promise<Response> {
  return fetch(`${baseUrl}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

before(async () => {
  db = createDatabase(":memory:");
  server = createBookServer(db);
  await new Promise<void>((resolve) =>
    server.listen(0, "127.0.0.1", () => resolve()),
  );
  const { port } = server.address() as AddressInfo;
  baseUrl = `http://127.0.0.1:${port}`;
});

after(async () => {
  await new Promise<void>((resolve, reject) =>
    server.close((err) => (err ? reject(err) : resolve())),
  );
  db.close();
});

test("GET /health returns 200 ok", async () => {
  const res = await fetch(`${baseUrl}/health`);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: "ok" });
});

test("POST /books creates a book and GET /books lists it", async () => {
  const created = await postJson("/books", {
    title: "The Hobbit",
    author: "J.R.R. Tolkien",
    year: 1937,
    isbn: "978-0-261-10221-7",
  });
  assert.equal(created.status, 201);
  const book = (await created.json()) as Book;
  assert.equal(book.title, "The Hobbit");
  assert.equal(book.author, "J.R.R. Tolkien");
  assert.equal(book.year, 1937);
  assert.equal(book.isbn, "978-0-261-10221-7");
  assert.ok(Number.isInteger(book.id) && book.id > 0);

  const list = await fetch(`${baseUrl}/books`);
  assert.equal(list.status, 200);
  const books = (await list.json()) as Book[];
  assert.ok(books.some((b) => b.id === book.id));
});

test("POST /books rejects a missing title or author with 400", async () => {
  const noTitle = await postJson("/books", { author: "Someone" });
  assert.equal(noTitle.status, 400);
  assert.match(((await noTitle.json()) as { error: string }).error, /title/);

  const noAuthor = await postJson("/books", { title: "Untitled" });
  assert.equal(noAuthor.status, 400);
  assert.match(((await noAuthor.json()) as { error: string }).error, /author/);

  const emptyTitle = await postJson("/books", { title: "  ", author: "X" });
  assert.equal(emptyTitle.status, 400);

  const badYear = await postJson("/books", {
    title: "T",
    author: "A",
    year: "nineteen",
  });
  assert.equal(badYear.status, 400);

  const invalidJson = await fetch(`${baseUrl}/books`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "not json{",
  });
  assert.equal(invalidJson.status, 400);
});

test("GET /books/:id returns a book, 404 when missing, 400 on bad id", async () => {
  const created = await postJson("/books", {
    title: "Dune",
    author: "Frank Herbert",
    year: 1965,
  });
  const book = (await created.json()) as Book;

  const found = await fetch(`${baseUrl}/books/${book.id}`);
  assert.equal(found.status, 200);
  assert.deepEqual(await found.json(), book);

  const missing = await fetch(`${baseUrl}/books/99999999`);
  assert.equal(missing.status, 404);

  const badId = await fetch(`${baseUrl}/books/abc`);
  assert.equal(badId.status, 400);
});

test("GET /books?author= filters by author", async () => {
  await postJson("/books", { title: "Book One", author: "Filter Author" });
  await postJson("/books", { title: "Book Two", author: "Filter Author" });
  await postJson("/books", { title: "Other Book", author: "Someone Else" });

  const res = await fetch(
    `${baseUrl}/books?author=${encodeURIComponent("Filter Author")}`,
  );
  assert.equal(res.status, 200);
  const books = (await res.json()) as Book[];
  assert.ok(books.length >= 2);
  assert.ok(books.every((b) => b.author === "Filter Author"));
});

test("PUT /books/:id replaces a book; 404 for unknown id", async () => {
  const created = await postJson("/books", {
    title: "Old Title",
    author: "Old Author",
  });
  const book = (await created.json()) as Book;

  const updated = await postJson(
    `/books/${book.id}`,
    { title: "New Title", author: "New Author", year: 2001, isbn: "123" },
    "PUT",
  );
  assert.equal(updated.status, 200);
  const updatedBook = (await updated.json()) as Book;
  assert.equal(updatedBook.id, book.id);
  assert.equal(updatedBook.title, "New Title");
  assert.equal(updatedBook.author, "New Author");
  assert.equal(updatedBook.year, 2001);
  assert.equal(updatedBook.isbn, "123");

  const missing = await postJson(
    "/books/99999999",
    { title: "T", author: "A" },
    "PUT",
  );
  assert.equal(missing.status, 404);

  const invalid = await postJson(
    `/books/${book.id}`,
    { author: "No title here" },
    "PUT",
  );
  assert.equal(invalid.status, 400);
});

test("DELETE /books/:id removes a book; 404 afterwards and for unknown id", async () => {
  const created = await postJson("/books", {
    title: "To Delete",
    author: "Author",
  });
  const book = (await created.json()) as Book;

  const del = await fetch(`${baseUrl}/books/${book.id}`, { method: "DELETE" });
  assert.equal(del.status, 204);

  const gone = await fetch(`${baseUrl}/books/${book.id}`);
  assert.equal(gone.status, 404);

  const delAgain = await fetch(`${baseUrl}/books/${book.id}`, {
    method: "DELETE",
  });
  assert.equal(delAgain.status, 404);
});
