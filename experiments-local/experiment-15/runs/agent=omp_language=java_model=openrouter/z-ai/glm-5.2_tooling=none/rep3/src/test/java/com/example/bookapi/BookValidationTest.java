package com.example.bookapi;

import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Verifies input validation rules: title and author are required, year must be
 * positive when present.
 */
@SpringBootTest
@AutoConfigureMockMvc
class BookValidationTest {

    private static final Path DB_FILE;

    static {
        try {
            DB_FILE = Files.createTempFile("book-api-val", ".db");
            Files.deleteIfExists(DB_FILE);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> "jdbc:sqlite:" + DB_FILE);
    }

    @AfterAll
    static void cleanup() throws Exception {
        Files.deleteIfExists(DB_FILE);
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbc;

    @BeforeEach
    void resetTable() {
        jdbc.update("DELETE FROM books");
    }

    @Test
    void blankTitleIsRejected() throws Exception {
        String body = """
                {"title":"","author":"Asimov","year":1951}
                """;
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists());
    }

    @Test
    void missingAuthorIsRejected() throws Exception {
        String body = """
                {"title":"Foundation","year":1951}
                """;
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.author").exists());
    }

    @Test
    void negativeYearIsRejected() throws Exception {
        String body = """
                {"title":"Foundation","author":"Asimov","year":-5}
                """;
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.year").exists());
    }

    @Test
    void validMinimalBookIsCreated() throws Exception {
        // Only title and author are required; year and isbn may be omitted.
        String body = """
                {"title":"Foundation","author":"Asimov"}
                """;
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("Foundation"))
                .andExpect(jsonPath("$.author").value("Asimov"));
    }

    @Test
    void validationAlsoAppliesToUpdate() throws Exception {
        // Seed a book, then try an invalid update.
        String seed = """
                {"title":"Seed","author":"Author","year":2000}
                """;
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(seed))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        Long id = JsonTestSupport.idOf(created);

        String badUpdate = """
                {"title":"  ","author":"Author","year":2000}
                """;
        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(badUpdate))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists());
    }
}
