import type { BookInput, ValidationError } from "./types.ts";

/**
 * Validate book input for create/update operations.
 * Returns a list of validation errors (empty if valid).
 *
 * For updates (partial=true), only fields that are present are validated.
 * For creates (partial=false), title and author are required.
 */
export function validateBook(input: BookInput, partial = false): ValidationError[] {
  const errors: ValidationError[] = [];

  const hasTitle = input.title !== undefined;
  const hasAuthor = input.author !== undefined;

  if (!partial || hasTitle) {
    if (!hasTitle || typeof input.title !== "string" || input.title.trim() === "") {
      errors.push({ field: "title", message: "title is required and must be a non-empty string" });
    }
  }

  if (!partial || hasAuthor) {
    if (!hasAuthor || typeof input.author !== "string" || input.author.trim() === "") {
      errors.push({ field: "author", message: "author is required and must be a non-empty string" });
    }
  }

  if (input.year !== undefined && input.year !== null) {
    if (typeof input.year !== "number" || !Number.isInteger(input.year) || input.year < 0 || input.year > 9999) {
      errors.push({ field: "year", message: "year must be an integer between 0 and 9999" });
    }
  }

  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== "string" || input.isbn.trim() === "") {
      errors.push({ field: "isbn", message: "isbn must be a non-empty string or null" });
    }
  }

  return errors;
}
