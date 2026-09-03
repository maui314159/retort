import { expect } from "chai";
import { BookStore, ValidationError } from "../src/store";

describe("BookStore", () => {
  it("create requires title and author", () => {
    const store = new BookStore(":memory:");
    expect(() => store.create({ title: "", author: "x" })).to.throw(
      ValidationError
    );
    expect(() => store.create({ title: "x", author: "" })).to.throw(
      ValidationError
    );
  });

  it("update mutates an existing book", () => {
    const store = new BookStore(":memory:");
    const created = store.create({ title: "T", author: "A", year: 1 });
    const updated = store.update(created.id, {
      title: "T2",
      author: "A2",
    });
    expect(updated?.title).to.equal("T2");
    expect(updated?.author).to.equal("A2");
  });

  it("delete returns false for missing id", () => {
    const store = new BookStore(":memory:");
    expect(store.delete(123)).to.equal(false);
  });
});
