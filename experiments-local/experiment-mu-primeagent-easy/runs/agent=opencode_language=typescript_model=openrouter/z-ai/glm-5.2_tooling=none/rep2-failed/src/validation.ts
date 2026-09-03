export interface ValidBookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type ValidationResult =
  | { valid: true; value: ValidBookInput }
  | { valid: false; errors: string[] };

const MAX_YEAR = new Date().getFullYear() + 1;

export function validateBook(input: unknown): ValidationResult {
  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    return { valid: false, errors: ["Request body must be a JSON object"] };
  }

  const obj = input as Record<string, unknown>;
  const errors: string[] = [];

  if (typeof obj.title !== "string" || obj.title.trim() === "") {
    errors.push("title is required and must be a non-empty string");
  }

  if (typeof obj.author !== "string" || obj.author.trim() === "") {
    errors.push("author is required and must be a non-empty string");
  }

  let year: number | null = null;
  if (obj.year !== undefined && obj.year !== null) {
    if (typeof obj.year !== "number" || !Number.isFinite(obj.year)) {
      errors.push("year must be a number");
    } else if (!Number.isInteger(obj.year)) {
      errors.push("year must be an integer");
    } else if (obj.year < 0 || obj.year > MAX_YEAR) {
      errors.push(`year must be between 0 and ${MAX_YEAR}`);
    } else {
      year = obj.year;
    }
  }

  let isbn: string | null = null;
  if (obj.isbn !== undefined && obj.isbn !== null) {
    if (typeof obj.isbn !== "string") {
      errors.push("isbn must be a string");
    } else {
      const trimmed = obj.isbn.trim();
      isbn = trimmed === "" ? null : trimmed;
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    value: {
      title: (obj.title as string).trim(),
      author: (obj.author as string).trim(),
      year,
      isbn,
    },
  };
}
