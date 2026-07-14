package com.bookapi;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookApiIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        // Clean up the database before each test
        jdbcTemplate.execute("DELETE FROM books");
    }

    @Test
    void testHealthCheck() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void testCreateBook() throws Exception {
        String bookJson = """
            {
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "year": 1925,
                "isbn": "978-0743273565"
            }
            """;

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("The Great Gatsby"))
                .andExpect(jsonPath("$.author").value("F. Scott Fitzgerald"))
                .andExpect(jsonPath("$.year").value(1925))
                .andExpect(jsonPath("$.isbn").value("978-0743273565"));
    }

    @Test
    void testCreateBookValidation() throws Exception {
        // Test missing title
        String bookJsonMissingTitle = """
            {
                "author": "F. Scott Fitzgerald",
                "year": 1925
            }
            """;

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJsonMissingTitle))
                .andExpect(status().isBadRequest());

        // Test missing author
        String bookJsonMissingAuthor = """
            {
                "title": "The Great Gatsby",
                "year": 1925
            }
            """;

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJsonMissingAuthor))
                .andExpect(status().isBadRequest());
    }

    @Test
    void testGetAllBooks() throws Exception {
        // Create a book first
        String bookJson = """
            {
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "isbn": "978-0451524935"
            }
            """;

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson));

        // Get all books
        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThan(0))))
                .andExpect(jsonPath("$[0].title").value("1984"))
                .andExpect(jsonPath("$[0].author").value("George Orwell"));
    }

    @Test
    void testGetBooksByAuthor() throws Exception {
        // Create books by different authors
        String book1Json = """
            {
                "title": "1984",
                "author": "George Orwell",
                "year": 1949
            }
            """;

        String book2Json = """
            {
                "title": "Animal Farm",
                "author": "George Orwell",
                "year": 1945
            }
            """;

        String book3Json = """
            {
                "title": "To Kill a Mockingbird",
                "author": "Harper Lee",
                "year": 1960
            }
            """;

        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(book1Json));
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(book2Json));
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(book3Json));

        // Filter by author
        mockMvc.perform(get("/books").param("author", "George Orwell"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[*].author", everyItem(is("George Orwell"))));
    }

    @Test
    void testGetBookById() throws Exception {
        // Create a book
        String bookJson = """
            {
                "title": "Brave New World",
                "author": "Aldous Huxley",
                "year": 1932
            }
            """;

        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson))
                .andReturn()
                .getResponse()
                .getContentAsString();

        Long id = objectMapper.readTree(response).get("id").asLong();

        // Get book by id
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("Brave New World"))
                .andExpect(jsonPath("$.author").value("Aldous Huxley"));
    }

    @Test
    void testGetBookByIdNotFound() throws Exception {
        mockMvc.perform(get("/books/999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void testUpdateBook() throws Exception {
        // Create a book
        String bookJson = """
            {
                "title": "Old Title",
                "author": "Old Author",
                "year": 2000
            }
            """;

        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson))
                .andReturn()
                .getResponse()
                .getContentAsString();

        Long id = objectMapper.readTree(response).get("id").asLong();

        // Update the book
        String updatedBookJson = """
            {
                "title": "New Title",
                "author": "New Author",
                "year": 2023,
                "isbn": "978-1234567890"
            }
            """;

        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(updatedBookJson))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id))
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"))
                .andExpect(jsonPath("$.year").value(2023))
                .andExpect(jsonPath("$.isbn").value("978-1234567890"));
    }

    @Test
    void testUpdateBookNotFound() throws Exception {
        String updatedBookJson = """
            {
                "title": "New Title",
                "author": "New Author"
            }
            """;

        mockMvc.perform(put("/books/999")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(updatedBookJson))
                .andExpect(status().isNotFound());
    }

    @Test
    void testDeleteBook() throws Exception {
        // Create a book
        String bookJson = """
            {
                "title": "To Be Deleted",
                "author": "Some Author"
            }
            """;

        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson))
                .andReturn()
                .getResponse()
                .getContentAsString();

        Long id = objectMapper.readTree(response).get("id").asLong();

        // Delete the book
        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        // Verify it's deleted
        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void testDeleteBookNotFound() throws Exception {
        mockMvc.perform(delete("/books/999"))
                .andExpect(status().isNotFound());
    }
}
