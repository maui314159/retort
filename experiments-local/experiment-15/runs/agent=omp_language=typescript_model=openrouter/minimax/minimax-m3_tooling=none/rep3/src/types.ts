export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export type BookCreate = {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
};

export type BookUpdate = Partial<BookCreate>;
