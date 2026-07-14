import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { testClient } from "hono/testing";
import { createApp } from "../src/app.js";
import { closeDatabase, openMemoryDatabase } from "../src/db.js";
import type { BooksDb } from "../src/db.js";

let db: BooksDb;

beforeEach(() => {
  db = openMemoryDatabase();
});

afterEach(() => {
  closeDatabase(db);
});

describe("GET /health", () => {
  it("returns ok status", async () => {
    const client = testClient(createApp(db));
    const res = await client.health.$get();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201", async () => {
    const client = testClient(createApp(db));
    const res = await client.books.$post({
      json: {
        title: "The Pragmatic Programmer",
        author: "Andy Hunt",
        year: 1999,
        isbn: "978-0201616224",
      },
    });
    expect(res.status).toBe(201);
    const body = await res.json();
    expect(body.title).toBe("The Pragmatic Programmer");
    expect(body.author).toBe("Andy Hunt");
    expect(body.year).toBe(1999);
    expect(body.isbn).toBe("978-0201616224");
    expect(body.id).toBeGreaterThan(0);
  });

  it("rejects missing title with 400", async () => {
    const client = testClient(createApp(db));
    const res = await client.books.$post({
      json: { author: "Someone" },
    });
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.errors.title).toBeDefined();
  });

  it("rejects empty author and missing title with 400", async () => {
    const client = testClient(createApp(db));
    const res = await client.books.$post({
      json: { title: "   ", author: "" },
    });
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.errors.title).toBeDefined();
    expect(body.errors.author).toBeDefined();
  });

  it("rejects non-object body with 400", async () => {
    const app = createApp(db);
    const res = await app.request("/books", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "not json",
    });
    expect(res.status).toBe(400);
  });
});

describe("GET /books", () => {
  it("lists created books", async () => {
    const client = testClient(createApp(db));
    await client.books.$post({ json: { title: "A", author: "Alice" } });
    await client.books.$post({ json: { title: "B", author: "Bob" } });
    const res = await client.books.$get();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toHaveLength(2);
    expect(body[0].title).toBe("A");
    expect(body[1].title).toBe("B");
  });

  it("filters by author", async () => {
    const client = testClient(createApp(db));
    await client.books.$post({ json: { title: "A", author: "Alice" } });
    await client.books.$post({ json: { title: "B", author: "Bob" } });
    await client.books.$post({ json: { title: "C", author: "Alice" } });
    const res = await client.books.$get({ query: { author: "Alice" } });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toHaveLength(2);
    expect(body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });
});

describe("GET /books/:id", () => {
  it("returns 404 for unknown id", async () => {
    const client = testClient(createApp(db));
    const res = await client.books[":id"].$get({ param: { id: "999" } });
    expect(res.status).toBe(404);
  });

  it("returns a book by id", async () => {
    const client = testClient(createApp(db));
    const created = await client.books.$post({
      json: { title: "X", author: "Y" },
    });
    const id = (await created.json()).id;
    const res = await client.books[":id"].$get({ param: { id: String(id) } });
    expect(res.status).toBe(200);
    expect((await res.json()).title).toBe("X");
  });
});

describe("PUT /books/:id", () => {
  it("updates fields and returns 200", async () => {
    const client = testClient(createApp(db));
    const created = await client.books.$post({
      json: { title: "Old", author: "OldAuth", year: 2000 },
    });
    const id = (await created.json()).id;
    const res = await client.books[":id"].$put({
      param: { id: String(id) },
      json: { title: "New", year: 2010 },
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.title).toBe("New");
    expect(body.author).toBe("OldAuth");
    expect(body.year).toBe(2010);
  });

  it("returns 404 for unknown id", async () => {
    const client = testClient(createApp(db));
    const res = await client.books[":id"].$put({
      param: { id: "404" },
      json: { title: "New" },
    });
    expect(res.status).toBe(404);
  });

  it("rejects invalid title with 400", async () => {
    const client = testClient(createApp(db));
    const created = await client.books.$post({
      json: { title: "T", author: "A" },
    });
    const id = (await created.json()).id;
    const res = await client.books[":id"].$put({
      param: { id: String(id) },
      json: { title: "" },
    });
    expect(res.status).toBe(400);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book and returns 204", async () => {
    const client = testClient(createApp(db));
    const created = await client.books.$post({
      json: { title: "T", author: "A" },
    });
    const id = (await created.json()).id;
    const res = await client.books[":id"].$delete({ param: { id: String(id) } });
    expect(res.status).toBe(204);
    const after = await client.books[":id"].$get({ param: { id: String(id) } });
    expect(after.status).toBe(404);
  });

  it("returns 404 for unknown id", async () => {
    const client = testClient(createApp(db));
    const res = await client.books[":id"].$delete({ param: { id: "777" } });
    expect(res.status).toBe(404);
  });
});
