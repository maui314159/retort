package com.example.books;

import java.util.Set;
import java.util.stream.Collectors;

import com.example.books.dto.BookRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class BookRequestValidationTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void setUp() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void tearDown() {
        if (factory != null) {
            factory.close();
        }
    }

    @Test
    void blankTitleAndAuthorAreRejected() {
        BookRequest request = new BookRequest("", "", 1900, null);
        Set<String> invalidFields = validator.validate(request).stream()
                .map(v -> v.getPropertyPath().toString())
                .collect(Collectors.toSet());
        assertThat(invalidFields).contains("title", "author");
    }

    @Test
    void validRequestPasses() {
        BookRequest request = new BookRequest("Dune", "Frank Herbert", 1965, "9780441172719");
        assertThat(validator.validate(request)).isEmpty();
    }

    @Test
    void nullTitleAndAuthorAreRejected() {
        BookRequest request = new BookRequest(null, null, null, null);
        Set<String> invalidFields = validator.validate(request).stream()
                .map(v -> v.getPropertyPath().toString())
                .collect(Collectors.toSet());
        assertThat(invalidFields).contains("title", "author");
    }
}
