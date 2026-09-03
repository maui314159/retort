import { describe, it, expect } from "vitest";
import { validateBook } from "../src/validation.js";

describe("validateBook", () => {
  it("accepts a valid full payload", () => {
    const result = validateBook({
      title: "1984",
      author: "George Orwell",
      year: 1949,
      isbn: "978-0451524935",
    });
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.value).toEqual({
        title: "1984",
        author: "George Orwell",
        year: 1949,
        isbn: "978-0451524935",
      });
    }
  });

  it("requires a non-empty title and author", () => {
    const result = validateBook({ title: "  ", author: "" });
    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.errors.length).toBeGreaterThanOrEqual(2);
      expect(result.errors.join(" ")).toMatch(/title/i);
      expect(result.errors.join(" ")).toMatch(/author/i);
    }
  });

  it("trims whitespace from title and author", () => {
    const result = validateBook({ title: "  Dune  ", author: " Frank Herbert " });
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.value.title).toBe("Dune");
      expect(result.value.author).toBe("Frank Herbert");
    }
  });

  it("rejects non-integer years", () => {
    const result = validateBook({ title: "T", author: "A", year: 19.5 });
    expect(result.valid).toBe(false);
  });

  it("rejects years in the far future", () => {
    const result = validateBook({
      title: "T",
      author: "A",
      year: new Date().getFullYear() + 100,
    });
    expect(result.valid).toBe(false);
  });

  it("treats missing year/isbn as optional (null)", () => {
    const result = validateBook({ title: "T", author: "A" });
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.value.year).toBeNull();
      expect(result.value.isbn).toBeNull();
    }
  });

  it("rejects non-object bodies", () => {
    expect(validateBook(null).valid).toBe(false);
    expect(validateBook("hello").valid).toBe(false);
    expect(validateBook([1, 2, 3]).valid).toBe(false);
  });
});
