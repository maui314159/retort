package com.example.books;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Pure unit-level validation tests: no Spring context, no DB.
 * Verifies the constraints declared on {@link Book} directly.
 */
class BookValidationTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void initValidator() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void closeValidator() {
        factory.close();
    }

    @Test
    void validBookHasNoViolations() {
        Book b = new Book(1L, "Dune", "Frank Herbert", 1965, "0441172717");
        Set<ConstraintViolation<Book>> violations = validator.validate(b);
        assertThat(violations).isEmpty();
    }

    @Test
    void missingTitleIsRejected() {
        Book b = new Book(null, null, "Frank Herbert", 1965, null);
        Set<ConstraintViolation<Book>> violations = validator.validate(b);

        assertThat(violations).extracting(v -> v.getPropertyPath().toString())
                .contains("title");
    }

    @Test
    void missingAuthorIsRejected() {
        Book b = new Book(null, "Dune", null, 1965, null);
        Set<ConstraintViolation<Book>> violations = validator.validate(b);

        assertThat(violations).extracting(v -> v.getPropertyPath().toString())
                .contains("author");
    }

    @Test
    void blankFieldsAreRejected() {
        Book b = new Book(null, "  ", "", 1965, null);
        Set<ConstraintViolation<Book>> violations = validator.validate(b);

        assertThat(violations).extracting(v -> v.getPropertyPath().toString())
                .contains("title", "author");
    }

    @Test
    void yearMustBePositive() {
        Book b = new Book(null, "Dune", "Frank Herbert", 0, null);
        Set<ConstraintViolation<Book>> violations = validator.validate(b);

        assertThat(violations).extracting(v -> v.getPropertyPath().toString())
                .contains("year");
    }

    @Test
    void nullYearAndIsbnAreAllowed() {
        Book b = new Book(null, "Dune", "Frank Herbert", null, null);
        Set<ConstraintViolation<Book>> violations = validator.validate(b);
        assertThat(violations).isEmpty();
    }
}
