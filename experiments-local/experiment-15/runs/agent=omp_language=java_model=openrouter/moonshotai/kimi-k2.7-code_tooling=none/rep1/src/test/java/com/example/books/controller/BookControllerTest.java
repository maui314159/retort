package com.example.books.controller;

import com.example.books.entity.Book;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class BookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldCreateAndRetrieveBook() throws Exception {
        Book book = new Book();
        book.setTitle("The Hobbit");
        book.setAuthor("J.R.R. Tolkien");
        book.setYear(1937);
        book.setIsbn("978-0547928227");

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists())
                .andExpect(jsonPath("$.title").value("The Hobbit"));

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].title").value("The Hobbit"));
    }

    @Test
    void shouldFilterBooksByAuthor() throws Exception {
        Book book = new Book();
        book.setTitle("1984");
        book.setAuthor("George Orwell");
        book.setYear(1949);

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/books").param("author", "Orwell"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].author").value("George Orwell"));

        mockMvc.perform(get("/books").param("author", "Tolkien"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void shouldUpdateAndDeleteBook() throws Exception {
        Book book = new Book();
        book.setTitle("Dune");
        book.setAuthor("Frank Herbert");
        book.setYear(1965);

        String response = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();

        Long id = objectMapper.readTree(response).get("id").asLong();

        Book update = new Book();
        update.setTitle("Dune Messiah");
        update.setAuthor("Frank Herbert");
        update.setYear(1969);

        mockMvc.perform(put("/books/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(update)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Dune Messiah"));

        mockMvc.perform(delete("/books/{id}", id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/{id}", id))
                .andExpect(status().isNotFound());
    }

    @Test
    void shouldReturn404ForMissingBook() throws Exception {
        mockMvc.perform(get("/books/99999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void shouldRejectBookWithoutRequiredFields() throws Exception {
        Book book = new Book();
        book.setAuthor("Anonymous");
        book.setYear(2020);

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(book)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").value("Title is required"));
    }

    @Test
    void healthShouldReturnUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }
}
