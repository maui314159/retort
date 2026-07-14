import { describe, it, expect, beforeEach } from "vitest";
import { createApp, type App } from "../src/app.js";
import { createDb } from "../src/db.js";
import type Database from "better-sqlite3";
import http from "node:http";
import type { AddressInfo } from "node:net";

describe("Book API", () => {
  let db: Database.Database;
  let app: App;
  let server: http.Server;
  let baseUrl: string;

  beforeEach(() => {
    db = createDb();
    app = createApp(db);
    server = http.createServer(app);
  });

  async function listen(): Promise<void> {
    const { promise, resolve } = Promise.withResolvers<void>();
    server.listen(0, () => resolve());
    await promise;
    const addr = server.address() as AddressInfo;
    baseUrl = `http://127.0.0.1:${addr.port}`;
  }

  async function close(): Promise<void> {
    const { promise, resolve } = Promise.withResolvers<void>();
    server.close(() => resolve());
    await promise;
  }

  async function fetch_(path: string, opts?: RequestInit): Promise<Response> {
    return globalThis.fetch(baseUrl + path, opts);
  }

  it("GET /health returns ok", async () => {
    await listen();
    const res = await fetch_("/health");
    expect(res.status).toBe(200);
    const body = (await res.json()) as { status: string };
    expect(body).toEqual({ status: "ok" });
    await close();
  });

  it("POST /books creates a book and GET /books lists it", async () => {
    await listen();

    const createRes = await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "The Hobbit",
        author: "J.R.R. Tolkien",
        year: 1937,
        isbn: "978-0261102217",
      }),
    });
    expect(createRes.status).toBe(201);
    const created = (await createRes.json()) as { id: number; title: string; author: string };
    expect(created.title).toBe("The Hobbit");
    expect(created.author).toBe("J.R.R. Tolkien");
    expect(created.id).toBeDefined();

    const listRes = await fetch_("/books");
    expect(listRes.status).toBe(200);
    const books = (await listRes.json()) as Array<{ title: string }>;
    expect(books).toHaveLength(1);
    expect(books[0].title).toBe("The Hobbit");

    await close();
  });

  it("GET /books?author= filters by author", async () => {
    await listen();

    await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Book A", author: "Alice" }),
    });
    await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Book B", author: "Bob" }),
    });

    const res = await fetch_("/books?author=Alice");
    const books = (await res.json()) as Array<{ author: string }>;
    expect(books).toHaveLength(1);
    expect(books[0].author).toBe("Alice");

    await close();
  });

  it("GET /books/:id returns a single book", async () => {
    await listen();

    const createRes = await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Dune", author: "Frank Herbert", year: 1965 }),
    });
    const created = (await createRes.json()) as { id: number };

    const getRes = await fetch_(`/books/${created.id}`);
    expect(getRes.status).toBe(200);
    const book = (await getRes.json()) as { title: string };
    expect(book.title).toBe("Dune");

    await close();
  });

  it("GET /books/:id returns 404 for missing book", async () => {
    await listen();
    const res = await fetch_("/books/9999");
    expect(res.status).toBe(404);
    await close();
  });

  it("PUT /books/:id updates a book", async () => {
    await listen();

    const createRes = await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Old Title", author: "Old Author" }),
    });
    const created = (await createRes.json()) as { id: number };

    const updateRes = await fetch_(`/books/${created.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "New Title", author: "New Author", year: 2024 }),
    });
    expect(updateRes.status).toBe(200);
    const updated = (await updateRes.json()) as { title: string; author: string; year: number };
    expect(updated.title).toBe("New Title");
    expect(updated.author).toBe("New Author");
    expect(updated.year).toBe(2024);

    await close();
  });

  it("DELETE /books/:id deletes a book", async () => {
    await listen();

    const createRes = await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "To Delete", author: "Author" }),
    });
    const created = (await createRes.json()) as { id: number };

    const deleteRes = await fetch_(`/books/${created.id}`, { method: "DELETE" });
    expect(deleteRes.status).toBe(204);

    const getRes = await fetch_(`/books/${created.id}`);
    expect(getRes.status).toBe(404);

    await close();
  });

  it("POST /books rejects missing title or author", async () => {
    await listen();

    const noTitle = await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author: "Author" }),
    });
    expect(noTitle.status).toBe(400);

    const noAuthor = await fetch_("/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Title" }),
    });
    expect(noAuthor.status).toBe(400);

    await close();
  });

  it("PUT /books/:id returns 404 for missing book", async () => {
    await listen();

    const res = await fetch_("/books/9999", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "X", author: "Y" }),
    });
    expect(res.status).toBe(404);

    await close();
  });

  it("DELETE /books/:id returns 404 for missing book", async () => {
    await listen();

    const res = await fetch_("/books/9999", { method: "DELETE" });
    expect(res.status).toBe(404);

    await close();
  });
});
