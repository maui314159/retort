import { z } from "zod";

export const bookCreateSchema = z
  .object({
    title: z.string().min(1, "title is required").max(500),
    author: z.string().min(1, "author is required").max(500),
    year: z.number().int().min(0).max(9999).optional().nullable(),
    isbn: z.string().max(50).optional().nullable(),
  })
  .strict();

export const bookUpdateSchema = z
  .object({
    title: z.string().min(1).max(500).optional(),
    author: z.string().min(1).max(500).optional(),
    year: z.number().int().min(0).max(9999).optional().nullable(),
    isbn: z.string().max(50).optional().nullable(),
  })
  .strict();

export type BookCreate = z.infer<typeof bookCreateSchema>;
export type BookUpdate = z.infer<typeof bookUpdateSchema>;
