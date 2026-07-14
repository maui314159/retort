import { describe, it, expect } from 'vitest';
import { BookStore } from '../src/db';

describe('BookStore (unit)', () => {
  it('persists and retrieves books via SQLite', () => {
    const store = new BookStore(':memory:');

    const created = store.create({ title: 'Refactoring', author: 'Martin Fowler', year: 1999 });
    expect(created.id).toBeGreaterThan(0);
    expect(created.title).toBe('Refactoring');

    const found = store.getById(created.id);
    expect(found).toBeDefined();
    expect(found?.author).toBe('Martin Fowler');

    // list filter
    store.create({ title: 'Another', author: 'Fowler' });
    const all = store.list();
    expect(all).toHaveLength(2);
    const fowlers = store.list('Fowler');
    expect(fowlers).toHaveLength(1);
    expect(fowlers[0].title).toBe('Another');

    // update
    const updated = store.update(created.id, { year: 2018 });
    expect(updated?.year).toBe(2018);

    // delete
    expect(store.delete(created.id)).toBe(true);
    expect(store.getById(created.id)).toBeUndefined();
    expect(store.delete(created.id)).toBe(false);

    store.close();
  });
});
