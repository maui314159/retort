import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/server.js";

function app() {
  return createApp({ dbPath: ":memory:" });
}

describe("Health check", () => {
  it("GET /health returns 200 ok", async () => {
    const res = await request(app()).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("Books API CRUD", () => {
  let api: ReturnType<typeof app>;

  beforeEach(() => {
    api = app();
  });

  const validBook = {
    title: "The Pragmatic Programmer",
    author: "Andrew Hunt",
    year: 1999,
    isbn: "978-0201616224",
  };

  it("creates, fetches, lists, updates, and deletes a book", async () => {
    // Create
    const createRes = await request(api).post("/books").send(validBook);
    expect(createRes.status).toBe(201);
    expect(createRes.body).toMatchObject(validBook);
    expect(createRes.body.id).toBeGreaterThan(0);
    const id = createRes.body.id;

    // Get by id
    const getRes = await request(api).get(`/books/${id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body).toMatchObject(validBook);

    // List all
    const listRes = await request(api).get("/books");
    expect(listRes.status).toBe(200);
    expect(listRes.body).toHaveLength(1);

    // Update
    const updateRes = await request(api)
      .put(`/books/${id}`)
      .send({ year: 2000 });
    expect(updateRes.status).toBe(200);
    expect(updateRes.body.year).toBe(2000);
    expect(updateRes.body.title).toBe(validBook.title);

    // Delete
    const delRes = await request(api).delete(`/books/${id}`);
    expect(delRes.status).toBe(204);

    // Confirm gone
    const afterDel = await request(api).get(`/books/${id}`);
    expect(afterDel.status).toBe(404);
  });

  it("rejects creation without required title/author", async () => {
    const res = await request(api).post("/books").send({ year: 2020 });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation failed");
    expect(res.body.details.title).toBeDefined();
    expect(res.body.details.author).toBeDefined();
  });

  it("supports ?author= filter", async () => {
    await request(api).post("/books").send({ title: "A", author: "Alice" });
    await request(api).post("/books").send({ title: "B", author: "Bob" });
    await request(api).post("/books").send({ title: "C", author: "Alice" });

    const res = await request(api).get("/books?author=Alice");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });

  it("returns 404 for unknown book id", async () => {
    const res = await request(api).get("/books/9999");
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("Book not found");
  });

  it("returns 404 for unknown route", async () => {
    const res = await request(api).get("/unknown");
    expect(res.status).toBe(404);
  });
});
