export interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}

export interface ValidationError {
  field: string;
  message: string;
}

const isNonEmptyString = (v: unknown): v is string =>
  typeof v === "string" && v.trim().length > 0;

const isNullOrUndefined = (v: unknown): boolean =>
  v === null || v === undefined;

/** Validate a full create payload. Returns errors, or the normalized book. */
export function validateCreate(
  input: BookInput,
): { ok: true; book: NormalizedBook } | { ok: false; errors: ValidationError[] } {
  const errors: ValidationError[] = [];
  if (!isNonEmptyString(input.title)) {
    errors.push({ field: "title", message: "title is required and must be a non-empty string" });
  }
  if (!isNonEmptyString(input.author)) {
    errors.push({ field: "author", message: "author is required and must be a non-empty string" });
  }
  if (!isNullOrUndefined(input.year)) {
    if (typeof input.year !== "number" || !Number.isInteger(input.year) || input.year < 0) {
      errors.push({ field: "year", message: "year must be a non-negative integer" });
    }
  }
  if (!isNullOrUndefined(input.isbn)) {
    if (typeof input.isbn !== "string" || input.isbn.trim().length === 0) {
      errors.push({ field: "isbn", message: "isbn must be a non-empty string" });
    }
  }
  if (errors.length > 0) return { ok: false, errors };
  return {
    ok: true,
    book: {
      title: (input.title as string).trim(),
      author: (input.author as string).trim(),
      year: typeof input.year === "number" ? input.year : null,
      isbn: typeof input.isbn === "string" ? input.isbn.trim() : null,
    },
  };
}

export interface NormalizedBook {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/** Validate a partial update payload. At least one field must be present. */
export function validateUpdate(
  input: BookInput,
): { ok: true; book: Partial<NormalizedBook> } | { ok: false; errors: ValidationError[] } {
  const errors: ValidationError[] = [];
  const hasAny =
    !isNullOrUndefined(input.title) ||
    !isNullOrUndefined(input.author) ||
    !isNullOrUndefined(input.year) ||
    !isNullOrUndefined(input.isbn);

  if (!hasAny) {
    errors.push({ field: "body", message: "at least one field (title, author, year, isbn) must be provided" });
  }

  if (!isNullOrUndefined(input.title)) {
    if (!isNonEmptyString(input.title)) {
      errors.push({ field: "title", message: "title must be a non-empty string" });
    }
  }
  if (!isNullOrUndefined(input.author)) {
    if (!isNonEmptyString(input.author)) {
      errors.push({ field: "author", message: "author must be a non-empty string" });
    }
  }
  if (!isNullOrUndefined(input.year)) {
    if (typeof input.year !== "number" || !Number.isInteger(input.year) || input.year < 0) {
      errors.push({ field: "year", message: "year must be a non-negative integer" });
    }
  }
  if (!isNullOrUndefined(input.isbn)) {
    if (typeof input.isbn !== "string" || input.isbn.trim().length === 0) {
      errors.push({ field: "isbn", message: "isbn must be a non-empty string" });
    }
  }

  if (errors.length > 0) return { ok: false, errors };

  const book: Partial<NormalizedBook> = {};
  if (isNonEmptyString(input.title)) book.title = input.title.trim();
  if (isNonEmptyString(input.author)) book.author = input.author.trim();
  if (typeof input.year === "number") book.year = input.year;
  if (typeof input.isbn === "string") book.isbn = input.isbn.trim();
  return { ok: true, book };
}
