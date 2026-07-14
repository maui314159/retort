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

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * End-to-end integration test exercising every endpoint through the full
 * Spring stack against an isolated SQLite file database.
 */
@SpringBootTest
@AutoConfigureMockMvc
class BookControllerIntegrationTest {

    private static final Path DB_FILE;

    static {
        try {
            DB_FILE = Files.createTempFile("book-api-it", ".db");
            Files.deleteIfExists(DB_FILE); // let SQLite create it fresh
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
    void createThenGetReturnsBook() throws Exception {
        String body = """
                {"title":"The Hobbit","author":"Tolkien","year":1937,"isbn":"978-0261102217"}
                """;
        String location = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("The Hobbit"))
                .andExpect(jsonPath("$.author").value("Tolkien"))
                .andExpect(jsonPath("$.year").value(1937))
                .andExpect(jsonPath("$.isbn").value("978-0261102217"))
                .andReturn().getResponse().getContentAsString();

        // Extract the generated id and fetch it back.
        Long id = JsonTestSupport.idOf(location);
        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("The Hobbit"));
    }

    @Test
    void listReturnsAllBooksAndSupportsAuthorFilter() throws Exception {
        createBook("Dune", "Herbert", 1965);
        createBook("Foundation", "Asimov", 1951);
        createBook("I, Robot", "Asimov", 1950);

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));

        mockMvc.perform(get("/books").param("author", "Asimov"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].author").value("Asimov"));
    }

    @Test
    void updateModifiesExistingBook() throws Exception {
        Long id = createBook("Old Title", "Old Author", 2000);

        String body = """
                {"title":"New Title","author":"New Author","year":2010,"isbn":"111"}
                """;
        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"))
                .andExpect(jsonPath("$.year").value(2010))
                .andExpect(jsonPath("$.isbn").value("111"));
    }

    @Test
    void deleteRemovesBook() throws Exception {
        Long id = createBook("Disposable", "Someone", 1999);

        mockMvc.perform(delete("/books/{id}", id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isNotFound());
    }

    @Test
    void getUnknownIdReturns404() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404));
    }

    @Test
    void healthReturnsUp() throws Exception {
        mockMvc.perform(get("/books/health"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.status").value("UP"));
    }

    private Long createBook(String title, String author, int year) throws Exception {
        String body = String.format(
                "{\"title\":\"%s\",\"author\":\"%s\",\"year\":%d}", title, author, year);
        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        return JsonTestSupport.idOf(response);
    }
}
