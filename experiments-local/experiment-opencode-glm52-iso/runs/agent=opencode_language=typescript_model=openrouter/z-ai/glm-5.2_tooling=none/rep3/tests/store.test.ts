import { BookStore } from '../src/store';
import fs from 'fs';

function uniqueDbPath(): string {
  return `/tmp/books-unit-${Date.now()}-${Math.random().toString(36).slice(2)}.db`;
}

describe('BookStore', () => {
  let store: BookStore;

  beforeEach(() => {
    store = new BookStore(uniqueDbPath());
  });

  afterEach(() => {
    store.close();
  });

  it('inserts and retrieves a book', () => {
    const inserted = store.insert({
      title: 'Refactoring',
      author: 'Fowler',
      year: 1999,
      isbn: '123',
    });
    expect(inserted.id).toBeGreaterThan(0);
    const got = store.getById(inserted.id);
    expect(got?.title).toBe('Refactoring');
    expect(got?.isbn).toBe('123');
  });

  it('defaults year and isbn to null', () => {
    const inserted = store.insert({ title: 'T', author: 'A' });
    expect(inserted.year).toBeNull();
    expect(inserted.isbn).toBeNull();
  });

  it('lists books filtered by author', () => {
    store.insert({ title: 'A1', author: 'Alice' });
    store.insert({ title: 'A2', author: 'Alice' });
    store.insert({ title: 'B1', author: 'Bob' });
    const alice = store.list('Alice');
    expect(alice).toHaveLength(2);
    const all = store.list();
    expect(all).toHaveLength(3);
  });

  it('updates a book', () => {
    const inserted = store.insert({ title: 'Old', author: 'Old' });
    const updated = store.update(inserted.id, {
      title: 'New',
      author: 'New',
      year: 2001,
    });
    expect(updated?.title).toBe('New');
    expect(updated?.year).toBe(2001);
  });

  it('deletes a book', () => {
    const inserted = store.insert({ title: 'T', author: 'A' });
    const ok = store.delete(inserted.id);
    expect(ok).toBe(true);
    expect(store.getById(inserted.id)).toBeUndefined();
    expect(store.delete(inserted.id)).toBe(false);
  });
});
