import { z } from 'zod';

export const bookSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  author: z.string().min(1, 'Author is required'),
  year: z.number().int().min(1000).max(new Date().getFullYear()).optional().nullable(),
  isbn: z.string().min(10).max(20).optional().nullable(),
});

export type BookInput = z.infer<typeof bookSchema>;
