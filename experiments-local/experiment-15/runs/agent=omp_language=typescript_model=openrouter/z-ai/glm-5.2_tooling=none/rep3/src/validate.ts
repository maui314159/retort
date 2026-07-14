import type { BookInput, BookUpdate } from "./books.js";

/** Successful validation result carrying the coerced value. */
export interface ValidationOk<T> {
  ok: true;
  value: T;
}

/** Failed validation result. The errors map is keyed by field name. */
export interface ValidationFail {
  ok: false;
  errors: Record<string, string>;
}

export type ValidationResult<T> = ValidationOk<T> | ValidationFail;

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isYear(value: unknown): value is number | null {
  return (
    value === null ||
    (typeof value === "number" &&
      Number.isInteger(value) &&
      value >= 0 &&
      value <= 9999)
  );
}

function isIsbn(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

/** Validate a POST /books payload. title and author are required and non-empty. */
export function validateBookInput(
  input: unknown
): ValidationResult<BookInput> {
  const errors: Record<string, string> = {};
  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    return {
      ok: false,
      errors: { body: "expected a JSON object" },
    };
  }
  const raw = input as Record<string, unknown>;

  if (!isNonEmptyString(raw.title)) {
    errors.title = "title is required and must be a non-empty string";
  }
  if (!isNonEmptyString(raw.author)) {
    errors.author = "author is required and must be a non-empty string";
  }
  if (raw.year !== undefined && !isYear(raw.year)) {
    errors.year = "year must be an integer between 0 and 9999, or null";
  }
  if (raw.isbn !== undefined && !isIsbn(raw.isbn)) {
    errors.isbn = "isbn must be a string or null";
  }
  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  const value: BookInput = {
    title: (raw.title as string).trim(),
    author: (raw.author as string).trim(),
  };
  if (raw.year !== undefined) value.year = raw.year as number | null;
  if (raw.isbn !== undefined) value.isbn = raw.isbn as string | null;
  return { ok: true, value };
}

/** Validate a PUT /books/{id} payload. Provided fields follow the same rules as POST. */
export function validateBookUpdate(
  input: unknown
): ValidationResult<BookUpdate> {
  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    return {
      ok: false,
      errors: { body: "expected a JSON object" },
    };
  }
  const raw = input as Record<string, unknown>;
  const errors: Record<string, string> = {};

  if (raw.title !== undefined && !isNonEmptyString(raw.title)) {
    errors.title = "title must be a non-empty string";
  }
  if (raw.author !== undefined && !isNonEmptyString(raw.author)) {
    errors.author = "author must be a non-empty string";
  }
  if (raw.year !== undefined && !isYear(raw.year)) {
    errors.year = "year must be an integer between 0 and 9999, or null";
  }
  if (raw.isbn !== undefined && !isIsbn(raw.isbn)) {
    errors.isbn = "isbn must be a string or null";
  }
  if (Object.keys(raw).length === 0) {
    errors.body = "at least one field must be provided";
  }
  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  const value: BookUpdate = {};
  if (raw.title !== undefined) value.title = (raw.title as string).trim();
  if (raw.author !== undefined)
    value.author = (raw.author as string).trim();
  if (raw.year !== undefined) value.year = raw.year as number | null;
  if (raw.isbn !== undefined) value.isbn = raw.isbn as string | null;
  return { ok: true, value };
}
