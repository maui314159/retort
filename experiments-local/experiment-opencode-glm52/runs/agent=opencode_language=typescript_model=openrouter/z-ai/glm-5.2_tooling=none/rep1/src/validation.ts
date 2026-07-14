import type { BookInput } from "./db.js";

export interface ValidationError {
  field: string;
  message: string;
}

export function validateBook(
  body: unknown,
  { partial = false } = {}
): ValidationError[] {
  const errors: ValidationError[] = [];
  if (typeof body !== "object" || body === null) {
    errors.push({ field: "body", message: "Request body must be a JSON object" });
    return errors;
  }
  const b = body as Record<string, unknown>;

  if (!partial || b.title !== undefined) {
    if (typeof b.title !== "string" || b.title.trim() === "") {
      errors.push({ field: "title", message: "title is required and must be a non-empty string" });
    }
  }
  if (!partial || b.author !== undefined) {
    if (typeof b.author !== "string" || b.author.trim() === "") {
      errors.push({ field: "author", message: "author is required and must be a non-empty string" });
    }
  }
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== "number" || !Number.isInteger(b.year) || b.year < 0) {
      errors.push({ field: "year", message: "year must be a non-negative integer" });
    }
  }
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== "string" || b.isbn.trim() === "") {
      errors.push({ field: "isbn", message: "isbn must be a non-empty string if provided" });
    }
  }
  return errors;
}

export function normalizeBookInput(body: unknown): BookInput {
  const b = body as Record<string, unknown>;
  const trim = (v: unknown): string | undefined =>
    typeof v === "string" ? v.trim() : undefined;
  return {
    title: trim(b.title) ?? "",
    author: trim(b.author) ?? "",
    year:
      b.year === undefined || b.year === null ? null : Number(b.year),
    isbn:
      b.isbn === undefined || b.isbn === null
        ? null
        : typeof b.isbn === "string"
          ? b.isbn.trim()
          : null,
  };
}
