package com.example.books.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.example.books.model.Book;
import com.example.books.service.BookService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class BookControllerIntegrationTests {

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper objectMapper;

    @Autowired
    BookService bookService;

    @Autowired
    JdbcTemplate jdbcTemplate;

    @BeforeEach
    void cleanDb() {
        jdbcTemplate.update("DELETE FROM books");
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void createBookReturns201AndBody() throws Exception {
        Book book = new Book(null, "Dune", "Frank Herbert", 1965, "978-0441172719");
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.author").value("Frank Herbert"))
                .andExpect(jsonPath("$.year").value(1965))
                .andExpect(jsonPath("$.isbn").value("978-0441172719"));
    }

    @Test
    void createBookRejectsMissingTitleAndAuthor() throws Exception {
        Book book = new Book(null, "", "", 2000, "999");
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").exists())
                .andExpect(jsonPath("$.author").exists());
    }

    @Test
    void getBookByIdReturns404WhenMissing() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void listSupportsAuthorFilter() throws Exception {
        bookService.create(new Book(null, "A", "Alice", 2001, "1"));
        bookService.create(new Book(null, "B", "Bob", 2002, "2"));
        bookService.create(new Book(null, "C", "Alice", 2003, "3"));

        mockMvc.perform(get("/books").param("author", "Alice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].author").value("Alice"));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));
    }

    @Test
    void updateBookReturnsUpdated() throws Exception {
        Book created = bookService.create(new Book(null, "Old", "Auth", 2000, "x"));
        Book update = new Book(null, "New", "Auth2", 2020, "y");
        mockMvc.perform(put("/books/" + created.getId())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(update)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New"))
                .andExpect(jsonPath("$.id").value(created.getId()));
    }

    @Test
    void deleteBookReturns204() throws Exception {
        Book created = bookService.create(new Book(null, "Tmp", "Auth", 2000, "x"));
        mockMvc.perform(delete("/books/" + created.getId()))
                .andExpect(status().isNoContent());

        mockMvc.perform(delete("/books/" + created.getId()))
                .andExpect(status().isNotFound());
    }
}
