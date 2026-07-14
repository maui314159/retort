package com.example.books;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import java.nio.file.Files;

import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:sqlite::memory:",
        "spring.sql.init.mode=always"
})
class BookApiIntegrationTest {

    @Autowired private WebApplicationContext context;
    @Autowired private JdbcTemplate jdbc;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.webAppContextSetup(context).build();
        jdbc.update("DELETE FROM book");
    }

    @Test
    @DisplayName("Health endpoint returns UP")
    void healthReturnsUp() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    @DisplayName("Full CRUD lifecycle: create, read, update, delete")
    void fullCrudLifecycle() throws Exception {
        // Create
        String body = "{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"0441172717\"}";
        mvc.perform(post("/books")
                        .contentType("application/json")
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(header().exists("Location"))
                .andExpect(jsonPath("$.id").value(greaterThan(0)))
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.author").value("Frank Herbert"))
                .andExpect(jsonPath("$.year").value(1965))
                .andExpect(jsonPath("$.isbn").value("0441172717"));

        // Read single
        mvc.perform(get("/books/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune"));

        // List
        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)));

        // Update
        mvc.perform(put("/books/1")
                        .contentType("application/json")
                        .content("{\"title\":\"Dune (2nd ed.)\",\"author\":\"Frank Herbert\",\"year\":1969,\"isbn\":\"0441172717\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune (2nd ed.)"))
                .andExpect(jsonPath("$.year").value(1969));

        // Delete
        mvc.perform(delete("/books/1"))
                .andExpect(status().isNoContent());

        // Now 404
        mvc.perform(get("/books/1"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    @DisplayName("Filter books by author query parameter")
    void filterByAuthor() throws Exception {
        mvc.perform(post("/books").contentType("application/json")
                        .content("{\"title\":\"Dune\",\"author\":\"Frank Herbert\"}"))
                .andExpect(status().isCreated());
        mvc.perform(post("/books").contentType("application/json")
                        .content("{\"title\":\"Foundation\",\"author\":\"Isaac Asimov\"}"))
                .andExpect(status().isCreated());
        mvc.perform(post("/books").contentType("application/json")
                        .content("{\"title\":\"Children of Dune\",\"author\":\"Frank Herbert\"}"))
                .andExpect(status().isCreated());

        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)));

        mvc.perform(get("/books").param("author", "Frank Herbert"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].author").value("Frank Herbert"))
                .andExpect(jsonPath("$[1].author").value("Frank Herbert"));

        mvc.perform(get("/books").param("author", "Unknown"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    @Test
    @DisplayName("Validation rejects missing title or author; rejects missing body")
    void validationEnforced() throws Exception {
        // Missing author
        mvc.perform(post("/books").contentType("application/json")
                        .content("{\"title\":\"No Author\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.message").value(org.hamcrest.Matchers.containsString("author")));

        // Missing title
        mvc.perform(post("/books").contentType("application/json")
                        .content("{\"author\":\"Anon\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value(org.hamcrest.Matchers.containsString("title")));

        // Both blank
        mvc.perform(post("/books").contentType("application/json")
                        .content("{\"title\":\"\",\"author\":\"\"}"))
                .andExpect(status().isBadRequest());

        // Malformed JSON
        mvc.perform(post("/books").contentType("application/json")
                        .content("{not json"))
                .andExpect(status().isBadRequest());

        // Year too small
        mvc.perform(post("/books").contentType("application/json")
                        .content("{\"title\":\"x\",\"author\":\"y\",\"year\":0}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value(org.hamcrest.Matchers.containsString("year")));
    }

    @Test
    @DisplayName("Unknown book id returns 404 on get, put, and delete")
    void unknownIdReturns404() throws Exception {
        mvc.perform(get("/books/9999"))
                .andExpect(status().isNotFound());
        mvc.perform(put("/books/9999").contentType("application/json")
                        .content("{\"title\":\"x\",\"author\":\"y\"}"))
                .andExpect(status().isNotFound());
        mvc.perform(delete("/books/9999"))
                .andExpect(status().isNotFound());
    }
}
