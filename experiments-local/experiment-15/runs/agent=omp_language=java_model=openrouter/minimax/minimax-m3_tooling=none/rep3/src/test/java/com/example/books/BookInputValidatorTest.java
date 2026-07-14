package com.example.books;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for {@link BookInputValidator}. Covers the documented
 * contract: title and author are required; year is optional but bounded.
 */
class BookInputValidatorTest {

    @Test
    @DisplayName("accepts a complete book")
    void acceptsCompleteBook() {
        Book b = new Book(null, "Title", "Author", 2024, "isbn");
        assertDoesNotThrow(() -> BookInputValidator.validateForCreate(b));
    }

    @Test
    @DisplayName("accepts a book with optional year and isbn omitted")
    void acceptsBookWithoutOptionalFields() {
        Book b = new Book(null, "Title", "Author", null, null);
        assertDoesNotThrow(() -> BookInputValidator.validateForCreate(b));
    }

    @Test
    @DisplayName("rejects missing title")
    void rejectsMissingTitle() {
        Book b = new Book(null, null, "Author", 2000, null);
        ValidationException ex = assertThrows(ValidationException.class,
                () -> BookInputValidator.validateForCreate(b));
        assertEquals("title is required", ex.getMessage());
    }

    @Test
    @DisplayName("rejects blank title and author")
    void rejectsBlankTitleAndAuthor() {
        Book b = new Book(null, "   ", "\t", 2000, null);
        ValidationException ex = assertThrows(ValidationException.class,
                () -> BookInputValidator.validateForCreate(b));
        // Both errors should be present, separated by a semicolon.
        String msg = ex.getMessage();
        assertEquals(true, msg.contains("title is required"));
        assertEquals(true, msg.contains("author is required"));
    }

    @Test
    @DisplayName("rejects out-of-range year")
    void rejectsOutOfRangeYear() {
        Book b = new Book(null, "T", "A", -1, null);
        ValidationException ex = assertThrows(ValidationException.class,
                () -> BookInputValidator.validateForCreate(b));
        assertEquals("year must be between 0 and 9999", ex.getMessage());
    }

    @Test
    @DisplayName("validateForUpdate shares the rules with create")
    void updateUsesSameRules() {
        Book b = new Book(null, null, null, null, null);
        assertThrows(ValidationException.class,
                () -> BookInputValidator.validateForUpdate(b));
    }
}
