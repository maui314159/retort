import { test, expect, describe, beforeEach, afterEach } from "bun:test";
import { createBookStore } from "../src/db.ts";
import { createServer } from "../src/server.ts";
import type { BookStore } from "../src/db.ts";

async function req(
  base: string,
  method: string,
  path: string,
  body?: unknown
): Promise<{ status: number; body: unknown }> {
  const init: RequestInit = { method };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`${base}${path}`, init);
  let parsed: unknown = null;
  const text = await res.text();
  if (text !== "") {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }
  return { status: res.status, body: parsed };
}

describe("Books HTTP API", () => {
  let store: BookStore;
  let base: string;

  beforeEach(() => {
    store = createBookStore(":memory:");
    const server = createServer({ port: 0, store });
    base = `http://localhost:${server.port}`;
    // Stop server after each test
    afterEach(() => server.stop());
  });

  test("GET /health returns ok", async () => {
    const { status, body } = await req(base, "GET", "/health");
    expect(status).toBe(200);
    expect(body).toEqual({ status: "ok" });
  });

  test("POST /books creates a book and returns 201", async () => {
    const { status, body } = await req(base, "POST", "/books", {
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "978-0261103283",
    });
    expect(status).toBe(201);
    const book = body as { id: number; title: string; author: string; year: number; isbn: string };
    expect(book.id).toBeGreaterThan(0);
    expect(book.title).toBe("The Hobbit");
    expect(book.author).toBe("J.R.R. Tolkien");
    expect(book.year).toBe(1937);
  });

  test("POST /books without title returns 422", async () => {
    const { status, body } = await req(base, "POST", "/books", { author: "Tolkien", year: 1937 });
    expect(status).toBe(422);
    const err = body as { errors: { field: string }[] };
    expect(err.errors.some((e) => e.field === "title")).toBe(true);
  });

  test("POST /books without author returns 422", async () => {
    const { status, body } = await req(base, "POST", "/books", { title: "T", year: 1937 });
    expect(status).toBe(422);
    const err = body as { errors: { field: string }[] };
    expect(err.errors.some((e) => e.field === "author")).toBe(true);
  });

  test("POST /books with invalid JSON returns 400", async () => {
    const res = await fetch(`${base}/books`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "not json",
    });
    expect(res.status).toBe(400);
  });

  test("GET /books lists all books", async () => {
    await req(base, "POST", "/books", { title: "A", author: "X", year: 2000, isbn: null });
    await req(base, "POST", "/books", { title: "B", author: "Y", year: 2001, isbn: null });
    const { status, body } = await req(base, "GET", "/books");
    expect(status).toBe(200);
    expect(body as unknown[]).toHaveLength(2);
  });

  test("GET /books?author= filters by author", async () => {
    await req(base, "POST", "/books", { title: "A", author: "X", year: 2000, isbn: null });
    await req(base, "POST", "/books", { title: "B", author: "Y", year: 2001, isbn: null });
    await req(base, "POST", "/books", { title: "C", author: "X", year: 2002, isbn: null });
    const { status, body } = await req(base, "GET", "/books?author=X");
    expect(status).toBe(200);
    const books = body as { author: string }[];
    expect(books).toHaveLength(2);
    expect(books.every((b) => b.author === "X")).toBe(true);
  });

  test("GET /books/{id} returns the book", async () => {
    const created = await req(base, "POST", "/books", { title: "Dune", author: "Herbert", year: 1965, isbn: null });
    const id = (created.body as { id: number }).id;
    const { status, body } = await req(base, "GET", `/books/${id}`);
    expect(status).toBe(200);
    expect((body as { title: string }).title).toBe("Dune");
  });

  test("GET /books/{id} unknown returns 404", async () => {
    const { status } = await req(base, "GET", "/books/9999");
    expect(status).toBe(404);
  });

  test("PUT /books/{id} updates the book", async () => {
    const created = await req(base, "POST", "/books", { title: "Old", author: "A", year: 2000, isbn: null });
    const id = (created.body as { id: number }).id;
    const { status, body } = await req(base, "PUT", `/books/${id}`, { title: "New", author: "A", year: 2001, isbn: "123" });
    expect(status).toBe(200);
    expect((body as { title: string }).title).toBe("New");
    expect((body as { isbn: string }).isbn).toBe("123");
  });

  test("PUT /books/{id} partial update with only year", async () => {
    const created = await req(base, "POST", "/books", { title: "T", author: "A", year: 2000, isbn: null });
    const id = (created.body as { id: number }).id;
    const { status, body } = await req(base, "PUT", `/books/${id}`, { year: 2010 });
    expect(status).toBe(200);
    expect((body as { year: number }).year).toBe(2010);
    expect((body as { title: string }).title).toBe("T");
  });

  test("PUT /books/{id} unknown returns 404", async () => {
    const { status } = await req(base, "PUT", "/books/9999", { title: "X", author: "Y", year: null, isbn: null });
    expect(status).toBe(404);
  });

  test("DELETE /books/{id} removes the book", async () => {
    const created = await req(base, "POST", "/books", { title: "T", author: "A", year: null, isbn: null });
    const id = (created.body as { id: number }).id;
    const { status } = await req(base, "DELETE", `/books/${id}`);
    expect(status).toBe(200);
    const get = await req(base, "GET", `/books/${id}`);
    expect(get.status).toBe(404);
  });

  test("DELETE /books/{id} unknown returns 404", async () => {
    const { status } = await req(base, "DELETE", "/books/9999");
    expect(status).toBe(404);
  });

  test("unknown route returns 404", async () => {
    const { status } = await req(base, "GET", "/unknown");
    expect(status).toBe(404);
  });

  test("unsupported method on /books returns 405 with Allow header", async () => {
    const res = await fetch(`${base}/books`, { method: "PATCH" });
    expect(res.status).toBe(405);
    expect(res.headers.get("Allow")).toContain("GET");
  });
});
