/**
 * Shared test world: a singleton holding the dataset, the last query
 * result, and a small set of assertion helpers used across step
 * definitions. The dataset is loaded once per worker.
 */

const { loadDataset } = require('../../dist/data/loader.js');

class World {
  constructor() {
    this.snap = loadDataset();
    this.lastResult = undefined;
    this.lastError = undefined;
  }

  /** Run a callback and capture the result or thrown error. */
  capture(fn) {
    this.lastError = undefined;
    try {
      this.lastResult = fn();
    } catch (err) {
      this.lastError = err;
      this.lastResult = undefined;
    }
    return this.lastResult;
  }
}

module.exports = { World };
