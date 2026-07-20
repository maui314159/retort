import type { BookInput } from "./types.ts";

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; error: string };

function fail(error: string): ValidationResult {
  return { ok: false, error };
}

/**
 * Validate an untrusted JSON payload as book fields.
 * `title` and `author` are required non-empty strings;
 * `year` (integer) and `isbn` (string) are optional.
 */
export function parseBookInput(data: unknown): ValidationResult {
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    return fail("Request body must be a JSON object");
  }
  const obj = data as Record<string, unknown>;

  if (typeof obj.title !== "string" || obj.title.trim() === "") {
    return fail("title is required and must be a non-empty string");
  }
  if (typeof obj.author !== "string" || obj.author.trim() === "") {
    return fail("author is required and must be a non-empty string");
  }

  let year: number | null = null;
  if (obj.year !== undefined && obj.year !== null) {
    if (typeof obj.year !== "number" || !Number.isInteger(obj.year)) {
      return fail("year must be an integer");
    }
    year = obj.year;
  }

  let isbn: string | null = null;
  if (obj.isbn !== undefined && obj.isbn !== null) {
    if (typeof obj.isbn !== "string") {
      return fail("isbn must be a string");
    }
    isbn = obj.isbn;
  }

  return {
    ok: true,
    value: {
      title: obj.title.trim(),
      author: obj.author.trim(),
      year,
      isbn,
    },
  };
}
