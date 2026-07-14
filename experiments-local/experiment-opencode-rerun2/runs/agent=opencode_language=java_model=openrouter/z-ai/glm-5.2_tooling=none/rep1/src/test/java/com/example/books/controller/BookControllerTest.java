package com.example.books.controller;

import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class BookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private BookRepository repository;

    @BeforeEach
    void cleanUp() {
        repository.deleteAll();
    }

    @Test
    void createBook_returnsCreatedWithBody() throws Exception {
        Map<String, Object> book = new HashMap<>();
        book.put("title", "The Hobbit");
        book.put("author", "J.R.R. Tolkien");
        book.put("year", 1937);
        book.put("isbn", "978-0261103283");

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id", notNullValue()))
                .andExpect(jsonPath("$.title", is("The Hobbit")))
                .andExpect(jsonPath("$.author", is("J.R.R. Tolkien")))
                .andExpect(jsonPath("$.year", is(1937)))
                .andExpect(jsonPath("$.isbn", is("978-0261103283")));
    }

    @Test
    void createBook_returns400_whenTitleOrAuthorMissing() throws Exception {
        Map<String, Object> book = new HashMap<>();
        book.put("year", 1999);

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title", notNullValue()))
                .andExpect(jsonPath("$.errors.author", notNullValue()));
    }

    @Test
    void listBooks_returnsAll_andFiltersByAuthor() throws Exception {
        repository.save(book("Dune", "Frank Herbert", 1965, "978-0441172719"));
        repository.save(book("The Martian", "Andy Weir", 2011, "978-0307464461"));
        repository.save(book("Foundation", "Isaac Asimov", 1951, "978-0553293357"));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)));

        mockMvc.perform(get("/books").param("author", "andy weir"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].title", is("The Martian")));
    }

    @Test
    void getBook_returns404_whenNotFound() throws Exception {
        mockMvc.perform(get("/books/9999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateBook_updatesAndReturns200_or404IfMissing() throws Exception {
        Book saved = repository.save(book("Old Title", "Old Author", 2000, "old-isbn"));

        Map<String, Object> update = new HashMap<>();
        update.put("title", "New Title");
        update.put("author", "New Author");
        update.put("year", 2020);
        update.put("isbn", "new-isbn");

        mockMvc.perform(put("/books/" + saved.getId())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(update)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title", is("New Title")))
                .andExpect(jsonPath("$.author", is("New Author")));

        mockMvc.perform(put("/books/9999")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(update)))
                .andExpect(status().isNotFound());
    }

    @Test
    void deleteBook_returns204_and404ForMissing() throws Exception {
        Book saved = repository.save(book("To Delete", "Author", 2010, "isbn-x"));

        mockMvc.perform(delete("/books/" + saved.getId()))
                .andExpect(status().isNoContent());

        mockMvc.perform(delete("/books/" + saved.getId()))
                .andExpect(status().isNotFound());
    }

    @Test
    void healthCheck_returns200() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("UP")));
    }

    private Book book(String title, String author, Integer year, String isbn) {
        Book b = new Book();
        b.setTitle(title);
        b.setAuthor(author);
        b.setYear(year);
        b.setIsbn(isbn);
        return b;
    }
}
