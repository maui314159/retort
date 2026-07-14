import { CreateBookInput, UpdateBookInput } from './types';

export function validateCreateBook(body: unknown): { valid: true; data: CreateBookInput } | { valid: false; error: string } {
  if (typeof body !== 'object' || body === null) {
    return { valid: false, error: 'Request body must be an object' };
  }

  const input = body as Record<string, unknown>;

  if (typeof input.title !== 'string' || input.title.trim().length === 0) {
    return { valid: false, error: 'Title is required and must be a non-empty string' };
  }

  if (typeof input.author !== 'string' || input.author.trim().length === 0) {
    return { valid: false, error: 'Author is required and must be a non-empty string' };
  }

  const data: CreateBookInput = {
    title: input.title.trim(),
    author: input.author.trim(),
  };

  if ('year' in input) {
    if (input.year !== null && (typeof input.year !== 'number' || !Number.isInteger(input.year))) {
      return { valid: false, error: 'Year must be a valid integer or null' };
    }
    data.year = input.year;
  }

  if ('isbn' in input) {
    if (input.isbn !== null && typeof input.isbn !== 'string') {
      return { valid: false, error: 'ISBN must be a string or null' };
    }
    data.isbn = input.isbn;
  }

  return { valid: true, data };
}

export function validateUpdateBook(body: unknown): { valid: true; data: UpdateBookInput } | { valid: false; error: string } {
  if (typeof body !== 'object' || body === null) {
    return { valid: false, error: 'Request body must be an object' };
  }

  const input = body as Record<string, unknown>;
  const data: UpdateBookInput = {};

  if ('title' in input) {
    if (typeof input.title !== 'string' || input.title.trim().length === 0) {
      return { valid: false, error: 'Title must be a non-empty string' };
    }
    data.title = input.title.trim();
  }

  if ('author' in input) {
    if (typeof input.author !== 'string' || input.author.trim().length === 0) {
      return { valid: false, error: 'Author must be a non-empty string' };
    }
    data.author = input.author.trim();
  }

  if ('year' in input) {
    if (input.year !== null && (typeof input.year !== 'number' || !Number.isInteger(input.year))) {
      return { valid: false, error: 'Year must be a valid integer or null' };
    }
    data.year = input.year;
  }

  if ('isbn' in input) {
    if (input.isbn !== null && typeof input.isbn !== 'string') {
      return { valid: false, error: 'ISBN must be a string or null' };
    }
    data.isbn = input.isbn;
  }

  return { valid: true, data };
}
