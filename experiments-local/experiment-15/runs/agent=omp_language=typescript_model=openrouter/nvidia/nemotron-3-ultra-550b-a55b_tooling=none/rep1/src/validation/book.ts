import { z } from 'zod';
import type { CreateBookInput, UpdateBookInput } from '../types/book';

export const createBookSchema: z.ZodType<CreateBookInput> = z.object({
  title: z.string().min(1, 'Title is required').trim(),
  author: z.string().min(1, 'Author is required').trim(),
  year: z.number().int().min(1000).max(9999).nullable().optional(),
  isbn: z.string().trim().nullable().optional(),
});

export const updateBookSchema: z.ZodType<UpdateBookInput> = z.object({
  title: z.string().min(1, 'Title is required').trim().optional(),
  author: z.string().min(1, 'Author is required').trim().optional(),
  year: z.number().int().min(1000).max(9999).nullable().optional(),
  isbn: z.string().trim().nullable().optional(),
}).refine((data) => Object.keys(data).length > 0, {
  message: 'At least one field must be provided for update',
});

export const bookIdSchema = z.coerce.number().int().positive('Book ID must be a positive integer');

export const authorFilterSchema = z.string().trim().optional();