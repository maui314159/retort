import { test, expect, describe } from "bun:test";
import { validateBook } from "../src/validation.ts";

describe("validateBook (create)", () => {
  test("valid full input has no errors", () => {
    const errors = validateBook({
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "978-0261103283",
    });
    expect(errors).toEqual([]);
  });

  test("missing title is rejected", () => {
    const errors = validateBook({ author: "Tolkien", year: 1937, isbn: null });
    expect(errors).toHaveLength(1);
    expect(errors[0].field).toBe("title");
  });

  test("missing author is rejected", () => {
    const errors = validateBook({ title: "The Hobbit", year: 1937, isbn: null });
    expect(errors).toHaveLength(1);
    expect(errors[0].field).toBe("author");
  });

  test("empty string title is rejected", () => {
    const errors = validateBook({ title: "   ", author: "Tolkien", year: 1937, isbn: null });
    expect(errors.some((e) => e.field === "title")).toBe(true);
  });

  test("non-integer year is rejected", () => {
    const errors = validateBook({ title: "T", author: "A", year: 19.5, isbn: null });
    expect(errors.some((e) => e.field === "year")).toBe(true);
  });

  test("negative year is rejected", () => {
    const errors = validateBook({ title: "T", author: "A", year: -1, isbn: null });
    expect(errors.some((e) => e.field === "year")).toBe(true);
  });

  test("year out of range is rejected", () => {
    const errors = validateBook({ title: "T", author: "A", year: 10000, isbn: null });
    expect(errors.some((e) => e.field === "year")).toBe(true);
  });

  test("null year and isbn are allowed", () => {
    const errors = validateBook({ title: "T", author: "A", year: null, isbn: null });
    expect(errors).toEqual([]);
  });
});

describe("validateBook (partial update)", () => {
  test("omitting title and author is allowed", () => {
    const errors = validateBook({ year: 2000 }, true);
    expect(errors).toEqual([]);
  });

  test("present but empty title is still rejected", () => {
    const errors = validateBook({ title: "" }, true);
    expect(errors.some((e) => e.field === "title")).toBe(true);
  });

  test("present but empty author is still rejected", () => {
    const errors = validateBook({ author: "" }, true);
    expect(errors.some((e) => e.field === "author")).toBe(true);
  });
});
