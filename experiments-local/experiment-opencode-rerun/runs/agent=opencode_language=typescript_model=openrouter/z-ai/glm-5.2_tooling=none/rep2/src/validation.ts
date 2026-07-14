import type { BookInput } from "./db.js";

export interface ValidationError {
  field: string;
  message: string;
}

export function validateBook(
  input: Partial<BookInput>,
  requireAll = true
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (requireAll || input.title !== undefined) {
    if (
      input.title === undefined ||
      input.title === null ||
      input.title.trim() === ""
    ) {
      errors.push({ field: "title", message: "title is required" });
    }
  }

  if (requireAll || input.author !== undefined) {
    if (
      input.author === undefined ||
      input.author === null ||
      input.author.trim() === ""
    ) {
      errors.push({ field: "author", message: "author is required" });
    }
  }

  if (input.year !== undefined && input.year !== null) {
    if (
      typeof input.year !== "number" ||
      !Number.isFinite(input.year) ||
      !Number.isInteger(input.year) ||
      input.year < 0 ||
      input.year > new Date().getFullYear() + 5
    ) {
      errors.push({ field: "year", message: "year must be a valid integer" });
    }
  }

  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== "string" || input.isbn.trim() === "") {
      errors.push({ field: "isbn", message: "isbn must be a non-empty string" });
    }
  }

  return errors;
}
