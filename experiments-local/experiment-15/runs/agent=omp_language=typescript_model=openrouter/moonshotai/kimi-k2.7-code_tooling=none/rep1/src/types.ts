import { z } from "zod";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export const bookSchema = z.object({
  title: z.string().min(1, "Title is required"),
  author: z.string().min(1, "Author is required"),
  year: z.number().int().optional(),
  isbn: z.string().optional(),
});

export type BookInput = z.infer<typeof bookSchema>;
