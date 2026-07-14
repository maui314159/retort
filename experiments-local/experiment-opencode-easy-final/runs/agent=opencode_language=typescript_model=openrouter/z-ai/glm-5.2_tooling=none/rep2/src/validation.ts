import { z } from "zod";

export const bookCreateSchema = z.object({
  title: z.string().min(1, "title is required"),
  author: z.string().min(1, "author is required"),
  year: z.number().int().min(0).max(9999).nullable().optional(),
  isbn: z.string().nullable().optional(),
});

export const bookUpdateSchema = bookCreateSchema.partial();

export type BookCreateInput = z.infer<typeof bookCreateSchema>;
export type BookUpdateInput = z.infer<typeof bookUpdateSchema>;
