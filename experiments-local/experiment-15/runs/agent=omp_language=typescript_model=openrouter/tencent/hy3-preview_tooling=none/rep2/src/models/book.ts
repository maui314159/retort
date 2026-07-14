export interface Book {
  id: number;
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

export type NewBook = Omit<Book, 'id'>;
export type UpdateBook = Partial<Omit<Book, 'id'>>;
