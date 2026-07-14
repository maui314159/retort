package com.example.bookapi;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
public class BookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    public void setUp() {
        jdbcTemplate.update("DELETE FROM books");
    }

    @Test
    public void testHealthEndpoint() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    public void testCreateAndGetBook() throws Exception {
        String bookJson = """
                {
                    "title": "The Hobbit",
                    "author": "J.R.R. Tolkien",
                    "year": 1937,
                    "isbn": "978-0547928227"
                }
                """;

        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(bookJson))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("The Hobbit"))
                .andExpect(jsonPath("$.author").value("J.R.R. Tolkien"));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("The Hobbit"));
    }

    @Test
    public void testValidation() throws Exception {
        String invalidBookJson = """
                {
                    "year": 2023
                }
                """;

        mockMvc.perform(post("/books")
                .contentType(MediaType.APPLICATION_JSON)
                .content(invalidBookJson))
                .andExpect(status().isBadRequest());
    }

    @Test
    public void testFilterByAuthor() throws Exception {
        String book1 = """
                {
                    "title": "Book 1",
                    "author": "Author A",
                    "year": 2020
                }
                """;
        String book2 = """
                {
                    "title": "Book 2",
                    "author": "Author B",
                    "year": 2021
                }
                """;

        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(book1));
        mockMvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(book2));

        mockMvc.perform(get("/books?author=Author A"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].author").value("Author A"))
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$.length()").value(1));
    }
}