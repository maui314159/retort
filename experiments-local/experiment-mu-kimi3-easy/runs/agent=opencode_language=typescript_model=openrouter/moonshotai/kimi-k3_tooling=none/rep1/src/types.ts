/** A book record as stored in the database and returned by the API. */
export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/** Validated fields used to create or replace a book. */
export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}
