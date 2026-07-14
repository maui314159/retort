import { test, expect, describe, beforeEach } from "bun:test";
import { createBookStore } from "../src/db.ts";

describe("BookStore", () => {
  let store: ReturnType<typeof createBookStore>;

  beforeEach(() => {
    store = createBookStore(":memory:");
  });

  test("create and get by id", () => {
    const created = store.create({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "978-0441172719" });
    expect(created.id).toBeGreaterThan(0);
    expect(created.title).toBe("Dune");

    const fetched = store.get(created.id);
    expect(fetched).toEqual(created);
  });

  test("get unknown id returns null", () => {
    expect(store.get(9999)).toBeNull();
  });

  test("list returns all books ordered by id", () => {
    store.create({ title: "B", author: "Y", year: null, isbn: null });
    store.create({ title: "A", author: "X", year: null, isbn: null });
    const all = store.list();
    expect(all).toHaveLength(2);
    expect(all[0].title).toBe("B");
    expect(all[1].title).toBe("A");
  });

  test("list filters by author", () => {
    store.create({ title: "B", author: "Y", year: null, isbn: null });
    store.create({ title: "A", author: "X", year: null, isbn: null });
    store.create({ title: "C", author: "Y", year: null, isbn: null });
    const filtered = store.list("Y");
    expect(filtered).toHaveLength(2);
    expect(filtered.every((b) => b.author === "Y")).toBe(true);
  });

  test("update existing book", () => {
    const created = store.create({ title: "Old", author: "A", year: 2000, isbn: null });
    const updated = store.update(created.id, { title: "New", author: "A", year: 2001, isbn: "123" });
    expect(updated).not.toBeNull();
    expect(updated!.title).toBe("New");
    expect(updated!.year).toBe(2001);
    expect(updated!.isbn).toBe("123");
  });

  test("update unknown id returns null", () => {
    expect(store.update(9999, { title: "X", author: "Y", year: null, isbn: null })).toBeNull();
  });

  test("delete existing book", () => {
    const created = store.create({ title: "T", author: "A", year: null, isbn: null });
    expect(store.delete(created.id)).toBe(true);
    expect(store.get(created.id)).toBeNull();
  });

  test("delete unknown id returns false", () => {
    expect(store.delete(9999)).toBe(false);
  });
});
