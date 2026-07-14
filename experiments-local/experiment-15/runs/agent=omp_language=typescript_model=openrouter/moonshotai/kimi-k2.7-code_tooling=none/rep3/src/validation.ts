import { CreateBookInput, UpdateBookInput, CreateBookValidationResult, UpdateBookValidationResult } from './types';

export function validateCreateBookInput(body: unknown): CreateBookValidationResult {
  if (!body || typeof body !== 'object') {
    return { valid: false, error: { error: 'Request body must be an object' } };
  }

  const input = body as Record<string, unknown>;

  if (typeof input.title !== 'string' || input.title.trim().length === 0) {
    return { valid: false, error: { error: 'title is required and must be a non-empty string' } };
  }

  if (typeof input.author !== 'string' || input.author.trim().length === 0) {
    return { valid: false, error: { error: 'author is required and must be a non-empty string' } };
  }

  const data: CreateBookInput = {
    title: input.title.trim(),
    author: input.author.trim(),
  };

  if (input.year !== undefined) {
    if (!Number.isInteger(input.year) || typeof input.year !== 'number') {
      return { valid: false, error: { error: 'year must be an integer' } };
    }
    data.year = input.year;
  }

  if (input.isbn !== undefined) {
    if (typeof input.isbn !== 'string') {
      return { valid: false, error: { error: 'isbn must be a string' } };
    }
    data.isbn = input.isbn.trim() || null;
  }

  return { valid: true, data };
}

export function validateUpdateBookInput(body: unknown): UpdateBookValidationResult {
  if (!body || typeof body !== 'object') {
    return { valid: false, error: { error: 'Request body must be an object' } };
  }

  const input = body as Record<string, unknown>;
  const data: UpdateBookInput = {};

  if (input.title !== undefined) {
    if (typeof input.title !== 'string' || input.title.trim().length === 0) {
      return { valid: false, error: { error: 'title must be a non-empty string' } };
    }
    data.title = input.title.trim();
  }

  if (input.author !== undefined) {
    if (typeof input.author !== 'string' || input.author.trim().length === 0) {
      return { valid: false, error: { error: 'author must be a non-empty string' } };
    }
    data.author = input.author.trim();
  }

  if (input.year !== undefined) {
    if (!Number.isInteger(input.year) || typeof input.year !== 'number') {
      return { valid: false, error: { error: 'year must be an integer' } };
    }
    data.year = input.year;
  }

  if (input.isbn !== undefined) {
    if (typeof input.isbn !== 'string') {
      return { valid: false, error: { error: 'isbn must be a string' } };
    }
    data.isbn = input.isbn.trim() || null;
  }

  if (Object.keys(data).length === 0) {
    return { valid: false, error: { error: 'At least one field must be provided for update' } };
  }

  return { valid: true, data };
}
