/**
 * Tiny BDD helpers for Given/When/Then style test blocks.
 * Wraps vitest's describe/it while preserving the Gherkin-flavored structure
 * required by the spec ("Use BDD test scenarios").
 *
 * NOTE: function names are capitalized because vitest 4 reserves the
 * lowercase `given`/`when`/`then` identifiers for its native BDD collector.
 */

import { describe, it } from 'vitest';

/** A "Given" precondition block. Runs body in a describe. */
export function Given(label: string, fn: () => void): void {
  describe(`Given ${label}`, fn);
}

/** A "When" action block. Runs body in a describe. */
export function When(label: string, fn: () => void): void {
  describe(`When ${label}`, fn);
}

/** A "Then" assertion block. Wraps vitest's it. */
export function Then(label: string, fn: () => void | Promise<void>): void {
  it(`Then ${label}`, fn);
}
