import { ValidatedBookInput, BookInput } from "./types";

/**
 * Input validation for book payloads.
 *
 * Rules:
 *  - `title` is required and must be a non-empty string.
 *  - `author` is required and must be a non-empty string.
 *  - `year` is optional; when present it must be an integer >= 0 (or null).
 *  - `isbn` is optional; when present it must be a string (or null).
 *
 * Returns a normalised `ValidatedBookInput` on success or an object whose
 * `details` map describes every field that failed validation.
 */
export function validateBookInput(
  input: BookInput
): { ok: true; value: ValidatedBookInput } | { ok: false; details: Record<string, string> } {
  const details: Record<string, string> = {};

  // --- title ---
  if (input.title === undefined || input.title === null) {
    details.title = "title is required";
  } else if (typeof input.title !== "string") {
    details.title = "title must be a string";
  } else if (input.title.trim().length === 0) {
    details.title = "title must not be empty";
  }

  // --- author ---
  if (input.author === undefined || input.author === null) {
    details.author = "author is required";
  } else if (typeof input.author !== "string") {
    details.author = "author must be a string";
  } else if (input.author.trim().length === 0) {
    details.author = "author must not be empty";
  }

  // --- year (optional) ---
  if (input.year !== undefined && input.year !== null) {
    if (typeof input.year === "number" && Number.isInteger(input.year)) {
      if (input.year < 0) {
        details.year = "year must not be negative";
      }
    } else if (typeof input.year === "string" && /^-?\d+$/.test(input.year.trim())) {
      // accept numeric strings, validated below
    } else {
      details.year = "year must be an integer";
    }
  }

  // --- isbn (optional) ---
  if (input.isbn !== undefined && input.isbn !== null && typeof input.isbn !== "string") {
    details.isbn = "isbn must be a string";
  }

  if (Object.keys(details).length > 0) {
    return { ok: false, details };
  }

  // Normalise the (now known-valid) fields.
  const year = normaliseYear(input.year);
  const isbn =
    input.isbn === undefined || input.isbn === null ? null : String(input.isbn).trim() || null;

  return {
    ok: true,
    value: {
      title: (input.title as string).trim(),
      author: (input.author as string).trim(),
      year,
      isbn,
    },
  };
}

function normaliseYear(value: unknown): number | null {
  if (value === undefined || value === null) return null;
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed === "") return null;
    const parsed = Number(trimmed);
    return Number.isInteger(parsed) ? parsed : null;
  }
  return null;
}
