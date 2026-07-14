import { describe, it, expect, beforeEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/server.js";

function freshApp() {
  return createApp();
}

describe("Health check", () => {
  it("GET /health returns 200 ok", async () => {
    const { app } = freshApp();
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("Books CRUD", () => {
  let app: ReturnType<typeof freshApp>["app"];

  beforeEach(() => {
    const created = freshApp();
    app = created.app;
  });

  it("creates, lists, fetches, updates, and deletes a book", async () => {
    const createRes = await request(app)
      .post("/books")
      .send({ title: "Clean Code", author: "Robert C. Martin", year: 2008, isbn: "978-0132350884" });
    expect(createRes.status).toBe(201);
    expect(createRes.body).toMatchObject({
      title: "Clean Code",
      author: "Robert C. Martin",
      year: 2008,
      isbn: "978-0132350884",
    });
    const id = createRes.body.id;
    expect(id).toBeTruthy();

    const listRes = await request(app).get("/books");
    expect(listRes.status).toBe(200);
    expect(listRes.body).toHaveLength(1);

    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body.id).toBe(id);

    const updateRes = await request(app)
      .put(`/books/${id}`)
      .send({ title: "Clean Code 2nd", author: "Robert C. Martin", year: 2020, isbn: null });
    expect(updateRes.status).toBe(200);
    expect(updateRes.body.title).toBe("Clean Code 2nd");
    expect(updateRes.body.isbn).toBeNull();

    const delRes = await request(app).delete(`/books/${id}`);
    expect(delRes.status).toBe(204);

    const after = await request(app).get(`/books/${id}`);
    expect(after.status).toBe(404);
  });
});

describe("Input validation", () => {
  it("rejects creation without title and author", async () => {
    const { app } = freshApp();
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toHaveLength(2);
    const fields = res.body.errors.map((e: { field: string }) => e.field).sort();
    expect(fields).toEqual(["author", "title"]);
  });

  it("rejects empty strings", async () => {
    const { app } = freshApp();
    const res = await request(app).post("/books").send({ title: "   ", author: "" });
    expect(res.status).toBe(400);
  });
});

describe("Author filter", () => {
  it("filters books by author", async () => {
    const { app } = freshApp();
    await request(app).post("/books").send({ title: "A", author: "Alice" });
    await request(app).post("/books").send({ title: "B", author: "Bob" });
    await request(app).post("/books").send({ title: "C", author: "Alice" });

    const res = await request(app).get("/books?author=Alice");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === "Alice")).toBe(true);
  });
});

describe("Not found handling", () => {
  it("returns 404 for unknown id on GET, PUT, DELETE", async () => {
    const { app } = freshApp();
    const id = "does-not-exist";
    expect((await request(app).get(`/books/${id}`)).status).toBe(404);
    expect(
      (
        await request(app).put(`/books/${id}`).send({ title: "X", author: "Y" })
      ).status
    ).toBe(404);
    expect((await request(app).delete(`/books/${id}`)).status).toBe(404);
  });
});
